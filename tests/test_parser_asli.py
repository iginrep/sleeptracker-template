"""Tes parser dengan struktur JSON yang sama seperti respons asli Garmin Personal API.

Nilai di sini karangan, hanya strukturnya yang mengikuti data asli.
"""

import unittest
from datetime import date

from bot.ai import format_durasi, ringkas_tren
from bot.garmin_data import olah_respons

AKHIR_TIDUR = 1_793_870_000_000  # ms

MENTAH = {
    "sleep": {
        "sleepTimeSeconds": 17_700,
        "sleepEndTimestampGMT": AKHIR_TIDUR,
        "avgHeartRate": 60.0,
        "sleepScores": {"overall": {"value": 61, "qualifierKey": "FAIR"},
                        "remPercentage": {"value": 20}},
    },
    "hrv": {"hrvSummary": {"weeklyAvg": 60, "lastNightAvg": 69, "status": "BALANCED"},
            "hrvReadings": [{"hrvValue": 80}]},
    "daily_summary": {"data": [{
        "heartRate": {"minValue": 48, "maxValue": 150, "restingValue": 52},
        "bodyBattery": {"minValue": 20, "maxValue": 90, "chargedValue": 40, "latestValue": 35},
    }]},
    "body_battery": [{
        "charged": 58, "drained": 70,
        "bodyBatteryValuesArray": [
            [AKHIR_TIDUR - 4 * 3600_000, 30],
            [AKHIR_TIDUR - 3 * 60_000, 77],   # titik terdekat dengan waktu bangun
            [AKHIR_TIDUR + 5 * 3600_000, 90],
        ],
    }],
}


class TesParserAsli(unittest.TestCase):
    def test_semua_metrik(self):
        m = olah_respons(date(2026, 11, 6), MENTAH)
        self.assertEqual(m.sleep_score, 61)
        self.assertEqual(m.hrv_semalam, 69)          # bukan weeklyAvg
        self.assertEqual(m.hrv_status, "BALANCED")
        self.assertEqual(m.resting_hr, 52)           # heartRate.restingValue
        self.assertEqual(m.body_battery, 77)         # level saat bangun, bukan charged (58)

    def test_body_battery_cadangan_maxvalue(self):
        mentah = dict(MENTAH, body_battery=None)
        self.assertEqual(olah_respons(date(2026, 11, 6), mentah).body_battery, 90)

    def test_format_durasi(self):
        self.assertEqual(format_durasi(4.92), "4 jam 55 menit")
        self.assertEqual(format_durasi(7.5), "7 jam 30 menit")
        self.assertIsNone(format_durasi(None))

    def test_tren_belum_cukup(self):
        self.assertIn("belum cukup data", ringkas_tren([{"sleep_score": 60}]))

    def test_tren_rata_rata(self):
        r = [{"sleep_score": 60, "body_battery": 50, "hrv_semalam": 40},
             {"sleep_score": 80, "body_battery": 70, "hrv_semalam": 60},
             {"sleep_score": 70, "body_battery": None, "hrv_semalam": 50}]
        t = ringkas_tren(r)
        self.assertIn("sleep score 70", t)
        self.assertIn("Body Battery saat bangun 60", t)
        self.assertIn("HRV 50 ms", t)


if __name__ == "__main__":
    unittest.main()
