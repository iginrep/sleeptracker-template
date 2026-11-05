-- Jalankan sekali di Supabase: SQL Editor > New query > tempel > Run.

-- Riwayat metrik harian dari Garmin
create table if not exists daily_metrics (
    tanggal          date primary key,
    sleep_score      int,
    sleep_jam        numeric(4,2),
    hrv_semalam      int,
    hrv_status       text,
    body_battery     int,
    resting_hr       int,
    tingkat_pulih    text,
    dibuat_pada      timestamptz default now()
);

-- Catatan pengeluaran makan
create table if not exists expenses (
    id                   bigint generated always as identity primary key,
    tanggal              date not null,
    nominal              int not null check (nominal > 0),
    keterangan           text,
    telegram_message_id  bigint unique,   -- mencegah pesan yang sama tercatat dua kali
    dibuat_pada          timestamptz default now()
);
create index if not exists expenses_tanggal_idx on expenses (tanggal);

-- Pengaturan sederhana (budget bulanan, posisi pesan Telegram terakhir, dll.)
create table if not exists settings (
    kunci  text primary key,
    nilai  text not null
);

insert into settings (kunci, nilai) values ('budget_bulanan', '1500000')
on conflict (kunci) do nothing;

-- Keamanan: aktifkan Row Level Security TANPA policy.
-- Artinya hanya secret/service_role key (yang ada di GitHub Secrets) yang bisa
-- membaca dan menulis. Anon/publishable key tidak bisa mengakses apa pun.
alter table daily_metrics enable row level security;
alter table expenses      enable row level security;
alter table settings      enable row level security;
