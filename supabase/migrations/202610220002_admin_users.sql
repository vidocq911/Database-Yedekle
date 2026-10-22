-- Admin authorization registry for Database Yedekle.
-- Bootstrap the first admin manually after creating the Supabase Auth user:
-- INSERT INTO public.admin_users (user_id, role) VALUES ('<auth-user-uuid>', 'owner');
-- Run that statement only in the SQL Editor as project owner.
create table if not exists public.admin_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'admin' check (role in ('owner','admin','support')),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);
alter table public.admin_users enable row level security;
comment on table public.admin_users is 'Server-side admin allowlist. No public client policies; only trusted server functions should read it.';
