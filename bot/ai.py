"""Merangkai saran latihan dan makanan dengan Gemini.

Yang dikirim ke Gemini hanya angka ringkasan, tanpa nama, email, atau identitas.
"""

from __future__ import annotations

import logging
import time

from google import genai
from google.genai import errors, types

from .budget import StatusBudget, rupiah
from .garmin_data import MetrikHarian
from .recovery import Rekomendasi

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Kamu adalah asisten kesehatan pribadi yang praktis.
Tugasmu menulis bagian saran untuk laporan pagi di Telegram, dalam Bahasa Indonesia santai.

Aturan:
1. Keputusan latihan SUDAH DITENTUKAN oleh sistem. Jangan mengubah intensitasnya,
   cukup jelaskan dalam 1-2 kalimat kenapa itu masuk akal berdasarkan data.
2. Rekomendasikan menu makan untuk sarapan, makan siang, dan makan malam yang
   realistis dibeli atau dimasak di kota pengguna.
3. Sesuaikan gizi dengan kondisi pemulihan: pemulihan rendah butuh protein cukup,
   cairan, dan makanan yang mudah dicerna. Hari latihan berat butuh karbohidrat lebih.
4. Patuhi catatan makanan pengguna (alergi, pantangan, preferensi).
5. Tulis teks biasa tanpa Markdown (tanpa *, #, atau _). Boleh pakai emoji secukupnya.
6. Maksimal 150 kata. Jangan memberi diagnosis medis.
7. Kalau data tidur tidak tersedia, jangan menebak angkanya.
"""

# Percobaan ulang kalau server Google sibuk (error 5xx) atau kena limit (429).
JEDA_PERCOBAAN = (0, 10, 30)  # detik sebelum percobaan ke-1, ke-2, ke-3


def _fmt(nilai, satuan: str = "") -> str:
    return "tidak tersedia" if nilai is None else f"{nilai}{satuan}"


def susun_prompt(m: MetrikHarian, rek: Rekomendasi, b: StatusBudget | None,
                 riwayat: list[dict], kota: str, catatan_makanan: str,
                 catatan_olahraga: str) -> str:
    tren = ", ".join(
        f"{r['tanggal']}: skor {r.get('sleep_score') or '-'}, BB {r.get('body_battery') or '-'}"
        for r in riwayat
    ) or "belum ada"

    bagian_budget = ""
    if b is not None:
        bagian_budget = f"""
BUDGET MAKAN
- Jatah hari ini: {rupiah(b.jatah_hari_ini)}
- Sudah terpakai hari ini: {rupiah(b.terpakai_hari_ini)}
- Sertakan perkiraan harga tiap menu (tulis "sekitar"), dan total TIDAK BOLEH melebihi jatah.
"""

    return f"""DATA PAGI INI
- Sleep score: {_fmt(m.sleep_score)}
- Durasi tidur: {_fmt(m.sleep_jam, ' jam')}
- HRV semalam: {_fmt(m.hrv_semalam, ' ms')} (status: {_fmt(m.hrv_status)})
- Body Battery: {_fmt(m.body_battery)}
- Resting HR: {_fmt(m.resting_hr, ' bpm')}
- Tren 7 hari terakhir: {tren}

KEPUTUSAN SISTEM
- Tingkat pemulihan: {rek.tingkat}
- Latihan hari ini: {rek.latihan}
{bagian_budget}
KONTEKS PENGGUNA
- Kota: {kota}
- Catatan makanan: {catatan_makanan}
- Kebiasaan olahraga: {catatan_olahraga}

Tulis saran latihan singkat dan rencana makan hari ini."""


def _coba_model(client: genai.Client, model: str, prompt: str) -> str | None:
    for i, jeda in enumerate(JEDA_PERCOBAAN, start=1):
        if jeda:
            time.sleep(jeda)
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,
                                                   temperature=0.7),
            )
            teks = (resp.text or "").strip()
            if teks:
                return teks
            log.warning("Gemini (%s) mengembalikan teks kosong", model)
            return None
        except errors.ServerError as e:
            log.warning("Gemini (%s) percobaan %d: server error %s", model, i, e.code)
        except errors.ClientError as e:
            log.warning("Gemini (%s) percobaan %d: client error %s", model, i, e.code)
            if e.code != 429:  # 400/403/404 tidak akan beres dengan dicoba ulang
                return None
        except Exception as e:  # noqa: BLE001 - laporan harus tetap terkirim
            log.warning("Gemini (%s) percobaan %d: %s", model, i, type(e).__name__)
    return None


def buat_saran(api_key: str, model: str, prompt: str,
               model_cadangan: str | None = None) -> str | None:
    """Kembalikan teks saran, atau None kalau Gemini gagal (laporan tetap dikirim)."""
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:  # noqa: BLE001
        log.warning("Gemini client gagal dibuat: %s", type(e).__name__)
        return None
    hasil = _coba_model(client, model, prompt)
    if hasil is None and model_cadangan and model_cadangan != model:
        log.info("Mencoba model cadangan")
        hasil = _coba_model(client, model_cadangan, prompt)
    return hasil
