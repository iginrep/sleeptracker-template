# Sleeptracker: Bot Laporan Tidur Garmin ke Telegram

Bot pribadi yang setiap pagi mengirim laporan tidur dan pemulihan dari smartwatch Garmin
ke Telegram, lengkap dengan rekomendasi latihan dan catatan singkat dari AI.

Semua layanan yang dipakai **gratis**, dan bot berjalan di server GitHub. **Tidak perlu VPS,
dan laptop boleh mati.**

```
cron-job.org (tiap 30 menit pagi hari)
   │  memicu
   ▼
GitHub Actions ──► Garmin Personal API : sleep score, durasi, HRV, Body Battery, resting HR
       │
       ├──► Aturan pemulihan            : tingkat pemulihan + rekomendasi latihan
       ├──► Supabase                    : simpan riwayat untuk tren
       ├──► Google Gemini               : catatan singkat (hanya menerima angka ringkasan)
       └──► Telegram                    : kirim laporan ke chat pribadimu
```

Contoh laporan:

```
☀️ Laporan Pagi, Sabtu 07/11/2026

😴 TIDUR & PEMULIHAN
Sleep score: 72
Durasi tidur: 7 jam 5 menit
HRV semalam: 61 ms (BALANCED)
Body Battery saat bangun: 78
Resting HR: 54 bpm

🟢 Pemulihan: TINGGI
(Sleep score cukup, Body Battery baik, Status HRV baik)

🏃 LATIHAN HARI INI
Siap untuk sesi berkualitas: tempo atau interval sesuai rencana, atau lari zona 2-3 selama 40-60 menit.

🤖 CATATAN AI
...
```

> Bot ini bukan alat medis. Rekomendasinya bersifat umum. Kalau merasa sakit atau
> kelelahan berat, istirahat dan konsultasi ke tenaga kesehatan.

---

## Daftar isi

1. [Yang perlu disiapkan](#1-yang-perlu-disiapkan)
2. [Buat repo kamu sendiri](#2-buat-repo-kamu-sendiri)
3. [Install di laptop](#3-install-di-laptop)
4. [API key Garmin](#4-api-key-garmin)
5. [Bot Telegram](#5-bot-telegram)
6. [Database Supabase](#6-database-supabase)
7. [API key Gemini](#7-api-key-gemini)
8. [Isi file .env](#8-isi-file-env)
9. [Uji di laptop](#9-uji-di-laptop)
10. [Upload ke GitHub](#10-upload-ke-github)
11. [Isi Secrets dan Variables di GitHub](#11-isi-secrets-dan-variables-di-github)
12. [Tes di GitHub](#12-tes-di-github)
13. [Pemicu tepat waktu dengan cron-job.org](#13-pemicu-tepat-waktu-dengan-cron-joborg)
14. [Cara kerja harian](#14-cara-kerja-harian)
15. [Perintah Telegram](#15-perintah-telegram)
16. [Perawatan](#16-perawatan)
17. [Mengatasi masalah](#17-mengatasi-masalah)
18. [Keamanan dan privasi](#18-keamanan-dan-privasi)
19. [Struktur proyek](#19-struktur-proyek)

---

## 1. Yang perlu disiapkan

**Perangkat**
- Smartwatch Garmin yang mendukung pelacakan tidur, dan aplikasi **Garmin Connect** di HP.
- Laptop atau PC (panduan ini memakai Windows, tapi Mac dan Linux juga bisa).

**Software di laptop**
- **Python 3.12 atau lebih baru.** Library resmi Garmin mensyaratkan versi ini.
  Cek dengan `py --list` (Windows) atau `python3 --version`.
  Kalau belum ada, unduh dari python.org dan **centang "Add python.exe to PATH"** saat install.
- **Git.** Cek dengan `git --version`. Kalau belum ada, install dari git-scm.com
  atau jalankan `winget install Git.Git` di CMD.
- Editor teks, misalnya **Visual Studio Code**.

**Akun (semua gratis)**
- GitHub
- Telegram
- Supabase
- Google (untuk Gemini lewat Google AI Studio)
- cron-job.org

---

## 2. Buat repo kamu sendiri

Setiap orang memakai repo, database, bot, dan API key **miliknya sendiri**. Jangan memakai
punya orang lain.

1. Di halaman repo template ini, klik **Use this template > Create a new repository**.
2. Isi nama repo, misalnya `sleeptracker`.
3. Pilih **Private**. Ini penting, karena log GitHub Actions bisa dilihat siapa pun kalau repo public.
4. Klik **Create repository**.
5. Clone ke laptop (ganti `USERNAME` dengan username GitHub kamu):

```cmd
git clone https://github.com/USERNAME/sleeptracker.git
cd sleeptracker
```

---

## 3. Install di laptop

Jalankan di folder proyek.

**CMD (Command Prompt):**
```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

**PowerShell:**
```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Kalau versi Python kamu 3.13, ganti `-3.12` jadi `-3.13`.

Setelah aktif, baris perintah diawali `(.venv)`. **Setiap kali membuka terminal baru,
aktifkan lagi** dengan perintah baris kedua. Kalau lupa, akan muncul error
`No module named 'garmin_personal_api'`.

Cek instalasi dengan menjalankan tes (tidak butuh internet atau API key):
```cmd
python -m unittest discover tests
```
Hasil yang benar diakhiri `OK`.

---

## 4. API key Garmin

Bot memakai **Garmin Connect Personal API resmi**. Aksesnya hanya membaca data akunmu
sendiri, jadi tidak berisiko diblokir seperti library tidak resmi.

1. Login ke **connect.garmin.com** lewat browser di laptop.
2. Buka halaman Personal API Token:
   `https://connect.garmin.com/app/settings/personalApiToken`
3. Buat key baru, setujui syarat penggunaan, lalu pilih masa berlaku
   (30 hari, 90 hari, 180 hari, atau 1 tahun). **Pilih 1 tahun** supaya tidak sering mengganti.
4. **Salin key-nya sekarang**, karena hanya ditampilkan sekali. Simpan sementara di tempat aman.

Dokumentasi resmi: developer.garmin.com/gc-developer-program/personal/personal-api

---

## 5. Bot Telegram

1. Di Telegram, cari **@BotFather**, kirim `/newbot`, lalu ikuti langkahnya.
   Username bot harus diakhiri `bot`. BotFather akan memberi **token**.
2. Cari **@userinfobot**, kirim pesan apa saja. Dia membalas dengan **Id** kamu (angka).
   Ini `TELEGRAM_CHAT_ID`.
3. Buka bot buatanmu dan tekan **Start**. Wajib, karena bot tidak bisa mengirim pesan
   duluan ke orang yang belum pernah memulai chat.

Bot hanya merespons chat ID ini. Pesan dari orang lain diabaikan.

---

## 6. Database Supabase

1. Di **supabase.com**, buat project baru. Region terdekat ke Indonesia, misalnya Singapore.
2. Buka **SQL Editor** (ikon `>_` di sidebar kiri) > **New query**.
3. Buka file `supabase/schema.sql` di VS Code, salin **seluruh isinya** (Ctrl+A, Ctrl+C),
   tempel di SQL Editor, lalu klik **Run**.
   Hasil yang benar: `Success. No rows returned`.
4. Cek di **Table Editor**: harus ada tabel `daily_metrics`, `expenses`, dan `settings`.
5. Buka **Project Settings** (ikon gerigi) > **API Keys**, lalu catat:
   - **Project URL**, contoh `https://abcdefgh.supabase.co`
   - **Secret key** (diawali `sb_secret_...`). Kalau hanya ada tab Legacy, pakai
     **`service_role`** (diawali `eyJ...`).

   **Jangan** pakai publishable atau anon key. Tabel dilindungi Row Level Security,
   jadi key itu tidak punya akses.

---

## 7. API key Gemini

1. Buka **aistudio.google.com** dan login dengan akun Google.
2. Klik **Get API key** > **Create API key**.
3. Salin key-nya.

Bot memakai `gemini-flash-lite-latest` sebagai model utama karena cepat dan stabil,
dengan `gemini-flash-latest` sebagai cadangan. Batas free tier bisa dicek di halaman
rate limit AI Studio. Bot hanya butuh beberapa panggilan per hari.

---

## 8. Isi file .env

File `.env` menyimpan semua kredensial untuk dipakai di laptop. File ini sudah masuk
`.gitignore`, jadi **tidak akan ikut ter-upload** ke GitHub.

```cmd
copy .env.example .env
notepad .env
```

Isi nilainya **tanpa tanda kutip**:

```
GARMIN_PERSONAL_API_KEY=key_dari_langkah_4

SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...

GEMINI_API_KEY=key_dari_langkah_7
GEMINI_MODEL=gemini-flash-lite-latest
GEMINI_MODEL_CADANGAN=gemini-flash-latest

TELEGRAM_BOT_TOKEN=token_dari_botfather
TELEGRAM_CHAT_ID=angka_dari_userinfobot

FITUR_MAKANAN=false
FITUR_BUDGET=false

KOTA=Bandung
CATATAN_MAKANAN=halal, lebih sering beli di warung
CATATAN_OLAHRAGA=lari 3x seminggu
```

Penjelasan fitur opsional:

| Variabel | Fungsi |
|---|---|
| `FITUR_MAKANAN` | `true` = AI memberi saran menu sarapan, makan siang, dan makan malam. `false` = AI hanya memberi catatan singkat soal pemulihan. |
| `FITUR_BUDGET` | `true` = tampilkan budget makan dan aktifkan perintah `/catat`, `/sisa`, `/budget`, `/batal`. Butuh `FITUR_MAKANAN=true`. |
| `KOTA`, `CATATAN_MAKANAN` | Dipakai hanya kalau `FITUR_MAKANAN=true`. |
| `CATATAN_OLAHRAGA` | Konteks untuk catatan AI. |

---

## 9. Uji di laptop

Pastikan `(.venv)` aktif, lalu uji satu per satu.

**a. Telegram**
```cmd
python -c "import os; from dotenv import load_dotenv; load_dotenv(); from bot.telegram import Telegram; Telegram(os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID']).kirim('Halo, bot sudah terhubung!')"
```
Pesan "Halo" harus masuk ke Telegram.

**b. Gemini**
```cmd
python cek_gemini.py
```
Minimal satu model harus `OK`.

**c. Garmin**
```cmd
python cek_garmin.py
```
Kalau hari ini belum ada data tidur, coba tanggal kemarin, misalnya
`python cek_garmin.py 2026-11-06`. Respons mentah disimpan ke folder `samples/`,
yang juga tidak ikut ter-upload.

**d. Laporan lengkap**
```cmd
python main.py pagi
```
Laporan harus masuk ke Telegram. Kalau dijalankan malam hari, data tidur memang kosong.
Itu normal.

---

## 10. Upload ke GitHub

```cmd
git add .
git status
```

**Periksa hasil `git status`.** Tidak boleh ada `.env`, `.venv`, atau `samples`.
Yang boleh hanya `.env.example`. Kalau sudah aman:

```cmd
git commit -m "Konfigurasi awal"
git push
```

---

## 11. Isi Secrets dan Variables di GitHub

Di repo GitHub kamu: **Settings > Secrets and variables > Actions**.

**Tab Secrets** > **New repository secret**. Salin nilainya saja, tanpa nama variabel,
tanda `=`, tanda kutip, atau spasi di akhir.

| Name | Isi |
|---|---|
| `GARMIN_PERSONAL_API_KEY` | API key Garmin |
| `SUPABASE_URL` | URL project Supabase |
| `SUPABASE_SECRET_KEY` | secret atau service_role key |
| `GEMINI_API_KEY` | API key Gemini |
| `TELEGRAM_BOT_TOKEN` | token bot |
| `TELEGRAM_CHAT_ID` | chat ID |

**Tab Variables** > **New repository variable**:

| Name | Value |
|---|---|
| `GEMINI_MODEL` | `gemini-flash-lite-latest` |
| `GEMINI_MODEL_CADANGAN` | `gemini-flash-latest` |
| `CATATAN_OLAHRAGA` | samakan dengan `.env` |
| `FITUR_MAKANAN` | opsional, `true` kalau mau saran menu |
| `FITUR_BUDGET` | opsional, `true` kalau mau budget makan |
| `KOTA`, `CATATAN_MAKANAN` | opsional, hanya kalau `FITUR_MAKANAN=true` |

Variable yang tidak dibuat otomatis memakai nilai default (fitur makanan dan budget nonaktif).

---

## 12. Tes di GitHub

1. Kirim `/laporan` ke bot Telegram kamu.
2. Di repo GitHub, buka tab **Actions** > **Sinkron Perintah Telegram** > **Run workflow**.
3. Dalam sekitar satu menit harus muncul centang hijau dan laporan masuk ke Telegram.

Kalau muncul silang merah, klik run-nya, buka langkah `python main.py ...`, lalu baca
pesan errornya. Lihat juga [Mengatasi masalah](#17-mengatasi-masalah).

---

## 13. Pemicu tepat waktu dengan cron-job.org

Repo ini sudah punya jadwal bawaan GitHub, tapi **jadwal GitHub tidak bisa diandalkan**:
sering telat sampai berjam-jam atau bahkan dilewati saat server sedang ramai. Karena itu,
pemicu utamanya cron-job.org, sedangkan jadwal GitHub tetap aktif sebagai cadangan.
Laporan tidak akan terkirim dobel walaupun keduanya jalan.

### 13a. Buat token GitHub dengan akses terbatas

1. GitHub > foto profil > **Settings** > **Developer settings** > **Personal access tokens**
   > **Fine-grained tokens** > **Generate new token**.
2. Isi:
   - **Token name:** `cron-sleeptracker`
   - **Expiration:** paling lama yang tersedia. **Catat tanggalnya.**
   - **Repository access:** **Only select repositories**, lalu pilih repo sleeptracker kamu.
   - **Permissions > Repository permissions > Actions:** **Read and write**.
3. **Generate token**, lalu salin (diawali `github_pat_...`). Hanya ditampilkan sekali.

Token ini hanya bisa menjalankan workflow di satu repo itu. Tidak bisa membaca kode
atau mengakses repo lain.

**Tes token dari CMD** (ganti `TOKEN`, `USERNAME`, dan `NAMA-REPO`):
```cmd
curl -i -X POST -H "Authorization: Bearer TOKEN" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" https://api.github.com/repos/USERNAME/NAMA-REPO/actions/workflows/pagi.yml/dispatches -d "{\"ref\":\"main\"}"
```
Baris pertama harus `HTTP/1.1 204 No Content`.

### 13b. Cronjob "Laporan Pagi"

Di **cron-job.org** > **Create cronjob**.

**Tab COMMON**
- **Title:** `Laporan Pagi`
- **URL:** `https://api.github.com/repos/USERNAME/NAMA-REPO/actions/workflows/pagi.yml/dispatches`
- **Execution schedule:** **Custom**. Isi kotak **Crontab expression** dengan:
  ```
  */30 6-12 * * *
  ```
  Artinya setiap 30 menit dari 06.00 sampai 12.30. Cek panel **Next executions** di kanan:
  harus 6:00, 6:30, 7:00, dan seterusnya.

**Tab ADVANCED**
- **Requires HTTP authentication:** biarkan **mati**.
- **Headers:**

  | Key | Value |
  |---|---|
  | `Authorization` | `Bearer github_pat_...` (satu spasi setelah `Bearer`) |
  | `Accept` | `application/vnd.github+json` |
  | `X-GitHub-Api-Version` | `2022-11-28` |
  | `Content-Type` | `application/json` (atau klik **ADD CONTENT-TYPE HEADER NOW**) |

- **Time zone:** `Asia/Jakarta` atau `Asia/Bangkok` (sama-sama UTC+7)
- **Request method:** `POST`
- **Request body:**
  ```json
  {"ref":"main"}
  ```

Klik **TEST RUN**. Hasilnya harus **204 No Content**. Lalu klik **SAVE**.

### 13c. Cronjob "Sinkron"

Supaya perintah Telegram juga dibalas di siang dan malam hari:

1. Di cronjob Laporan Pagi, klik **ACTIONS** > **Clone**.
2. Ubah:
   - **Title:** `Sinkron`
   - **URL:** ganti `pagi.yml` jadi `sinkron.yml`
   - **Crontab expression:** `0 13-23 * * *` (setiap jam dari 13.00 sampai 23.00)
3. **TEST RUN** (harus 204), lalu **SAVE**.

Total sekitar 40 run per hari, masih di bawah kuota menit gratis GitHub Actions
untuk repo private.

**Setup selesai.** Mulai sekarang bot berjalan sendiri tanpa laptop.

---

## 14. Cara kerja harian

1. Tidur dengan jam Garmin terpasang.
2. Setelah bangun, buka aplikasi **Garmin Connect** di HP supaya data tersinkron.
3. Pada pengecekan 30 menit berikutnya, laporan lengkap masuk ke Telegram.

Aturan pengiriman:
- Laporan lengkap dikirim **sekali sehari**, begitu data tidur tersedia.
- Kalau sampai **jam 10.00** data tidur belum ada, laporan tetap dikirim apa adanya.
  Setelah itu bot terus memantau dan mengirim **satu laporan susulan** yang lengkap
  begitu data tidur muncul.
- Batas jam bisa diubah lewat `JAM_BATAS_LAPORAN` di `main.py`.

Aturan tingkat pemulihan (di `bot/recovery.py`):
- **Sleep score** mengikuti kategori Garmin: 80 ke atas baik, 60 sampai 79 cukup, di bawah 60 kurang.
- **Status HRV** mengikuti label Garmin: BALANCED baik, UNBALANCED cukup, LOW atau POOR kurang.
- **Body Battery saat bangun:** 70 ke atas baik, 40 sampai 69 cukup, di bawah 40 kurang.
  Ambang ini titik awal heuristik, bukan standar resmi Garmin. Silakan sesuaikan
  setelah beberapa minggu melihat datamu sendiri.

Catatan AI baru membandingkan dengan tren setelah ada minimal 3 hari data sebelumnya.

---

## 15. Perintah Telegram

| Perintah | Fungsi |
|---|---|
| `/laporan` | kirim ulang laporan dengan data terbaru |
| `/help` | daftar perintah |
| `/catat 25000 nasi padang` | catat pengeluaran makan (butuh `FITUR_BUDGET=true`) |
| `/sisa` | sisa budget hari ini dan bulan ini (butuh `FITUR_BUDGET=true`) |
| `/budget 1500000` | ubah budget makan bulanan (butuh `FITUR_BUDGET=true`) |
| `/batal` | hapus catatan pengeluaran terakhir (butuh `FITUR_BUDGET=true`) |

Perintah diproses saat pemicu berikutnya berjalan, jadi balasannya datang
paling lama sekitar 30 menit di pagi hari dan sekitar 1 jam di siang sampai malam hari.

---

## 16. Perawatan

| Yang perlu diganti | Kapan | Caranya |
|---|---|---|
| API key Garmin | sesuai masa berlaku yang dipilih (Garmin mengirim email sekitar seminggu sebelumnya) | buat key baru di Garmin Connect, lalu perbarui secret `GARMIN_PERSONAL_API_KEY` |
| Token GitHub untuk cron-job.org | tanggal kedaluwarsa yang kamu catat | buat atau regenerate token, lalu perbarui header `Authorization` di kedua cronjob |

Kalau API key Garmin ditolak, bot memberi tahu lewat Telegram.

Supabase free tier dijeda kalau tidak ada aktivitas selama seminggu. Bot menulis data
setiap hari, jadi biasanya aman.

---

## 17. Mengatasi masalah

| Gejala | Penyebab | Solusi |
|---|---|---|
| `No module named 'garmin_personal_api'` atau `cannot import name 'genai'` | virtual env belum aktif | jalankan `.venv\Scripts\activate.bat`, pastikan muncul `(.venv)` |
| `No suitable Python runtime found` | versi Python yang diminta belum terpasang | cek `py --list`, pakai versi 3.12 atau lebih baru yang ada |
| `'New-Item' is not recognized` | perintah PowerShell dijalankan di CMD | pakai versi CMD dari panduan ini |
| `cek_gemini.py`: `504 DEADLINE_EXCEEDED` | model sedang lambat di server Google | pakai `gemini-flash-lite-latest` sebagai model utama |
| Saran AI "tidak tersedia" | Gemini gagal atau kena limit | laporan tetap terkirim, cek dengan `python cek_gemini.py` |
| cron-job.org: `401 Unauthorized` | header Authorization kosong atau token salah | isi `Bearer ` + token, tes token dengan perintah curl di langkah 13a |
| cron-job.org: `403` atau `404` | izin Actions belum Read and write, repo belum dipilih, atau URL salah | periksa pengaturan token dan URL |
| Laporan pagi tidak datang | data tidur belum tersinkron, atau pemicu tidak jalan | buka aplikasi Garmin Connect, cek riwayat di cron-job.org dan tab Actions |
| Ada metrik tampil `-` | jam tidak mengukur metrik itu, atau data belum sinkron | jalankan `python cek_garmin.py`, lihat file JSON di `samples/` |
| `/laporan` lama dibalas | perintah baru diproses saat pemicu berikutnya | normal, tunggu pemicu berikutnya |
| Log: `Kolom baru belum ada di Supabase` | tabel dibuat sebelum fitur tahap tidur ditambahkan | jalankan `supabase/migrasi_tahap_tidur.sql` di SQL Editor Supabase |

---

## 18. Keamanan dan privasi

- Pakai repo **private**. Log GitHub Actions di repo public bisa dilihat siapa pun.
- Semua kredensial hanya ada di `.env` (lokal) dan GitHub Secrets. **Jangan pernah**
  commit `.env` atau mengirim key ke chat.
- Log GitHub Actions hanya berisi status, tidak pernah angka kesehatan atau uang.
- Bot mengabaikan pesan Telegram dari chat selain `TELEGRAM_CHAT_ID`.
- Supabase memakai Row Level Security tanpa policy, jadi hanya secret key yang bisa mengakses.
- Garmin diakses lewat Personal API resmi dan hanya membaca data.
- Ke Gemini hanya dikirim angka ringkasan tanpa nama atau identitas. Free tier Gemini
  dapat memakai data input untuk pengembangan produk Google, jadi pertimbangkan hal ini.
- Versi library dikunci di `requirements.txt`.
- **Jangan menambahkan orang lain sebagai collaborator** di repo yang berisi secrets-mu.
  Collaborator bisa mengubah workflow dan membaca secrets lewat workflow itu.
  Untuk berbagi, bagikan repo template (kode saja).

---

## 19. Struktur proyek

| File | Fungsi |
|---|---|
| `main.py` | titik masuk: mode `pantau`, `pagi`, `sinkron` |
| `cek_garmin.py` | uji koneksi Garmin dan simpan respons mentah ke `samples/` |
| `cek_gemini.py` | uji koneksi Gemini |
| `bot/garmin_data.py` | ambil dan baca data Garmin |
| `bot/recovery.py` | aturan pemulihan dan rekomendasi latihan |
| `bot/ai.py` | prompt dan pemanggilan Gemini |
| `bot/report.py` | susun teks laporan |
| `bot/commands.py` | perintah Telegram |
| `bot/budget.py` | hitung budget makan (opsional) |
| `bot/db.py`, `bot/telegram.py`, `bot/config.py` | akses Supabase, Telegram, dan pengaturan |
| `supabase/schema.sql` | struktur tabel database |
| `.github/workflows/pagi.yml` | workflow laporan pagi (mode pantau) |
| `.github/workflows/sinkron.yml` | workflow sinkron perintah dan laporan susulan |
| `tests/` | tes otomatis, jalankan dengan `python -m unittest discover tests` |

Mode `main.py`:

| Mode | Fungsi |
|---|---|
| `python main.py pantau` | proses perintah, lalu kirim laporan kalau data tidur sudah ada atau batas jam tercapai |
| `python main.py sinkron` | proses perintah, plus kirim laporan susulan kalau data tidur baru muncul |
| `python main.py pagi` | paksa kirim laporan sekarang (untuk uji coba) |
