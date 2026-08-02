-- BoostRAG v2 Phase 2 — accounts & My Garage schema.
-- Run once in the Supabase SQL editor (Dashboard → SQL Editor → New query → paste → Run).
-- Safe to re-run: every object uses IF NOT EXISTS / CREATE OR REPLACE / drop-then-create.
--
-- Security model: the backend talks to PostgREST with the SERVICE-ROLE key, which
-- BYPASSES the RLS policies below. RLS is therefore a defense-in-depth backstop for
-- anon-key / direct client access; the backend is still responsible for filtering
-- every query by the JWT `sub` (see garage_store.py). Do not relax that.

-- ---------------------------------------------------------------------------
-- profiles : one row per auth user (auto-created on signup by trigger below)
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
    id           uuid primary key references auth.users (id) on delete cascade,
    display_name text,
    plan         text        not null default 'free',   -- free | plus | pro (future paid tiers)
    credits      integer     not null default 0,
    created_at   timestamptz not null default now()
);

alter table public.profiles enable row level security;

drop policy if exists "profiles are self-only" on public.profiles;
create policy "profiles are self-only" on public.profiles
    for all
    using (id = auth.uid())
    with check (id = auth.uid());

-- Auto-provision a profile row whenever a new auth user is created.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (id, display_name)
    values (new.id, new.raw_user_meta_data ->> 'display_name')
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- garages : exactly one per user (the UNIQUE on user_id backs the upsert's
--           on_conflict=user_id in garage_store.upsert_garage)
-- ---------------------------------------------------------------------------
create table if not exists public.garages (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid        not null unique references public.profiles (id) on delete cascade,
    year       integer,
    model      text,
    trim       text,
    context_on boolean     not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.garages enable row level security;

drop policy if exists "garages are self-only" on public.garages;
create policy "garages are self-only" on public.garages
    for all
    using (user_id = auth.uid())
    with check (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- garage_mods : the installed parts that flavor the answer context
-- ---------------------------------------------------------------------------
create table if not exists public.garage_mods (
    id         uuid primary key default gen_random_uuid(),
    garage_id  uuid        not null references public.garages (id) on delete cascade,
    category   text,
    name       text,
    source_url text,
    created_at timestamptz not null default now()
);

create index if not exists garage_mods_garage_id_idx on public.garage_mods (garage_id);

alter table public.garage_mods enable row level security;

drop policy if exists "mods via own garage" on public.garage_mods;
create policy "mods via own garage" on public.garage_mods
    for all
    using (garage_id in (select id from public.garages where user_id = auth.uid()))
    with check (garage_id in (select id from public.garages where user_id = auth.uid()));
