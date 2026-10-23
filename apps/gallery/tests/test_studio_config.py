import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "gallery"))
sys.path.insert(0, str(ROOT / "apps" / "studio-console"))


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


if __name__ == "__main__":
    unittest.main()
