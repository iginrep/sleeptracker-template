"""Tes mode pantau: kapan laporan dikirim dan kapan tidak."""

import unittest
from datetime import datetime
from types import SimpleNamespace

import main
from bot.config import ZONA_WAKTU

CFG = SimpleNamespace(garmin_api_key="x")


class DbPalsu:
    def __init__(self, terakhir=None):
        self.s = {"laporan_terakhir": terakhir} if terakhir else {}

    def get_setting(self, k, default=None):
        return self.s.get(k, default)


def jam(h, m=7):
    return datetime(2026, 11, 6, h, m, tzinfo=ZONA_WAKTU)


class TesPantau(unittest.TestCase):
    def setUp(self):
        self.asli = main.tidur_sudah_tersedia

    def tearDown(self):
        main.tidur_sudah_tersedia = self.asli

    def set_tidur(self, ada):
        main.tidur_sudah_tersedia = lambda k, t: ada

    def test_data_belum_ada_sebelum_batas(self):
        self.set_tidur(False)
        self.assertFalse(main.perlu_kirim_sekarang(CFG, DbPalsu(), jam(7)))

    def test_data_sudah_ada(self):
        self.set_tidur(True)
        self.assertTrue(main.perlu_kirim_sekarang(CFG, DbPalsu(), jam(7)))

    def test_sudah_terkirim_hari_ini(self):
        self.set_tidur(True)
        self.assertFalse(main.perlu_kirim_sekarang(CFG, DbPalsu("2026-11-06"), jam(8)))

    def test_terkirim_kemarin_tidak_menghalangi(self):
        self.set_tidur(True)
        self.assertTrue(main.perlu_kirim_sekarang(CFG, DbPalsu("2026-11-05"), jam(6)))

    def test_batas_jam_tetap_kirim(self):
        self.set_tidur(False)
        self.assertTrue(main.perlu_kirim_sekarang(CFG, DbPalsu(), jam(10)))

    def test_garmin_error_tetap_kirim_supaya_ada_peringatan(self):
        def gagal(k, t):
            raise RuntimeError("x")
        main.tidur_sudah_tersedia = gagal
        self.assertTrue(main.perlu_kirim_sekarang(CFG, DbPalsu(), jam(6)))


if __name__ == "__main__":
    unittest.main()
