-- Database Yedekle licensing/customer-management foundation.
-- RLS is enabled with no client policies by design: use trusted Edge Functions
-- with server-side authorization for all reads/writes. Never ship service_role keys.

create sequence if not exists public.customer_number_seq start 1;

create table if not exists public.customers (
  id uuid primary key default gen_random_uuid(),
  customer_number text not null unique,
  company_name text not null,
  contact_person text not null,
  phone text not null,
  email text,
  identity_fingerprint text,
  status text not null default 'pending'
    check (status in ('pending','active','rejected','blocked')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.assign_customer_number()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.customer_number is null or btrim(new.customer_number) = '' then
    new.customer_number := 'DBY-' || lpad(nextval('public.customer_number_seq')::text, 6, '0');
  end if;
  return new;
end;
$$;

drop trigger if exists customers_assign_customer_number on public.customers;
create trigger customers_assign_customer_number
before insert on public.customers
for each row execute function public.assign_customer_number();

create table if not exists public.demo_requests (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references public.customers(id) on delete restrict,
  status text not null default 'pending'
    check (status in ('pending','approved','rejected','cancelled')),
  requested_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by text,
  review_note text,
  trial_starts_at timestamptz,
  trial_ends_at timestamptz,
  duplicate_review_required boolean not null default false
);

create table if not exists public.licenses (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references public.customers(id) on delete restrict,
  license_key_hash text not null unique,
  status text not null default 'issued'
    check (status in ('issued','active','suspended','revoked','expired')),
  issued_at timestamptz not null default now(),
  starts_at timestamptz,
  expires_at timestamptz,
  max_devices integer not null default 1 check (max_devices = 1),
  last_verified_at timestamptz,
  created_by text,
  notes text
);

create table if not exists public.license_devices (
  id uuid primary key default gen_random_uuid(),
  license_id uuid not null references public.licenses(id) on delete restrict,
  device_fingerprint_hash text not null,
  device_label text,
  first_activated_at timestamptz not null default now(),
  last_verified_at timestamptz,
  released_at timestamptz,
  released_by text,
  release_note text
);
create unique index if not exists one_active_device_per_license
  on public.license_devices(license_id)
  where released_at is null;

create table if not exists public.sales (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references public.customers(id) on delete restrict,
  license_id uuid references public.licenses(id) on delete set null,
  sale_date date not null default current_date,
  total_amount numeric(12,2) not null check (total_amount >= 0),
  currency text not null default 'TRY' check (currency in ('TRY','EUR','USD')),
  payment_method text,
  due_date date,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  sale_id uuid not null references public.sales(id) on delete restrict,
  amount numeric(12,2) not null check (amount > 0),
  paid_at timestamptz not null default now(),
  payment_method text,
  reference_note text,
  created_by text
);

create table if not exists public.license_events (
  id bigint generated always as identity primary key,
  customer_id uuid references public.customers(id) on delete set null,
  license_id uuid references public.licenses(id) on delete set null,
  device_id uuid references public.license_devices(id) on delete set null,
  event_type text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists customers_company_name_idx on public.customers (lower(company_name));
create index if not exists customers_contact_person_idx on public.customers (lower(contact_person));
create index if not exists customers_phone_idx on public.customers (phone);
create index if not exists demo_requests_customer_status_idx on public.demo_requests (customer_id, status);
create index if not exists licenses_customer_status_idx on public.licenses (customer_id, status);
create index if not exists sales_customer_date_idx on public.sales (customer_id, sale_date desc);
create index if not exists payments_sale_date_idx on public.payments (sale_id, paid_at desc);

alter table public.customers enable row level security;
alter table public.demo_requests enable row level security;
alter table public.licenses enable row level security;
alter table public.license_devices enable row level security;
alter table public.sales enable row level security;
alter table public.payments enable row level security;
alter table public.license_events enable row level security;

comment on table public.customers is 'Private customer registry. Customer number is generated by database and is not an authentication secret.';
comment on table public.demo_requests is 'Demo starts only after authorized admin approval; trial timestamps are server-managed.';
comment on table public.license_devices is 'A license has at most one unreleased device; device transfer requires admin release.';
comment on table public.payments is 'Individual payment entries used to calculate paid amount and outstanding balance.';
