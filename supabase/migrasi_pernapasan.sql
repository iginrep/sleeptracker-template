-- Jalankan sekali di Supabase (SQL Editor > New query > Run) kalau tabel
-- daily_metrics sudah dibuat sebelum data pernapasan ditambahkan.
-- Aman dijalankan berulang kali.

alter table daily_metrics add column if not exists napas_rata      numeric(4,1);
alter table daily_metrics add column if not exists napas_terendah  numeric(4,1);
alter table daily_metrics add column if not exists napas_tertinggi numeric(4,1);
alter table daily_metrics add column if not exists variasi_napas   text;
alter table daily_metrics add column if not exists spo2_rata       int;
alter table daily_metrics add column if not exists spo2_terendah   int;
