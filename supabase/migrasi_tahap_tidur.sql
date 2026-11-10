-- Jalankan sekali di Supabase (SQL Editor > New query > Run) kalau tabel
-- daily_metrics sudah dibuat sebelum fitur kategori dan tahap tidur ditambahkan.
-- Aman dijalankan berulang kali.

alter table daily_metrics add column if not exists sleep_kategori text;
alter table daily_metrics add column if not exists deep_menit     int;
alter table daily_metrics add column if not exists light_menit    int;
alter table daily_metrics add column if not exists rem_menit      int;
alter table daily_metrics add column if not exists awake_menit    int;
