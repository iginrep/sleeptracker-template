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
Tugasmu menulis bagian catatan untuk laporan pagi di Telegram, dalam Bahasa Indonesia santai.

Aturan umum:
1. Keputusan latihan SUDAH DITENTUKAN oleh sistem. Jangan mengubah intensitasnya.
2. Ikuti bagian TUGAS di pesan pengguna, termasuk batas jumlah kata.
3. Tulis teks biasa tanpa Markdown (tanpa *, #, atau _). Boleh pakai emoji secukupnya.
4. Jangan memberi diagnosis medis.
5. Kalau data tidur tidak tersedia, jangan menebak angkanya.
6. Kalau menyebut angka, salin persis dari data beserta satuannya. Jangan mengubah,
   menggabungkan, atau menghitung ulang angka. Sleep score tidak punya satuan jam.
7. Kalau tren tertulis "belum cukup data", jangan membandingkan dengan tren.
"""

TUGAS_TANPA_MAKANAN = """TUGAS
Tulis 2-3 kalimat (maksimal 60 kata):
- Artikan kondisi tidur dan pemulihan pagi ini, bandingkan dengan tren 7 hari kalau ada.
- Jelaskan singkat kenapa latihan yang ditentukan sistem masuk akal.
- Beri satu tips praktis untuk hari ini (mis. hidrasi, jam tidur malam nanti, pemanasan).
JANGAN membahas makanan atau menu."""

TUGAS_DENGAN_MAKANAN = """TUGAS
Tulis maksimal 150 kata:
- Jelaskan dalam 1-2 kalimat kenapa latihan yang ditentukan sistem masuk akal.
- Rekomendasikan menu sarapan, makan siang, dan makan malam yang realistis dibeli
  atau dimasak di kota pengguna.
- Sesuaikan gizi dengan pemulihan: pemulihan rendah butuh protein cukup, cairan, dan
  makanan mudah dicerna. Hari latihan berat butuh karbohidrat lebih.
- Patuhi catatan makanan pengguna (alergi, pantangan, preferensi)."""

# Percobaan ulang kalau server Google sibuk (error 5xx) atau kena limit (429).
JEDA_PERCOBAAN = (0, 5, 15)   # detik sebelum percobaan ke-1, ke-2, ke-3
BATAS_WAKTU_REQUEST_MS = 30_000  # satu request paling lama 30 detik
BATAS_TOTAL_DETIK = 120          # semua percobaan (termasuk model cadangan) maks 2 menit


def _fmt(nilai, satuan: str = "") -> str:
    return "tidak tersedia" if nilai is None else f"{nilai}{satuan}"


def format_durasi(jam: float | None) -> str | None:
    """4.92 -> '4 jam 55 menit'."""
    if jam is None:
        return None
    total_menit = round(jam * 60)
    return f"{total_menit // 60} jam {total_menit % 60} menit"


def ringkas_tren(riwayat: list[dict], minimal_hari: int = 3) -> str:
    """Ringkasan hari-hari SEBELUM hari ini. Riwayat tidak boleh berisi hari ini."""
    if len(riwayat) < minimal_hari:
        return f"belum cukup data (baru {len(riwayat)} hari tercatat sebelum hari ini)"

    def rata(kolom: str) -> str:
        nilai = [r[kolom] for r in riwayat if r.get(kolom) is not None]
        return f"{sum(nilai) / len(nilai):.0f}" if nilai else "-"

    return (f"rata-rata {len(riwayat)} hari sebelumnya: sleep score {rata('sleep_score')}, "
            f"Body Battery saat bangun {rata('body_battery')}, HRV {rata('hrv_semalam')} ms")


def susun_prompt(m: MetrikHarian, rek: Rekomendasi, b: StatusBudget | None,
                 riwayat: list[dict], kota: str, catatan_makanan: str,
                 catatan_olahraga: str, makanan: bool = True) -> str:
    tren = ringkas_tren(riwayat)
    konteks_makanan = (f"- Kota: {kota}\n- Catatan makanan: {catatan_makanan}\n"
                       if makanan else "")

    bagian_budget = ""
    if makanan and b is not None:
        bagian_budget = f"""
BUDGET MAKAN
- Jatah hari ini: {rupiah(b.jatah_hari_ini)}
- Sudah terpakai hari ini: {rupiah(b.terpakai_hari_ini)}
- Sertakan perkiraan harga tiap menu (tulis "sekitar"), dan total TIDAK BOLEH melebihi jatah.
"""

    return f"""DATA PAGI INI
- Sleep score: {_fmt(m.sleep_score)}
- Durasi tidur: {_fmt(format_durasi(m.sleep_jam))}
- HRV semalam: {_fmt(m.hrv_semalam, ' ms')} (status: {_fmt(m.hrv_status)})
- {"Body Battery saat bangun" if m.ada_data_tidur else "Body Battery tertinggi hari ini (data tidur belum ada, jam mungkin tidak dipakai semalam)"}: {_fmt(m.body_battery)}
- Resting HR: {_fmt(m.resting_hr, ' bpm')}
- Tren: {tren}

KEPUTUSAN SISTEM
- Tingkat pemulihan: {rek.tingkat}
- Latihan hari ini: {rek.latihan}
{bagian_budget}
KONTEKS PENGGUNA
- Kebiasaan olahraga: {catatan_olahraga}
{konteks_makanan}
{TUGAS_DENGAN_MAKANAN if makanan else TUGAS_TANPA_MAKANAN}"""


def _coba_model(client: genai.Client, model: str, prompt: str, tenggat: float) -> str | None:
    for i, jeda in enumerate(JEDA_PERCOBAAN, start=1):
        if time.monotonic() + jeda >= tenggat:
            log.warning("Gemini (%s): batas waktu total tercapai", model)
            return None
        if jeda:
            time.sleep(jeda)
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,
                                                   temperature=0.3),
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
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=BATAS_WAKTU_REQUEST_MS,
                # Percobaan ulang diatur sendiri di atas, jadi bawaan SDK dimatikan.
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
    except Exception as e:  # noqa: BLE001
        log.warning("Gemini client gagal dibuat: %s", type(e).__name__)
        return None
    tenggat = time.monotonic() + BATAS_TOTAL_DETIK
    hasil = _coba_model(client, model, prompt, tenggat)
    if hasil is None and model_cadangan and model_cadangan != model:
        log.info("Mencoba model cadangan")
        hasil = _coba_model(client, model_cadangan, prompt, tenggat)
    return hasil
