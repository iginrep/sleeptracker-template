"""Membaca semua pengaturan dari environment variable (.env lokal atau GitHub Secrets)."""

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

ZONA_WAKTU = ZoneInfo("Asia/Jakarta")


def _wajib(nama: str) -> str:
    nilai = os.environ.get(nama, "").strip()
    if not nilai:
        raise RuntimeError(f"Environment variable {nama} belum diisi.")
    return nilai


def _opsional(nama: str, default: str = "") -> str:
    return os.environ.get(nama, "").strip() or default


@dataclass(frozen=True)
class Config:
    garmin_api_key: str
    supabase_url: str
    supabase_key: str
    gemini_api_key: str
    gemini_model: str
    gemini_model_cadangan: str
    telegram_token: str
    telegram_chat_id: str
    kota: str
    catatan_makanan: str
    catatan_olahraga: str
    fitur_budget: bool
    fitur_makanan: bool


def load_config() -> Config:
    return Config(
        garmin_api_key=_wajib("GARMIN_PERSONAL_API_KEY"),
        supabase_url=_wajib("SUPABASE_URL").rstrip("/"),
        supabase_key=_wajib("SUPABASE_SECRET_KEY"),
        gemini_api_key=_wajib("GEMINI_API_KEY"),
        gemini_model=_opsional("GEMINI_MODEL", "gemini-flash-latest"),
        gemini_model_cadangan=_opsional("GEMINI_MODEL_CADANGAN", "gemini-flash-lite-latest"),
        telegram_token=_wajib("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_wajib("TELEGRAM_CHAT_ID"),
        kota=_opsional("KOTA", "Jakarta"),
        catatan_makanan=_opsional("CATATAN_MAKANAN", "-"),
        catatan_olahraga=_opsional("CATATAN_OLAHRAGA", "-"),
        fitur_budget=_opsional("FITUR_BUDGET", "false").lower() in ("1", "true", "ya", "on"),
        fitur_makanan=_opsional("FITUR_MAKANAN", "false").lower() in ("1", "true", "ya", "on"),
    )
