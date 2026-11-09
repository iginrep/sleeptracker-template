"""Aturan pemulihan dan rekomendasi latihan.

Keputusan latihan dibuat dengan aturan yang pasti (bukan oleh AI), supaya
hasilnya konsisten dan mudah dievaluasi. AI hanya merangkai kalimat dan menu.

Ambang batas:
- Sleep score mengikuti kategori Garmin: Excellent 90-100, Good 80-89,
  Fair 60-79, Poor di bawah 60.
- HRV status mengikuti label Garmin (BALANCED, UNBALANCED, LOW, POOR).
- Ambang Body Battery adalah titik awal heuristik, bukan standar resmi.
  Silakan disesuaikan setelah beberapa minggu melihat datamu sendiri.

Ini bukan saran medis. Kalau merasa sakit atau kelelahan berat, istirahat.
"""

from __future__ import annotations

from dataclasses import dataclass

from .garmin_data import MetrikHarian

BAIK, CUKUP, KURANG = 2, 1, 0


def nilai_sleep_score(skor: int | None) -> int | None:
    if skor is None:
        return None
    if skor >= 80:
        return BAIK
    if skor >= 60:
        return CUKUP
    return KURANG


def nilai_body_battery(bb: int | None) -> int | None:
    if bb is None:
        return None
    if bb >= 70:
        return BAIK
    if bb >= 40:
        return CUKUP
    return KURANG


def nilai_hrv_status(status: str | None) -> int | None:
    if not status:
        return None
    s = status.upper()
    if s.startswith("BALANCED"):
        return BAIK
    if s.startswith("UNBALANCED"):
        return CUKUP
    if s.startswith("LOW") or s.startswith("POOR"):
        return KURANG
    return None  # mis. "NONE" saat baseline HRV belum terbentuk


@dataclass(frozen=True)
class Rekomendasi:
    tingkat: str          # "tinggi" | "sedang" | "rendah" | "tidak diketahui"
    latihan: str
    alasan: list[str]


LATIHAN = {
    "tinggi": "Siap untuk sesi berkualitas: tempo atau interval sesuai rencana, "
              "atau lari zona 2-3 selama 40-60 menit.",
    "sedang": "Lari santai zona 2 selama 30-40 menit. Hindari interval hari ini.",
    "rendah": "Istirahat aktif: jalan kaki 20-30 menit, stretching, atau mobilitas ringan.",
    "tidak diketahui": "Data pemulihan belum lengkap. Dengarkan badan: kalau terasa segar, "
                       "lari santai zona 2. Kalau capek, istirahat aktif.",
}


def tentukan_rekomendasi(m: MetrikHarian) -> Rekomendasi:
    penilaian = {
        "Sleep score": nilai_sleep_score(m.sleep_score),
        "Body Battery": nilai_body_battery(m.body_battery),
        "Status HRV": nilai_hrv_status(m.hrv_status),
    }
    tersedia = {k: v for k, v in penilaian.items() if v is not None}

    if not tersedia:
        return Rekomendasi("tidak diketahui", LATIHAN["tidak diketahui"], ["Data Garmin belum tersedia"])

    label = {BAIK: "baik", CUKUP: "cukup", KURANG: "kurang"}
    alasan = [f"{k} {label[v]}" for k, v in tersedia.items()]
    jumlah_kurang = sum(1 for v in tersedia.values() if v == KURANG)
    rata_rata = sum(tersedia.values()) / len(tersedia)

    # Body Battery sangat rendah langsung dianggap pemulihan rendah.
    if jumlah_kurang >= 2 or (m.body_battery is not None and m.body_battery < 25):
        tingkat = "rendah"
    elif jumlah_kurang == 1 or rata_rata < 1.5:
        tingkat = "sedang"
    else:
        tingkat = "tinggi"

    if not m.ada_data_tidur:
        alasan.append("tanpa data tidur, kurang akurat")
    return Rekomendasi(tingkat, LATIHAN[tingkat], alasan)
