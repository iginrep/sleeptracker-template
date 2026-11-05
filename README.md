# Sleeptracker: Personal Health & Productivity Bot

Bot Telegram yang setiap pagi mengirim laporan tidur dan pemulihan dari Garmin,
rekomendasi latihan, dan rencana makan sesuai sisa budget.

```
GitHub Actions (cek tiap 30 menit, 06.07 - 10.07 WIB)
   │
   ├─ Telegram  : baca perintah baru (/catat, /budget, ...)
   ├─ Garmin    : ambil tidur, HRV, Body Battery, resting HR (Personal API resmi, read-only)
   ├─ Aturan    : tentukan tingkat pemulihan + latihan (bukan AI, supaya konsisten)
   ├─ Supabase  : simpan metrik, hitung sisa budget
   ├─ Gemini    : susun saran menu (hanya menerima angka ringkasan)
   └─ Telegram  : kirim laporan
```

## Struktur

| File | Fungsi |
|---|---|
| `main.py` | Titik masuk (`pagi` atau `sinkron`) |
| `cek_garmin.py` | Uji koneksi Garmin dari laptop |
| `bot/garmin_data.py` | Ambil data Garmin |
| `bot/recovery.py` | Aturan pemulihan dan latihan |
| `bot/budget.py` | Hitung jatah makan harian |
| `bot/ai.py` | Prompt Gemini |
| `bot/commands.py` | Perintah Telegram |
| `bot/db.py`, `bot/telegram.py` | Akses Supabase dan Telegram |
| `supabase/schema.sql` | Tabel database |
| `.github/workflows/` | Jadwal otomatis |

---

## Setup (sekali saja)

### 1. Install di laptop (Windows, PowerShell di VS Code)

Butuh **Python 3.12 atau lebih baru** (syarat library resmi Garmin).

```powershell
cd C:\Users\IGIN\Downloads\sleeptracker
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Kalau muncul error "running scripts is disabled", jalankan sekali:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 2. Supabase

1. Buka project Supabase > **SQL Editor** > **New query**.
2. Tempel isi `supabase/schema.sql` > **Run**.
3. Ambil **Project URL** dan **secret key** (atau `service_role` key) di **Project Settings > API Keys**.
   Jangan pakai publishable/anon key.

### 3. Telegram

1. Chat **@BotFather** > `/newbot` > simpan **token**.
2. Chat **@userinfobot** > simpan angka **Id** kamu (ini `TELEGRAM_CHAT_ID`).
3. Buka bot kamu sendiri dan kirim `/start` sekali.

### 4. Gemini

Buka **aistudio.google.com** > **Get API key**. Cek batas free tier di halaman rate limit AI Studio.

### 5. Isi `.env`

Salin `.env.example` menjadi `.env`, lalu isi semua nilainya. File ini tidak akan ter-upload.

### 6. Uji di laptop

```powershell
python -m unittest discover tests     # tes logika, tanpa internet
python cek_garmin.py                  # cek data Garmin
python main.py pagi                   # paksa kirim laporan ke Telegram sekarang
```

`cek_garmin.py` menyimpan respons mentah ke folder `samples/`. Kalau ada metrik
yang tampil "-", buka file JSON terkait dan cari nama field-nya, supaya parser
di `bot/garmin_data.py` bisa disesuaikan. Folder ini tidak ikut ter-upload.

### 7. Upload ke GitHub (repo private)

```powershell
git init
git add .
git status        # PASTIKAN .env dan samples/ TIDAK ada di daftar
git commit -m "Versi awal sleeptracker"
git branch -M main
git remote add origin https://github.com/USERNAME/NAMA-REPO.git
git push -u origin main
```

### 8. GitHub Secrets dan Variables

Repo > **Settings > Secrets and variables > Actions**.

Tab **Secrets** (terenkripsi, tidak bisa dibaca lagi setelah disimpan):

| Nama | Isi |
|---|---|
| `GARMIN_PERSONAL_API_KEY` | API key Garmin |
| `SUPABASE_URL` | URL project Supabase |
| `SUPABASE_SECRET_KEY` | secret / service_role key |
| `GEMINI_API_KEY` | API key Gemini |
| `TELEGRAM_BOT_TOKEN` | token dari BotFather |
| `TELEGRAM_CHAT_ID` | Id dari userinfobot |

Tab **Variables** (bukan rahasia, opsional):

| Nama | Contoh |
|---|---|
| `KOTA` | `Bandung` |
| `CATATAN_MAKANAN` | `halal, tidak suka pare, lebih sering beli di warung` |
| `CATATAN_OLAHRAGA` | `lari 3x seminggu, persiapan 10K` |
| `GEMINI_MODEL` | kosongkan untuk pakai `gemini-flash-latest` |
| `GEMINI_MODEL_CADANGAN` | kosongkan untuk pakai `gemini-flash-lite-latest` |
| `FITUR_BUDGET` | `true` untuk mengaktifkan budget makan (default nonaktif) |

### 9. Tes di GitHub

Tab **Actions** > **Laporan Pagi** > **Run workflow**. Kalau pesan masuk ke Telegram, selesai.

---

## Jadwal

| Workflow | Waktu (WIB) | Fungsi |
|---|---|---|
| Laporan Pagi | tiap 30 menit, 06.07 sampai 10.07 | proses perintah, cek apakah data tidur sudah tersinkron, kirim laporan sekali per hari |
| Sinkron | 11.17, 14.17, 17.17, 20.17, 23.17 | proses perintah (`/catat`, `/sisa`, dll.) |

Cara kerja Laporan Pagi: begitu jam Garmin tersinkron ke HP setelah kamu bangun,
laporan dikirim pada pengecekan berikutnya. Kalau sampai 10.07 data belum ada,
laporan tetap dikirim dengan catatan. Semua berjalan di server GitHub, laptop boleh mati.

Jadwal GitHub bisa telat beberapa menit. Ubah jam di file `.github/workflows/*.yml`
(ingat cron memakai UTC, WIB = UTC + 7). Kalau batas jam diubah, sesuaikan juga
`JAM_BATAS_LAPORAN` di `main.py`.

## Perintah Telegram

Perintah budget (`/catat`, `/sisa`, `/budget`, `/batal`) hanya aktif kalau `FITUR_BUDGET=true`.

```
/catat 25000 nasi padang   catat pengeluaran makan
/sisa                      sisa budget hari ini dan bulan ini
/budget 1500000            ubah budget makan bulanan
/batal                     hapus catatan terakhir
/laporan                   kirim ulang laporan pagi
/help                      daftar perintah
```

Balasan datang saat workflow berikutnya berjalan, bukan seketika.
Tanggal pengeluaran mengikuti waktu kamu mengirim pesan, bukan waktu diproses.

## Cara hitung budget

`jatah hari ini = (budget bulanan - terpakai sebelum hari ini) / sisa hari termasuk hari ini`

Kalau kemarin boros, jatah hari berikutnya otomatis mengecil, dan sebaliknya.

## Perawatan

- **API key Garmin punya masa berlaku** (pilihan 30 hari sampai 1 tahun). Garmin mengirim email
  sekitar seminggu sebelum habis. Buat key baru, lalu perbarui secret `GARMIN_PERSONAL_API_KEY`.
  Kalau key ditolak, bot juga memberi tahu lewat Telegram.
- **Ambang pemulihan** di `bot/recovery.py` adalah titik awal. Sesuaikan setelah beberapa minggu.
- **Supabase free tier** dijeda kalau tidak aktif seminggu. Bot menulis data setiap hari, jadi aman.

## Keamanan

- Repo **private**. Semua kredensial hanya di `.env` (lokal) dan GitHub Secrets.
- Log GitHub Actions hanya berisi status, tidak pernah angka kesehatan atau uang.
- Bot mengabaikan pesan dari chat selain `TELEGRAM_CHAT_ID`.
- Supabase memakai Row Level Security tanpa policy, jadi hanya secret key yang bisa mengakses.
- Garmin diakses lewat **Personal API resmi**, hanya membaca data.
- Ke Gemini hanya dikirim angka ringkasan tanpa identitas.
- Versi library dikunci di `requirements.txt`.

Bot ini bukan alat medis. Rekomendasinya bersifat umum. Kalau merasa sakit, istirahat dan konsultasi ke tenaga kesehatan.
