"""Titik masuk utama.

Cara pakai:
    python main.py pantau    -> dipakai jadwal pagi: kirim laporan begitu data tidur
                                sudah tersinkron, atau saat batas jam tercapai
    python main.py pagi      -> paksa kirim laporan sekarang
    python main.py sinkron   -> proses pesan masuk saja (dan kirim laporan kalau diminta /laporan)
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime

from bot import ai
from bot.commands import proses_pesan_masuk, status_budget
from bot.config import ZONA_WAKTU, load_config
from bot.db import Database
from bot.garmin_data import (GarminAuthError, GarminRateLimitError, MetrikHarian, ambil_metrik,
                             tidur_sudah_tersedia)
from bot.recovery import tentukan_rekomendasi
from bot.report import susun_laporan
from bot.telegram import Telegram

# Log hanya berisi status, tidak pernah berisi data kesehatan atau uang.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
# Library HTTP tidak perlu mencetak detail request.
for nama in ("garmin_personal_api", "httpx", "urllib3", "google_genai"):
    logging.getLogger(nama).setLevel(logging.WARNING)
log = logging.getLogger("main")

# Mode "pantau": kalau sampai jam ini data tidur belum ada, laporan tetap dikirim.
# Harus sama dengan jadwal terakhir di .github/workflows/pagi.yml
JAM_BATAS_LAPORAN = 10


def kirim_laporan(cfg, db: Database, tg: Telegram, hari_ini) -> None:
    catatan = None
    try:
        metrik = ambil_metrik(cfg.garmin_api_key, hari_ini)
        log.info("Data Garmin diambil (data tidur %s)", "ada" if metrik.ada_data_tidur else "belum ada")
    except GarminAuthError:
        metrik = MetrikHarian(tanggal=hari_ini)
        catatan = "⚠️ API key Garmin ditolak atau kedaluwarsa. Buat key baru di Garmin Connect lalu perbarui GitHub Secret."
        log.error("Garmin menolak API key")
    except GarminRateLimitError:
        metrik = MetrikHarian(tanggal=hari_ini)
        catatan = "⚠️ Garmin sedang membatasi akses. Bot tidak mencoba ulang hari ini."
        log.error("Garmin rate limit")
    except Exception as e:  # noqa: BLE001
        metrik = MetrikHarian(tanggal=hari_ini)
        catatan = "⚠️ Gagal mengambil data Garmin. Coba /laporan nanti."
        log.error("Garmin error: %s", type(e).__name__)

    if catatan is None and not metrik.ada_data_tidur:
        catatan = ("ℹ️ Data tidur semalam belum ada. Buka aplikasi Garmin Connect di HP untuk sinkron, "
                   "lalu kirim /laporan.")

    rek = tentukan_rekomendasi(metrik)

    if metrik.ada_data_tidur:
        db.simpan_metrik({**metrik.ke_dict(), "tingkat_pulih": rek.tingkat})

    # Budget hanya relevan kalau saran makanan aktif.
    budget = status_budget(db, hari_ini) if (cfg.fitur_budget and cfg.fitur_makanan) else None
    riwayat = db.metrik_terakhir(7)
    prompt = ai.susun_prompt(metrik, rek, budget, riwayat, cfg.kota,
                             cfg.catatan_makanan, cfg.catatan_olahraga, cfg.fitur_makanan)
    saran = ai.buat_saran(cfg.gemini_api_key, cfg.gemini_model, prompt,
                          cfg.gemini_model_cadangan)
    log.info("Saran AI %s", "berhasil" if saran else "tidak tersedia")

    tg.kirim(susun_laporan(metrik, rek, budget, saran, catatan, cfg.fitur_makanan))
    # Tandai "sudah terkirim" hanya kalau laporan berisi data tidur. Jadi laporan
    # uji coba atau /laporan sebelum jam sinkron tidak membatalkan laporan pagi.
    if metrik.ada_data_tidur:
        db.set_setting("laporan_terakhir", hari_ini.isoformat())
    log.info("Laporan terkirim")


def perlu_kirim_sekarang(cfg, db: Database, sekarang: datetime) -> bool:
    """Untuk mode pantau: kirim kalau belum terkirim hari ini DAN
    (data tidur sudah ada ATAU sudah lewat batas jam)."""
    hari_ini = sekarang.date()
    if db.get_setting("laporan_terakhir") == hari_ini.isoformat():
        log.info("Laporan hari ini sudah terkirim")
        return False
    if sekarang.hour >= JAM_BATAS_LAPORAN:
        log.info("Batas jam tercapai, laporan dikirim apa adanya")
        return True
    try:
        ada = tidur_sudah_tersedia(cfg.garmin_api_key, hari_ini)
    except Exception as e:  # noqa: BLE001 - biar laporan lengkap yang menangani & melapor
        log.warning("Cek data tidur gagal: %s", type(e).__name__)
        return True
    log.info("Data tidur %s", "sudah ada" if ada else "belum ada, cek lagi nanti")
    return ada


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "sinkron"
    if mode not in ("pantau", "pagi", "sinkron"):
        print("Mode harus 'pantau', 'pagi', atau 'sinkron'")
        return 2

    cfg = load_config()
    db = Database(cfg.supabase_url, cfg.supabase_key)
    tg = Telegram(cfg.telegram_token, cfg.telegram_chat_id)
    sekarang = datetime.now(ZONA_WAKTU)
    hari_ini = sekarang.date()

    hasil = proses_pesan_masuk(db, tg, hari_ini, cfg.fitur_budget)
    log.info("Perintah diproses: %d", hasil.jumlah_pesan)
    if hasil.balasan:
        tg.kirim("\n\n".join(hasil.balasan))

    if mode == "pagi" or hasil.minta_laporan:
        kirim_laporan(cfg, db, tg, hari_ini)
    elif mode == "pantau" and perlu_kirim_sekarang(cfg, db, sekarang):
        kirim_laporan(cfg, db, tg, hari_ini)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        # Coba beri tahu lewat Telegram, tanpa membocorkan detail.
        # Pesan RuntimeError buatan kita sendiri aman ditampilkan (tidak berisi data).
        log.error("Gagal: %s %s", type(e).__name__, e if isinstance(e, RuntimeError) else "")
        try:
            cfg = load_config()
            Telegram(cfg.telegram_token, cfg.telegram_chat_id).kirim(
                f"❌ Bot gagal berjalan ({type(e).__name__}). Cek tab Actions di GitHub.")
        except Exception:  # noqa: BLE001
            pass
        sys.exit(1)
