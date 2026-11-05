"""Telegram Bot API lewat requests (tanpa library tambahan)."""

from __future__ import annotations

from typing import Any

import requests

BATAS_PANJANG = 4000  # batas Telegram 4096 karakter per pesan


class Telegram:
    def __init__(self, token: str, chat_id: str, timeout: float = 20):
        self._base = f"https://api.telegram.org/bot{token}"
        self.chat_id = str(chat_id)
        self.timeout = timeout

    def _call(self, metode: str, **data: Any) -> Any:
        try:
            r = requests.post(f"{self._base}/{metode}", json=data, timeout=self.timeout)
        except requests.RequestException:
            # Pesan error asli requests memuat URL yang berisi token, jadi diganti.
            raise RuntimeError(f"Telegram {metode} gagal (masalah jaringan)") from None
        if not r.ok:
            # URL berisi token, jadi yang ditampilkan hanya nama metode dan status.
            raise RuntimeError(f"Telegram {metode} gagal (HTTP {r.status_code})")
        return r.json().get("result")

    def kirim(self, teks: str) -> None:
        """Kirim teks biasa (tanpa Markdown supaya tidak error karena simbol)."""
        for i in range(0, len(teks), BATAS_PANJANG):
            self._call("sendMessage", chat_id=self.chat_id, text=teks[i:i + BATAS_PANJANG],
                       disable_web_page_preview=True)

    def ambil_pesan(self, offset: int | None) -> list[dict[str, Any]]:
        """Ambil pesan baru. Telegram menyimpan pesan yang belum diambil hingga 24 jam."""
        data: dict[str, Any] = {"timeout": 0, "allowed_updates": ["message"]}
        if offset is not None:
            data["offset"] = offset
        return self._call("getUpdates", **data) or []
