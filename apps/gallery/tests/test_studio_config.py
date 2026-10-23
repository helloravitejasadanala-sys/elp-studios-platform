import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "gallery"))
sys.path.insert(0, str(ROOT / "apps" / "studio-console"))
sys.path.insert(0, str(ROOT / "apps" / "gallery" / "tests"))


class StudioConfigTests(unittest.TestCase):
    def test_config_endpoint_lists_brands_and_video_accept(self):
        import server as studio

        httpd = studio.ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(f"http://127.0.0.1:{port}/config.json", timeout=5) as resp:
                cfg = json.loads(resp.read().decode())
        finally:
            httpd.shutdown()
        ids = [b["id"] for b in cfg["brands"]]
        self.assertEqual(ids, ["mini-momentz", "katha-films", "tattva-weddings"])
        self.assertIn(".mp4", cfg["video"]["accept"])
        self.assertIn(".mov", cfg["video"]["accept"])
        mini = cfg["brands"][0]
        self.assertIn("Mini Momentz", mini["whatsapp_share_template"])
        self.assertTrue(mini["logo_web_path"].startswith("/brand-assets/"))
        self.assertEqual(cfg["storage"]["volumeName"], "elp-picpeak-data")
        self.assertEqual([a["percent"] for a in cfg["storage"]["alerts"]], [70, 85, 95])
        self.assertFalse(cfg["storage"]["archivePolicy"]["console_deletes"])
        cost_ids = [c["id"] for c in cfg["storage"]["costCategories"]]
        self.assertEqual(cost_ids, ["software", "hosting", "backup", "third_party"])
        self.assertFalse(any(c["committed"] for c in cfg["storage"]["costCategories"]))

    def test_storage_report_is_read_only_and_splits_media(self):
        import server as studio
        from mock_picpeak import H as MockPicPeak

        mock = studio.ThreadingHTTPServer(("127.0.0.1", 0), MockPicPeak)
        mock_port = mock.server_address[1]
        mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
        mock_thread.start()
        prev_origin = studio.PICPEAK_ORIGIN
        studio.PICPEAK_ORIGIN = f"http://127.0.0.1:{mock_port}"
        httpd = studio.ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            req = Request(
                f"http://127.0.0.1:{port}/elp/storage-report",
                headers={"Authorization": "Bearer mock-token"},
            )
            with urlopen(req, timeout=5) as resp:
                report = json.loads(resp.read().decode())
        finally:
            studio.PICPEAK_ORIGIN = prev_origin
            httpd.shutdown()
            mock.shutdown()
        self.assertFalse(report["destructive"])
        self.assertFalse(report["paid_services_enabled"])
        self.assertEqual(report["volume_name"], "elp-picpeak-data")
        self.assertGreaterEqual(len(report["events"]), 1)
        row = report["events"][0]
        self.assertTrue(row["has_media_split"])
        self.assertEqual(row["photo_count"], 1)
        self.assertEqual(row["video_count"], 1)
        self.assertEqual(report["backup"]["enabled"], False)
        self.assertFalse(report["archive_policy"]["console_deletes"])


if __name__ == "__main__":
    unittest.main()
