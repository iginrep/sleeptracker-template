"""Tes saklar budget dan percobaan ulang Gemini."""

import unittest
from datetime import date
from types import SimpleNamespace

from google.genai import errors

import bot.ai as ai
from bot.commands import _proses_satu, HasilProses
from bot.garmin_data import MetrikHarian
from bot.recovery import tentukan_rekomendasi
from bot.report import susun_laporan


class TesTanpaBudget(unittest.TestCase):
    def test_laporan_tanpa_budget(self):
        m = MetrikHarian(tanggal=date(2026, 11, 6), sleep_score=70)
        teks = susun_laporan(m, tentukan_rekomendasi(m), None, "menu")
        self.assertNotIn("BUDGET", teks)
        self.assertNotIn("/catat", teks)
        self.assertIn("/laporan", teks)

    def test_prompt_tanpa_budget(self):
        m = MetrikHarian(tanggal=date(2026, 11, 6))
        p = ai.susun_prompt(m, tentukan_rekomendasi(m), None, [], "Bandung", "-", "-")
        self.assertNotIn("BUDGET", p)

    def test_perintah_budget_ditolak(self):
        h = HasilProses(fitur_budget=False)
        _proses_satu("/catat 10000 kopi", {"date": 0}, db=None, hasil=h)
        self.assertEqual(h.balasan, ["Fitur budget sedang nonaktif."])
        h2 = HasilProses(fitur_budget=False)
        _proses_satu("/help", {}, db=None, hasil=h2)
        self.assertNotIn("/catat", h2.balasan[0])


class ClientPalsu:
    def __init__(self, gagal_per_model):
        self.gagal = dict(gagal_per_model)
        self.panggilan = []
        self.models = SimpleNamespace(generate_content=self._gen)

    def _gen(self, model, contents, config):
        self.panggilan.append(model)
        if self.gagal.get(model, 0) > 0:
            self.gagal[model] -= 1
            raise errors.ServerError(503, {"error": {"code": 503, "status": "UNAVAILABLE"}})
        return SimpleNamespace(text="saran ok")


class TesGeminiRetry(unittest.TestCase):
    def setUp(self):
        self.jeda = ai.JEDA_PERCOBAAN
        ai.JEDA_PERCOBAAN = (0, 0, 0)
        self.client_asli = ai.genai.Client

    def tearDown(self):
        ai.JEDA_PERCOBAAN = self.jeda
        ai.genai.Client = self.client_asli

    def jalankan(self, gagal):
        c = ClientPalsu(gagal)
        ai.genai.Client = lambda api_key, http_options=None: c
        return ai.buat_saran("k", "utama", "p", "cadangan"), c.panggilan

    def test_berhasil_setelah_retry(self):
        hasil, panggilan = self.jalankan({"utama": 2})
        self.assertEqual(hasil, "saran ok")
        self.assertEqual(panggilan, ["utama"] * 3)

    def test_pindah_ke_model_cadangan(self):
        hasil, panggilan = self.jalankan({"utama": 3})
        self.assertEqual(hasil, "saran ok")
        self.assertEqual(panggilan[-1], "cadangan")

    def test_semua_gagal(self):
        hasil, _ = self.jalankan({"utama": 3, "cadangan": 3})
        self.assertIsNone(hasil)


if __name__ == "__main__":
    unittest.main()


class TesTanpaMakanan(unittest.TestCase):
    def test_prompt_tanpa_makanan(self):
        m = MetrikHarian(tanggal=date(2026, 11, 6), sleep_score=75)
        p = ai.susun_prompt(m, tentukan_rekomendasi(m), None, [], "Bandung", "halal", "lari",
                            makanan=False)
        self.assertIn("JANGAN membahas makanan", p)
        self.assertNotIn("Bandung", p)
        self.assertNotIn("halal", p)

    def test_prompt_dengan_makanan(self):
        m = MetrikHarian(tanggal=date(2026, 11, 6))
        p = ai.susun_prompt(m, tentukan_rekomendasi(m), None, [], "Bandung", "halal", "lari",
                            makanan=True)
        self.assertIn("menu sarapan", p)
        self.assertIn("Bandung", p)

    def test_judul_laporan(self):
        m = MetrikHarian(tanggal=date(2026, 11, 6))
        r = tentukan_rekomendasi(m)
        self.assertIn("CATATAN AI", susun_laporan(m, r, None, "x"))
        self.assertIn("SARAN DARI AI", susun_laporan(m, r, None, "x", makanan=True))


class TesTanpaDataTidur(unittest.TestCase):
    def test_label_dan_catatan(self):
        m = MetrikHarian(tanggal=date(2026, 11, 9), body_battery=5, resting_hr=62)
        r = tentukan_rekomendasi(m)
        self.assertIn("tanpa data tidur, kurang akurat", r.alasan)
        teks = susun_laporan(m, r, None, "x")
        self.assertIn("Body Battery tertinggi hari ini: 5", teks)
        self.assertNotIn("saat bangun", teks)

    def test_label_normal(self):
        m = MetrikHarian(tanggal=date(2026, 11, 9), sleep_score=62, sleep_jam=6.45, body_battery=70)
        teks = susun_laporan(m, tentukan_rekomendasi(m), None, "x")
        self.assertIn("Body Battery saat bangun: 70", teks)
