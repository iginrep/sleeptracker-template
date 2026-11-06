"""Mengambil metrik tidur dan pemulihan dari Garmin Connect Personal API (resmi).

Catatan: dokumentasi Garmin belum menjelaskan nama field di setiap respons JSON.
Karena itu pengambilan nilai di sini dibuat toleran (mencari beberapa kemungkinan
nama field). Jalankan `python cek_garmin.py` untuk melihat respons asli dari
akunmu dan memastikan semua metrik terbaca.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import date
from typing import Any

from garmin_personal_api import (
    GarminPersonalApiClient,
    GarminPersonalApiError,
    HttpError,
    PersonalApiAuthenticator,
)

log = logging.getLogger(__name__)


class GarminAuthError(Exception):
    """API key tidak valid, dicabut, atau kedaluwarsa. Perlu tindakan manual."""


class GarminRateLimitError(Exception):
    """Garmin menolak karena terlalu banyak request. Jangan dicoba ulang hari ini."""


@dataclass
class MetrikHarian:
    tanggal: date
    sleep_score: int | None = None
    sleep_jam: float | None = None
    hrv_semalam: int | None = None
    hrv_status: str | None = None
    body_battery: int | None = None
    resting_hr: int | None = None

    @property
    def ada_data_tidur(self) -> bool:
        return self.sleep_score is not None or self.sleep_jam is not None

    def ke_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tanggal"] = self.tanggal.isoformat()
        return d


# ---------------------------------------------------------------------------
# Pencarian field yang toleran
# ---------------------------------------------------------------------------

def cari(data: Any, *nama_kunci: str) -> Any:
    """Cari nilai pertama (breadth-first) dari salah satu nama kunci, di level mana pun.

    Breadth-first dipakai supaya field ringkasan di level atas didahulukan
    daripada field dengan nama sama di dalam data time series.
    """
    antrean = [data]
    while antrean:
        berikut = []
        for node in antrean:
            if isinstance(node, dict):
                for k in nama_kunci:
                    if k in node and node[k] not in (None, "", [], {}):
                        return node[k]
                berikut.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                berikut.extend(v for v in node if isinstance(v, (dict, list)))
        antrean = berikut
    return None


def _angka(nilai: Any) -> int | None:
    if isinstance(nilai, dict):  # contoh: {"value": 82, "qualifierKey": "GOOD"}
        nilai = nilai.get("value")
    try:
        return int(round(float(nilai)))
    except (TypeError, ValueError):
        return None


def olah_respons(tanggal: date, mentah: dict[str, Any]) -> MetrikHarian:
    """Ubah respons mentah dari beberapa endpoint menjadi MetrikHarian."""
    tidur = mentah.get("sleep")
    hrv = mentah.get("hrv")
    ringkasan = mentah.get("daily_summary")
    bb = mentah.get("body_battery")

    m = MetrikHarian(tanggal=tanggal)

    # Sleep score: biasanya di sleepScores.overall.value
    skor = cari(tidur, "overall")
    m.sleep_score = _angka(skor) if skor is not None else _angka(cari(tidur, "sleepScore", "overallSleepScore"))

    detik = _angka(cari(tidur, "sleepTimeSeconds", "totalSleepTimeSeconds", "sleepTimeInSeconds"))
    if detik:
        m.sleep_jam = round(detik / 3600, 2)

    # Hanya rata-rata semalam. weeklyAvg sengaja tidak dipakai sebagai cadangan
    # karena artinya berbeda (rata-rata 7 hari).
    m.hrv_semalam = _angka(cari(hrv, "lastNightAvg", "lastNightAverage"))
    status = cari(hrv, "status", "hrvStatus")
    m.hrv_status = str(status).upper() if isinstance(status, str) else None

    # Format asli: daily_summary.data[].heartRate.restingValue
    m.resting_hr = _angka(
        cari(ringkasan, "restingValue", "restingHeartRate", "restingHeartRateInBeatsPerMinute")
        or cari(tidur, "restingHeartRate")
    )

    m.body_battery = body_battery_saat_bangun(tidur, bb, ringkasan)
    return m


def body_battery_saat_bangun(tidur: Any, bb: Any, ringkasan: Any) -> int | None:
    """Level Body Battery saat bangun.

    Cara utama: ambil titik di bodyBatteryValuesArray ([timestamp_ms, level]) yang
    paling dekat dengan sleepEndTimestampGMT. Cadangan: nilai tertinggi hari itu
    (bodyBattery.maxValue), yang di pagi hari biasanya sama dengan level saat bangun.
    Field "charged" TIDAK dipakai karena itu jumlah energi yang terisi, bukan level.
    """
    akhir_tidur = cari(tidur, "sleepEndTimestampGMT")
    deret = cari(bb, "bodyBatteryValuesArray")
    if isinstance(akhir_tidur, (int, float)) and isinstance(deret, list):
        terbaik, selisih_terbaik = None, None
        for titik in deret:
            if not (isinstance(titik, list) and len(titik) >= 2):
                continue
            ts, level = titik[0], titik[-1]
            if not isinstance(ts, (int, float)) or not isinstance(level, (int, float)):
                continue
            selisih = abs(ts - akhir_tidur)
            if selisih_terbaik is None or selisih < selisih_terbaik:
                terbaik, selisih_terbaik = level, selisih
        if terbaik is not None and selisih_terbaik <= 90 * 60 * 1000:
            return _angka(terbaik)

    body_battery = cari(ringkasan, "bodyBattery")
    if isinstance(body_battery, dict):
        return _angka(body_battery.get("maxValue"))
    return _angka(cari(ringkasan, "bodyBatteryAtWakeTime", "bodyBatteryHighestValue"))


# ---------------------------------------------------------------------------
# Pengambilan data
# ---------------------------------------------------------------------------

def ambil_mentah(api_key: str, tanggal: date,
                 bagian: tuple[str, ...] | None = None) -> dict[str, Any]:
    """Ambil respons mentah dari Garmin. Hanya membaca, tidak mengubah apa pun.

    `bagian` membatasi endpoint yang dipanggil, mis. ("sleep",) untuk sekadar
    mengecek apakah data tidur sudah tersinkron (lebih hemat request).
    """
    try:
        with PersonalApiAuthenticator() as auth:
            token = auth.obtain_token(api_key)
    except HttpError as e:
        if e.status_code in (401, 403):
            raise GarminAuthError("API key Garmin ditolak") from None
        if e.status_code == 429:
            raise GarminRateLimitError("Garmin membatasi request") from None
        raise

    hasil: dict[str, Any] = {}
    permintaan = {
        "sleep": lambda c: c.get_daily_sleep(tanggal),
        "hrv": lambda c: c.get_daily_hrv(tanggal),
        "daily_summary": lambda c: c.get_daily_summaries(tanggal, tanggal),
        "body_battery": lambda c: c.get_daily_body_battery(tanggal, tanggal),
    }
    if bagian:
        permintaan = {k: v for k, v in permintaan.items() if k in bagian}
    with GarminPersonalApiClient(token.access_token) as client:
        for nama, fungsi in permintaan.items():
            try:
                hasil[nama] = fungsi(client)
            except HttpError as e:
                if e.status_code in (401, 403):
                    raise GarminAuthError("Token Garmin ditolak") from None
                if e.status_code == 429:
                    raise GarminRateLimitError("Garmin membatasi request") from None
                # Endpoint lain tetap dicoba. Isi respons tidak dicetak ke log.
                log.warning("Endpoint Garmin '%s' gagal (HTTP %s)", nama, e.status_code)
                hasil[nama] = None
            except GarminPersonalApiError:
                log.warning("Endpoint Garmin '%s' gagal", nama)
                hasil[nama] = None
    return hasil


def ambil_metrik(api_key: str, tanggal: date) -> MetrikHarian:
    return olah_respons(tanggal, ambil_mentah(api_key, tanggal))


def tidur_sudah_tersedia(api_key: str, tanggal: date) -> bool:
    """Cek ringan: hanya memanggil endpoint tidur."""
    mentah = ambil_mentah(api_key, tanggal, bagian=("sleep",))
    return olah_respons(tanggal, mentah).ada_data_tidur
