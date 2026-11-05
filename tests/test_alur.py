"""Tes alur perintah Telegram dan laporan memakai database & Telegram palsu."""

import unittest
from datetime import date

from bot.commands import proses_pesan_masuk
from bot.garmin_data import MetrikHarian
from bot.recovery import tentukan_rekomendasi
from bot.report import susun_laporan
from bot.commands import status_budget

CHAT_ID = "12345"


class DbPalsu:
    def __init__(self):
        self.settings = {"budget_bulanan": "1500000"}
        self.expenses = []

    def get_setting(self, k, default=None):
        return self.settings.get(k, default)

    def set_setting(self, k, v):
        self.settings[k] = v

    def catat_pengeluaran(self, tgl, nominal, ket, mid):
        if any(e["mid"] == mid for e in self.expenses):
            return
        self.expenses.append({"id": len(self.expenses) + 1, "tanggal": tgl.isoformat(),
                              "nominal": nominal, "keterangan": ket, "mid": mid})

    def pengeluaran_antara(self, mulai, sampai):
        return [e for e in self.expenses if mulai.isoformat() <= e["tanggal"] <= sampai.isoformat()]

    def hapus_pengeluaran_terakhir(self):
        return self.expenses.pop() if self.expenses else None


class TgPalsu:
    chat_id = CHAT_ID

    def __init__(self, updates):
        self.updates = updates

    def ambil_pesan(self, offset):
        return [u for u in self.updates if offset is None or u["update_id"] >= offset]


def pesan(uid, teks, chat=CHAT_ID, ts=1_793_934_000):  # 6 Nov 2026 10.00 WIB
    return {"update_id": uid, "message": {"message_id": uid, "date": ts,
                                          "chat": {"id": int(chat)}, "text": teks}}


class TesPerintah(unittest.TestCase):
    def test_alur_lengkap(self):
        db = DbPalsu()
        tg = TgPalsu([
            pesan(1, "/catat 25rb nasi padang"),
            pesan(2, "/catat 10000 es teh"),
            pesan(3, "/catat 999 dari orang lain", chat="999"),  # harus diabaikan
            pesan(4, "/batal"),
            pesan(5, "/sisa"),
            pesan(6, "/laporan"),
        ])
        hari = date(2026, 11, 6)
        h = proses_pesan_masuk(db, tg, hari)
        self.assertEqual(len(db.expenses), 1)
        self.assertEqual(db.expenses[0]["nominal"], 25_000)
        self.assertTrue(h.minta_laporan)
        self.assertEqual(db.settings["telegram_offset"], "7")
        self.assertTrue(any("Sisa hari ini" in b for b in h.balasan))

        # Dijalankan lagi: pesan lama tidak diproses ulang
        h2 = proses_pesan_masuk(db, tg, hari)
        self.assertEqual(h2.jumlah_pesan, 0)
        self.assertEqual(len(db.expenses), 1)

    def test_laporan_tersusun(self):
        db = DbPalsu()
        m = MetrikHarian(tanggal=date(2026, 11, 6), sleep_score=82, sleep_jam=7.5,
                         hrv_semalam=48, hrv_status="BALANCED", body_battery=76, resting_hr=52)
        teks = susun_laporan(m, tentukan_rekomendasi(m), status_budget(db, m.tanggal), None)
        self.assertIn("Jumat 06/11/2026", teks)
        self.assertIn("TINGGI", teks)
        self.assertIn("Rp60.000", teks)  # 1.500.000 / 25 hari tersisa
        print("\n" + teks)


if __name__ == "__main__":
    unittest.main()
