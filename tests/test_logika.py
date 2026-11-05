"""Tes logika inti. Jalankan: python -m unittest discover tests"""

import unittest
from datetime import date

from bot.budget import hitung_status, parse_nominal, rupiah
from bot.garmin_data import MetrikHarian, olah_respons
from bot.recovery import tentukan_rekomendasi


class TesBudget(unittest.TestCase):
    def test_jatah_harian(self):
        # November 30 hari, tanggal 21 -> sisa 10 hari termasuk hari ini
        b = hitung_status(1_500_000, 1_000_000, 20_000, date(2026, 11, 21))
        self.assertEqual(b.sisa_hari, 10)
        self.assertEqual(b.jatah_hari_ini, 50_000)
        self.assertEqual(b.sisa_hari_ini, 30_000)
        self.assertEqual(b.sisa_bulan_ini, 480_000)

    def test_budget_habis(self):
        b = hitung_status(1_000_000, 1_200_000, 0, date(2026, 11, 25))
        self.assertEqual(b.jatah_hari_ini, 0)

    def test_parse_nominal(self):
        self.assertEqual(parse_nominal("25000"), 25_000)
        self.assertEqual(parse_nominal("25.000"), 25_000)
        self.assertEqual(parse_nominal("25rb"), 25_000)
        self.assertEqual(parse_nominal("25k"), 25_000)
        self.assertEqual(parse_nominal("1,5jt"), 1_500_000)
        self.assertEqual(parse_nominal("Rp12.500"), 12_500)
        self.assertIsNone(parse_nominal("abc"))
        self.assertIsNone(parse_nominal("0"))

    def test_rupiah(self):
        self.assertEqual(rupiah(1500000), "Rp1.500.000")
        self.assertEqual(rupiah(-5000), "-Rp5.000")


class TesPemulihan(unittest.TestCase):
    def m(self, **kw):
        return MetrikHarian(tanggal=date(2026, 11, 6), **kw)

    def test_tinggi(self):
        r = tentukan_rekomendasi(self.m(sleep_score=85, body_battery=80, hrv_status="BALANCED"))
        self.assertEqual(r.tingkat, "tinggi")

    def test_sedang(self):
        r = tentukan_rekomendasi(self.m(sleep_score=55, body_battery=75, hrv_status="BALANCED"))
        self.assertEqual(r.tingkat, "sedang")

    def test_rendah(self):
        r = tentukan_rekomendasi(self.m(sleep_score=50, body_battery=30, hrv_status="LOW"))
        self.assertEqual(r.tingkat, "rendah")

    def test_body_battery_sangat_rendah(self):
        r = tentukan_rekomendasi(self.m(sleep_score=85, body_battery=20, hrv_status="BALANCED"))
        self.assertEqual(r.tingkat, "rendah")

    def test_tanpa_data(self):
        self.assertEqual(tentukan_rekomendasi(self.m()).tingkat, "tidak diketahui")


class TesParserGarmin(unittest.TestCase):
    def test_struktur_umum(self):
        mentah = {
            "sleep": {"dailySleepDTO": {"sleepTimeSeconds": 27000,
                                        "sleepScores": {"overall": {"value": 82}}}},
            "hrv": {"hrvSummary": {"lastNightAvg": 48, "status": "BALANCED"}},
            "daily_summary": {"data": [{"restingHeartRate": 52, "bodyBatteryAtWakeTime": 76}]},
            "body_battery": None,
        }
        m = olah_respons(date(2026, 11, 6), mentah)
        self.assertEqual(m.sleep_score, 82)
        self.assertEqual(m.sleep_jam, 7.5)
        self.assertEqual(m.hrv_semalam, 48)
        self.assertEqual(m.hrv_status, "BALANCED")
        self.assertEqual(m.resting_hr, 52)
        self.assertEqual(m.body_battery, 76)

    def test_semua_kosong(self):
        m = olah_respons(date(2026, 11, 6), {"sleep": None, "hrv": None,
                                             "daily_summary": None, "body_battery": None})
        self.assertFalse(m.ada_data_tidur)


if __name__ == "__main__":
    unittest.main()
