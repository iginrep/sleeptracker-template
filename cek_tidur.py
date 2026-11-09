"""Diagnosis data tidur: python cek_tidur.py [YYYY-MM-DD]

Menampilkan apakah Garmin punya data tidur untuk kemarin dan hari ini, beserta jam
tidur dan bangun. Tidak menampilkan API key. Respons mentah disimpan ke samples/.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from garmin_personal_api import GarminPersonalApiClient, PersonalApiAuthenticator

load_dotenv()
key = os.environ.get("GARMIN_PERSONAL_API_KEY", "").strip()
if not key:
    sys.exit("Isi GARMIN_PERSONAL_API_KEY di .env dulu.")

hari = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
tanggal = [hari - timedelta(days=1), hari]


def jam_lokal(ms):
    if not isinstance(ms, (int, float)):
        return "-"
    # Timestamp "Local" dari Garmin sudah waktu lokal, jadi dibaca sebagai UTC.
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%d/%m %H:%M")


with PersonalApiAuthenticator() as auth:
    token = auth.obtain_token(key)

Path("samples").mkdir(exist_ok=True)
with GarminPersonalApiClient(token.access_token) as c:
    for t in tanggal:
        print(f"\n=== dailySleep tanggal {t} ===")
        d = c.get_daily_sleep(t)
        Path(f"samples/{t}_sleep.json").write_text(json.dumps(d, indent=2), encoding="utf-8")
        if not d:
            print("  respons kosong")
            continue
        dto = d.get("dailySleepDTO", d)
        skor = ((dto.get("sleepScores") or {}).get("overall") or {}).get("value")
        print("  calendarDate      :", dto.get("calendarDate"))
        print("  mulai tidur       :", jam_lokal(dto.get("sleepStartTimestampLocal")))
        print("  bangun            :", jam_lokal(dto.get("sleepEndTimestampLocal")))
        print("  durasi tidur (mnt):", (dto.get("sleepTimeSeconds") or 0) // 60)
        print("  durasi nap (mnt)  :", (dto.get("napTimeSeconds") or 0) // 60)
        print("  sleep score       :", skor)
        print("  window confirmed  :", dto.get("sleepWindowConfirmed"),
              dto.get("sleepWindowConfirmationType"))

        s = c.get_daily_sleep_summaries(t, t)
        Path(f"samples/{t}_sleep_summary.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
        print("  sleep summary     :", "ada isi" if s else "kosong")
