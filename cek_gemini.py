"""Uji koneksi Gemini dari laptop: python cek_gemini.py

Menampilkan kode error yang jelas kalau gagal, tanpa menampilkan API key.
"""

import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

key = os.environ.get("GEMINI_API_KEY", "").strip()
if not key:
    raise SystemExit("Isi GEMINI_API_KEY di file .env dulu.")

client = genai.Client(api_key=key, http_options=types.HttpOptions(
    timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1)))

models = [os.environ.get("GEMINI_MODEL") or "gemini-flash-latest",
          os.environ.get("GEMINI_MODEL_CADANGAN") or "gemini-flash-lite-latest"]

for model in models:
    print(f"Mencoba {model} ...", flush=True)
    mulai = time.monotonic()
    try:
        r = client.models.generate_content(model=model, contents="Balas dengan satu kata: halo")
        print(f"  OK dalam {time.monotonic() - mulai:.1f} detik -> {(r.text or '').strip()[:50]}")
    except errors.APIError as e:
        print(f"  GAGAL: kode {e.code} {e.status} -> {str(e.message)[:200]}")
    except Exception as e:  # noqa: BLE001
        print(f"  GAGAL: {type(e).__name__} setelah {time.monotonic() - mulai:.1f} detik")
