"""Uji koneksi Garmin dari laptop. JANGAN dijalankan di GitHub Actions.

    python cek_garmin.py              -> data hari ini (tidur semalam)
    python cek_garmin.py 2026-11-05   -> data tanggal tertentu

Respons mentah disimpan ke folder samples/ (sudah di .gitignore) supaya kamu bisa
melihat struktur JSON aslinya. Kalau ada metrik yang terbaca "-", kirim NAMA FIELD
yang relevan dari file JSON itu (bukan isinya) supaya parser bisa disesuaikan.
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

from bot.config import ZONA_WAKTU
from bot.garmin_data import ambil_mentah, olah_respons
from bot.recovery import tentukan_rekomendasi

import os
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    api_key = os.environ.get("GARMIN_PERSONAL_API_KEY", "").strip()
    if not api_key:
        sys.exit("Isi GARMIN_PERSONAL_API_KEY di file .env dulu.")

    tanggal = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(ZONA_WAKTU).date()
    print(f"Mengambil data Garmin untuk {tanggal} ...")
    mentah = ambil_mentah(api_key, tanggal)

    folder = Path("samples")
    folder.mkdir(exist_ok=True)
    for nama, isi in mentah.items():
        path = folder / f"{tanggal}_{nama}.json"
        path.write_text(json.dumps(isi, indent=2, ensure_ascii=False), encoding="utf-8")
        status = "kosong/gagal" if isi is None else "OK"
        print(f"  {nama:14s} {status:12s} -> {path}")

    m = olah_respons(tanggal, mentah)
    print("\nMetrik yang terbaca:")
    for k, v in m.ke_dict().items():
        print(f"  {k:12s}: {'-' if v is None else v}")

    rek = tentukan_rekomendasi(m)
    print(f"\nPemulihan: {rek.tingkat}  ({', '.join(rek.alasan)})")
    print(f"Latihan  : {rek.latihan}")


if __name__ == "__main__":
    main()
