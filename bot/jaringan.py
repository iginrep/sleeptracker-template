"""Percobaan ulang untuk request HTTP yang gagal karena gangguan sesaat."""

from __future__ import annotations

import logging
import time
from typing import Callable

import requests

log = logging.getLogger(__name__)

JEDA_ULANG = (0, 3, 10)  # detik sebelum percobaan ke-1, ke-2, ke-3
STATUS_SEMENTARA = {429, 500, 502, 503, 504}


class GagalJaringan(Exception):
    """Semua percobaan gagal karena masalah jaringan (tanpa respons dari server)."""


def dengan_ulang(kirim: Callable[[], requests.Response], nama: str, *,
                 ulang_jika_timeout: bool = True) -> requests.Response:
    """Jalankan `kirim()` dan ulangi kalau gagal karena gangguan sesaat.

    - Gagal tersambung (ConnectionError, ConnectTimeout): selalu diulang,
      karena request pasti belum sampai ke server.
    - ReadTimeout: request mungkin sudah sampai. Hanya diulang kalau aman
      (ulang_jika_timeout=True), supaya pesan Telegram tidak terkirim dobel.
    - Status 429/5xx: diulang. Status lain dikembalikan apa adanya.
    """
    terakhir: requests.Response | None = None
    for i, jeda in enumerate(JEDA_ULANG, start=1):
        if jeda:
            time.sleep(jeda)
        try:
            r = kirim()
        except requests.exceptions.ReadTimeout:
            log.warning("%s percobaan %d: timeout", nama, i)
            if not ulang_jika_timeout:
                raise GagalJaringan(nama) from None
            continue
        except requests.RequestException as e:
            # Pesan asli tidak dicetak karena bisa memuat URL berisi token.
            log.warning("%s percobaan %d: %s", nama, i, type(e).__name__)
            continue
        if r.status_code in STATUS_SEMENTARA:
            log.warning("%s percobaan %d: HTTP %s", nama, i, r.status_code)
            terakhir = r
            continue
        return r
    if terakhir is not None:
        return terakhir
    raise GagalJaringan(nama)
