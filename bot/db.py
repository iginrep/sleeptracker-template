"""Akses Supabase lewat REST API (PostgREST) memakai requests.

Sengaja tidak memakai library supabase-py supaya dependensi lebih sedikit.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import requests


class Database:
    def __init__(self, url: str, key: str, timeout: float = 20):
        self.base = f"{url}/rest/v1"
        self.timeout = timeout
        self.headers = {"apikey": key, "Content-Type": "application/json"}
        # Key lama (format JWT "eyJ...") juga perlu dikirim di header Authorization.
        # Secret key format baru ("sb_secret_...") cukup lewat header apikey.
        if key.startswith("eyJ"):
            self.headers["Authorization"] = f"Bearer {key}"

    def _req(self, method: str, tabel: str, *, params=None, json=None, prefer=None) -> Any:
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        r = requests.request(method, f"{self.base}/{tabel}", headers=headers,
                             params=params, json=json, timeout=self.timeout)
        if not r.ok:
            # Tidak menampilkan isi data, hanya status.
            raise RuntimeError(f"Supabase {method} {tabel} gagal (HTTP {r.status_code})")
        return r.json() if r.content else None

    # --- settings ---------------------------------------------------------
    def get_setting(self, kunci: str, default: str | None = None) -> str | None:
        rows = self._req("GET", "settings", params={"kunci": f"eq.{kunci}", "select": "nilai"})
        return rows[0]["nilai"] if rows else default

    def set_setting(self, kunci: str, nilai: str) -> None:
        self._req("POST", "settings", params={"on_conflict": "kunci"},
                  json={"kunci": kunci, "nilai": nilai},
                  prefer="resolution=merge-duplicates,return=minimal")

    # --- daily_metrics ----------------------------------------------------
    def simpan_metrik(self, data: dict[str, Any]) -> None:
        self._req("POST", "daily_metrics", params={"on_conflict": "tanggal"}, json=data,
                  prefer="resolution=merge-duplicates,return=minimal")

    def metrik_terakhir(self, jumlah: int = 7) -> list[dict[str, Any]]:
        return self._req("GET", "daily_metrics", params={
            "select": "*", "order": "tanggal.desc", "limit": str(jumlah)}) or []

    # --- expenses ---------------------------------------------------------
    def catat_pengeluaran(self, tanggal: date, nominal: int, keterangan: str,
                          message_id: int | None) -> None:
        # ignore-duplicates: kalau message_id sama sudah tercatat, dilewati.
        self._req("POST", "expenses", params={"on_conflict": "telegram_message_id"},
                  json={"tanggal": tanggal.isoformat(), "nominal": nominal,
                        "keterangan": keterangan, "telegram_message_id": message_id},
                  prefer="resolution=ignore-duplicates,return=minimal")

    def pengeluaran_antara(self, mulai: date, sampai: date) -> list[dict[str, Any]]:
        return self._req("GET", "expenses", params=[
            ("select", "id,tanggal,nominal,keterangan"),
            ("tanggal", f"gte.{mulai.isoformat()}"),
            ("tanggal", f"lte.{sampai.isoformat()}"),
            ("order", "id.asc"),
        ]) or []

    def hapus_pengeluaran_terakhir(self) -> dict[str, Any] | None:
        rows = self._req("GET", "expenses", params={
            "select": "id,nominal,keterangan", "order": "id.desc", "limit": "1"})
        if not rows:
            return None
        self._req("DELETE", "expenses", params={"id": f"eq.{rows[0]['id']}"})
        return rows[0]
