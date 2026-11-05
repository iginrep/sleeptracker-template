"""Memproses perintah Telegram yang masuk sejak workflow terakhir berjalan."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime

from .budget import StatusBudget, hitung_status, parse_nominal, rupiah
from .config import ZONA_WAKTU
from .db import Database
from .telegram import Telegram

log = logging.getLogger(__name__)

BANTUAN_BUDGET = """
/catat 25000 nasi padang  : catat pengeluaran makan
/sisa                     : lihat sisa budget
/budget 1500000           : ubah budget makan bulanan
/batal                    : hapus catatan pengeluaran terakhir
Format nominal: 25000, 25.000, 25rb, 25k, 1,5jt"""

PERINTAH_BUDGET = ("/catat", "/sisa", "/budget", "/batal")


def teks_bantuan(fitur_budget: bool) -> str:
    return ("📖 Perintah yang tersedia:\n"
            "/laporan  : minta laporan pagi dikirim ulang\n"
            "/help     : daftar perintah"
            + (BANTUAN_BUDGET if fitur_budget else "")
            + "\n\nCatatan: bot memproses pesan secara berkala, jadi balasan bisa datang "
              "beberapa jam kemudian.")


@dataclass
class HasilProses:
    fitur_budget: bool = True
    minta_laporan: bool = False
    jumlah_pesan: int = 0
    balasan: list[str] = field(default_factory=list)


def status_budget(db: Database, hari_ini: date) -> StatusBudget:
    budget = int(db.get_setting("budget_bulanan", "0") or 0)
    rows = db.pengeluaran_antara(hari_ini.replace(day=1), hari_ini)
    hari_ini_str = hari_ini.isoformat()
    sebelum = sum(r["nominal"] for r in rows if r["tanggal"] != hari_ini_str)
    hari_ini_total = sum(r["nominal"] for r in rows if r["tanggal"] == hari_ini_str)
    return hitung_status(budget, sebelum, hari_ini_total, hari_ini)


def _tanggal_pesan(msg: dict) -> date:
    return datetime.fromtimestamp(msg["date"], ZONA_WAKTU).date()


def _proses_satu(teks: str, msg: dict, db: Database, hasil: HasilProses) -> None:
    bagian = teks.strip().split(maxsplit=2)
    perintah = bagian[0].lower().split("@")[0]  # "/catat@NamaBot" -> "/catat"

    if perintah in ("/start", "/help", "/bantuan"):
        hasil.balasan.append(teks_bantuan(hasil.fitur_budget))

    elif perintah in PERINTAH_BUDGET and not hasil.fitur_budget:
        hasil.balasan.append("Fitur budget sedang nonaktif.")

    elif perintah == "/catat":
        nominal = parse_nominal(bagian[1]) if len(bagian) > 1 else None
        if nominal is None:
            hasil.balasan.append("⚠️ Format salah. Contoh: /catat 25000 nasi padang")
            return
        ket = bagian[2] if len(bagian) > 2 else "-"
        tgl = _tanggal_pesan(msg)
        db.catat_pengeluaran(tgl, nominal, ket[:200], msg.get("message_id"))
        hasil.balasan.append(f"✅ Tercatat {rupiah(nominal)} ({ket}) untuk {tgl.strftime('%d/%m')}")

    elif perintah == "/batal":
        dihapus = db.hapus_pengeluaran_terakhir()
        hasil.balasan.append(
            f"🗑️ Dihapus: {rupiah(dihapus['nominal'])} ({dihapus['keterangan']})"
            if dihapus else "Belum ada catatan pengeluaran.")

    elif perintah == "/budget":
        nominal = parse_nominal(bagian[1]) if len(bagian) > 1 else None
        if nominal is None:
            hasil.balasan.append("⚠️ Format salah. Contoh: /budget 1500000")
            return
        db.set_setting("budget_bulanan", str(nominal))
        hasil.balasan.append(f"✅ Budget makan bulanan diubah menjadi {rupiah(nominal)}")

    elif perintah == "/sisa":
        hasil.balasan.append("__SISA__")  # dihitung di akhir supaya mencakup /catat terbaru

    elif perintah == "/laporan":
        hasil.minta_laporan = True

    else:
        hasil.balasan.append("Perintah tidak dikenal. Ketik /help untuk daftar perintah.")


def proses_pesan_masuk(db: Database, tg: Telegram, hari_ini: date,
                       fitur_budget: bool = True) -> HasilProses:
    hasil = HasilProses(fitur_budget=fitur_budget)
    offset_str = db.get_setting("telegram_offset")
    updates = tg.ambil_pesan(int(offset_str) if offset_str else None)
    if not updates:
        return hasil

    for upd in updates:
        msg = upd.get("message") or {}
        # Keamanan: abaikan pesan dari siapa pun selain pemilik bot.
        if str(msg.get("chat", {}).get("id")) != tg.chat_id:
            continue
        teks = msg.get("text") or ""
        if not teks.startswith("/"):
            continue
        hasil.jumlah_pesan += 1
        try:
            _proses_satu(teks, msg, db, hasil)
        except Exception as e:  # noqa: BLE001 - satu pesan gagal tidak menghentikan yang lain
            log.warning("Gagal memproses satu perintah: %s", type(e).__name__)
            hasil.balasan.append("⚠️ Ada perintah yang gagal diproses, coba kirim ulang.")

    # Tandai semua pesan sudah dibaca, supaya tidak diproses dua kali.
    db.set_setting("telegram_offset", str(updates[-1]["update_id"] + 1))

    if "__SISA__" in hasil.balasan:
        b = status_budget(db, hari_ini)
        teks_sisa = (f"💰 Sisa hari ini: {rupiah(b.sisa_hari_ini)} dari jatah {rupiah(b.jatah_hari_ini)}\n"
                     f"Sisa bulan ini: {rupiah(b.sisa_bulan_ini)} untuk {b.sisa_hari} hari")
        hasil.balasan = [teks_sisa if x == "__SISA__" else x for x in hasil.balasan]
    return hasil
