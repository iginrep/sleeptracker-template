"""Perhitungan budget makan harian dari budget bulanan."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class StatusBudget:
    budget_bulanan: int
    terpakai_bulan_ini: int
    terpakai_hari_ini: int
    sisa_hari: int            # termasuk hari ini
    jatah_hari_ini: int
    sisa_hari_ini: int
    sisa_bulan_ini: int


def hitung_status(budget_bulanan: int, terpakai_sebelum_hari_ini: int,
                  terpakai_hari_ini: int, hari_ini: date) -> StatusBudget:
    """Jatah harian = sisa uang (sebelum hari ini) dibagi sisa hari termasuk hari ini.

    Dengan cara ini, kalau kemarin boros, jatah hari-hari berikutnya otomatis
    mengecil. Kalau kemarin hemat, jatahnya bertambah.
    """
    hari_dalam_bulan = calendar.monthrange(hari_ini.year, hari_ini.month)[1]
    sisa_hari = hari_dalam_bulan - hari_ini.day + 1
    sisa_sebelum = budget_bulanan - terpakai_sebelum_hari_ini
    jatah = max(sisa_sebelum, 0) // sisa_hari
    total_terpakai = terpakai_sebelum_hari_ini + terpakai_hari_ini
    return StatusBudget(
        budget_bulanan=budget_bulanan,
        terpakai_bulan_ini=total_terpakai,
        terpakai_hari_ini=terpakai_hari_ini,
        sisa_hari=sisa_hari,
        jatah_hari_ini=jatah,
        sisa_hari_ini=jatah - terpakai_hari_ini,
        sisa_bulan_ini=budget_bulanan - total_terpakai,
    )


def rupiah(n: int) -> str:
    tanda = "-" if n < 0 else ""
    return f"{tanda}Rp{abs(n):,}".replace(",", ".")


def parse_nominal(teks: str) -> int | None:
    """Terima format '25000', '25.000', '25rb', '25k', '1,5jt'."""
    t = teks.strip().lower().replace("rp", "").replace(" ", "")
    pengali = 1
    for akhiran, kali in (("jt", 1_000_000), ("rb", 1_000), ("k", 1_000)):
        if t.endswith(akhiran):
            t, pengali = t[: -len(akhiran)], kali
            break
    if pengali > 1:
        t = t.replace(",", ".")
        try:
            hasil = int(round(float(t) * pengali))
        except ValueError:
            return None
    else:
        t = t.replace(".", "").replace(",", "")
        if not t.isdigit():
            return None
        hasil = int(t)
    return hasil if hasil > 0 else None
