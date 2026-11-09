"""Tes percobaan ulang jaringan untuk Telegram dan Supabase."""

import unittest
from types import SimpleNamespace

import requests

import bot.jaringan as jaringan
from bot.db import Database
from bot.telegram import Telegram


def resp(status, data=None):
    return SimpleNamespace(status_code=status, ok=200 <= status < 300,
                           content=b"x" if data is not None else b"",
                           json=lambda: data, text="")


class TesUlang(unittest.TestCase):
    def setUp(self):
        self.jeda = jaringan.JEDA_ULANG
        jaringan.JEDA_ULANG = (0, 0, 0)
        self.post, self.request = requests.post, requests.request

    def tearDown(self):
        jaringan.JEDA_ULANG = self.jeda
        requests.post, requests.request = self.post, self.request

    def urutan(self, hasil):
        panggilan = []

        def palsu(*a, **kw):
            panggilan.append(1)
            h = hasil[len(panggilan) - 1]
            if isinstance(h, Exception):
                raise h
            return h
        return palsu, panggilan

    def test_telegram_pulih_setelah_putus(self):
        f, n = self.urutan([requests.ConnectionError(), resp(200, {"result": []})])
        requests.post = f
        self.assertEqual(Telegram("t", "1").ambil_pesan(None), [])
        self.assertEqual(len(n), 2)

    def test_getupdates_diulang_saat_timeout(self):
        f, n = self.urutan([requests.exceptions.ReadTimeout(), resp(200, {"result": []})])
        requests.post = f
        Telegram("t", "1").ambil_pesan(None)
        self.assertEqual(len(n), 2)

    def test_sendmessage_tidak_diulang_saat_timeout(self):
        f, n = self.urutan([requests.exceptions.ReadTimeout(), resp(200, {"result": {}})])
        requests.post = f
        with self.assertRaises(RuntimeError):
            Telegram("t", "1").kirim("halo")
        self.assertEqual(len(n), 1)

    def test_telegram_gagal_terus(self):
        f, n = self.urutan([requests.ConnectionError()] * 3)
        requests.post = f
        with self.assertRaisesRegex(RuntimeError, "masalah jaringan"):
            Telegram("t", "1").ambil_pesan(None)
        self.assertEqual(len(n), 3)

    def test_supabase_pulih_dari_503(self):
        f, n = self.urutan([resp(503), resp(200, [{"nilai": "x"}])])
        requests.request = f
        self.assertEqual(Database("https://a.supabase.co", "k").get_setting("a"), "x")
        self.assertEqual(len(n), 2)

    def test_supabase_404_tidak_diulang(self):
        f, n = self.urutan([resp(404)])
        requests.request = f
        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            Database("https://a.supabase.co", "k").get_setting("a")
        self.assertEqual(len(n), 1)


if __name__ == "__main__":
    unittest.main()
