"""Menyusun teks laporan pagi."""

from __future__ import annotations

from .budget import StatusBudget, rupiah
from .garmin_data import MetrikHarian
from .recovery import Rekomendasi

IKON = {"tinggi": "🟢", "sedang": "🟡", "rendah": "🔴", "tidak diketahui": "⚪"}
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def _v(nilai, satuan: str = "") -> str:
    return "-" if nilai is None else f"{nilai}{satuan}"


def bagian_budget(b: StatusBudget) -> str:
    return (
        "💰 BUDGET MAKAN\n"
        f"Jatah hari ini: {rupiah(b.jatah_hari_ini)}\n"
        f"Terpakai hari ini: {rupiah(b.terpakai_hari_ini)}\n"
        f"Sisa hari ini: {rupiah(b.sisa_hari_ini)}\n"
        f"Sisa bulan ini: {rupiah(b.sisa_bulan_ini)} untuk {b.sisa_hari} hari"
    )


def susun_laporan(m: MetrikHarian, rek: Rekomendasi, b: StatusBudget | None,
                  saran_ai: str | None, catatan_garmin: str | None = None,
                  makanan: bool = False) -> str:
    t = m.tanggal
    baris = [f"☀️ Laporan Pagi, {HARI[t.weekday()]} {t.strftime('%d/%m/%Y')}", ""]

    baris.append("😴 TIDUR & PEMULIHAN")
    if catatan_garmin:
        baris.append(catatan_garmin)
    baris += [
        f"Sleep score: {_v(m.sleep_score)}",
        f"Durasi tidur: {_v(m.sleep_jam, ' jam')}",
        f"HRV semalam: {_v(m.hrv_semalam, ' ms')} ({_v(m.hrv_status)})",
        f"Body Battery: {_v(m.body_battery)}",
        f"Resting HR: {_v(m.resting_hr, ' bpm')}",
        "",
        f"{IKON.get(rek.tingkat, '⚪')} Pemulihan: {rek.tingkat.upper()}",
        f"({', '.join(rek.alasan)})",
        "",
        "🏃 LATIHAN HARI INI",
        rek.latihan,
        "",
    ]
    if b is not None:
        baris += [bagian_budget(b), ""]
    judul = "🍽️ SARAN DARI AI" if makanan else "🤖 CATATAN AI"
    if saran_ai:
        baris += [judul, saran_ai, ""]
    else:
        baris += [f"{judul}\nSedang tidak tersedia hari ini.", ""]
    if b is not None:
        baris.append("Catat jajan: /catat 25000 nasi padang  |  Bantuan: /help")
    else:
        baris.append("Kirim ulang laporan: /laporan  |  Bantuan: /help")
    return "\n".join(baris)
