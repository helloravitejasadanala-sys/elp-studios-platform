import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from elp_lib import (
    STORAGE_ALERT_THRESHOLDS,
    build_storage_report,
    classify_media,
    estimate_remaining_capacity,
    event_media_usage,
    storage_alert_for_percent,
    storage_fill_percent,
)


class StorageMathTests(unittest.TestCase):
    def test_alert_thresholds_are_70_85_95(self):
        self.assertEqual([row["percent"] for row in STORAGE_ALERT_THRESHOLDS], [70, 85, 95])
        self.assertEqual(storage_alert_for_percent(12)["level"], "ok")
        self.assertEqual(storage_alert_for_percent(70)["level"], "watch")
        self.assertEqual(storage_alert_for_percent(84.9)["level"], "watch")
        self.assertEqual(storage_alert_for_percent(85)["level"], "warning")
        self.assertEqual(storage_alert_for_percent(95)["level"], "critical")
        self.assertEqual(storage_alert_for_percent(None)["level"], "unknown")

    def test_fill_percent(self):
        self.assertEqual(storage_fill_percent(70, 100), 70.0)
        self.assertIsNone(storage_fill_percent(10, 0))
        self.assertIsNone(storage_fill_percent(None, 100))

    def test_classify_media(self):
        self.assertEqual(classify_media("clip.MP4", "video/mp4"), "video")
        self.assertEqual(classify_media("hero.jpg", "image/jpeg"), "photo")
        self.assertEqual(classify_media("notes.txt", "text/plain"), "other")

    def test_event_media_usage_splits_photo_and_video(self):
        usage = event_media_usage(
            [
                {"filename": "a.jpg", "size_bytes": 100, "mime_type": "image/jpeg"},
                {"filename": "b.mp4", "file_size": 900, "type": "video/mp4"},
                {"filename": "c.mov", "size": 50},
            ]
        )
        self.assertEqual(usage["photo_bytes"], 100)
        self.assertEqual(usage["video_bytes"], 950)
        self.assertEqual(usage["photo_count"], 1)
        self.assertEqual(usage["video_count"], 2)

    def test_remaining_capacity_from_recent_uploads(self):
        est = estimate_remaining_capacity(
            available_bytes=20_000,
            recent_bytes=10_000,
            window_days=10,
            sample_count=9,
        )
        self.assertEqual(est["bytes_per_day"], 1000)
        self.assertEqual(est["days_remaining"], 20.0)
        self.assertEqual(est["confidence"], "high")
        idle = estimate_remaining_capacity(available_bytes=20, recent_bytes=0, window_days=14)
        self.assertEqual(idle["status"], "idle")

    def test_report_uses_picpeak_info_and_does_not_mark_paid(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        photos = [
            {
                "filename": "a.jpg",
                "size_bytes": 8_000_000,
                "mime_type": "image/jpeg",
                "created_at": (now - timedelta(days=2)).isoformat(),
            },
            {
                "filename": "speech.mp4",
                "size_bytes": 42_000_000,
                "mime_type": "video/mp4",
                "created_at": (now - timedelta(days=1)).isoformat(),
            },
        ]
        report = build_storage_report(
            info={
                "total_used": 70,
                "disk_total": 100,
                "disk_available": 30,
                "cataloged_bytes": 50,
                "storage_by_event": [{"id": 7, "event_name": "Keep Me", "size": 50}],
                "storage_measurement": "disk",
                "archive_storage": 0,
                "configured_soft_limit": None,
                "disk_metrics_reliable": True,
            },
            events=[{"id": 7, "event_name": "Keep Me", "is_draft": False}],
            photos_by_event={7: photos},
            settings={"backup_enabled": False, "general_max_file_size_mb": 50, "general_max_video_size_mb": 500},
            backup={"backup_enabled": False},
            now=now,
        )
        self.assertFalse(report["destructive"])
        self.assertFalse(report["paid_services_enabled"])
        self.assertEqual(report["alert"]["level"], "watch")
        self.assertEqual(report["volume_name"], "elp-picpeak-data")
        row = report["events"][0]
        self.assertEqual(row["photo_count"], 1)
        self.assertEqual(row["video_count"], 1)
        self.assertEqual(row["video_bytes"], 42_000_000)
        self.assertEqual(report["backup"]["enabled"], False)
        self.assertGreaterEqual(len(report["cost_categories"]), 4)
        ids = {c["id"] for c in report["cost_categories"]}
        self.assertEqual(ids, {"software", "hosting", "backup", "third_party"})
        self.assertFalse(any(c["committed"] for c in report["cost_categories"]))
        self.assertFalse(report["archive_policy"]["console_deletes"])
        self.assertIn("docker compose down -v", report["archive_policy"]["never"])
        self.assertEqual(report["remaining"]["status"], "ok")

    def test_build_report_never_requires_delete_fields(self):
        report = build_storage_report(info={}, events=[], photos_by_event={})
        self.assertEqual(report["alert"]["level"], "unknown")
        self.assertFalse(report["destructive"])


if __name__ == "__main__":
    unittest.main()
