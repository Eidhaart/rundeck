-- RunDeck database schema. Run in the Supabase SQL editor. Safe to run again.
--
-- Privacy model: every row belongs to one user and only that user can read or change it.
-- Emails and passwords live only in Supabase Auth (auth.users); RunDeck's own tables never hold them.

-- Small per-user summary (handle, language, level). Private to its owner.
create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  handle text check (char_length(handle) <= 24),
  lang text default 'en' check (lang in ('en', 'pl', 'sv')),
  level int default 1,
  xp int default 0,
  updated_at timestamptz default now()
);
alter table public.profiles drop column if exists avatar_url;

-- The whole deck (tasks, shards, settings, portrait) as one JSON document per user. Private to its owner.
create table if not exists public.decks (
  user_id uuid primary key references auth.users on delete cascade,
  data jsonb not null check (pg_column_size(data) < 2000000),
  updated_at timestamptz default now()
);

alter table public.profiles enable row level security;
alter table public.decks enable row level security;
alter table public.profiles force row level security;
alter table public.decks force row level security;

-- Remove the older, wider policies if an earlier version of this file was run.
drop policy if exists "profiles readable by signed-in users" on public.profiles;
drop policy if exists "profiles owner insert" on public.profiles;
drop policy if exists "profiles owner update" on public.profiles;
drop policy if exists "decks owner all" on public.decks;

drop policy if exists "profiles owner select" on public.profiles;
create policy "profiles owner select" on public.profiles
  for select to authenticated using ((select auth.uid()) = id);
drop policy if exists "profiles owner insert" on public.profiles;
create policy "profiles owner insert" on public.profiles
  for insert to authenticated with check ((select auth.uid()) = id);
drop policy if exists "profiles owner update" on public.profiles;
create policy "profiles owner update" on public.profiles
  for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

drop policy if exists "decks owner select" on public.decks;
create policy "decks owner select" on public.decks
  for select to authenticated using ((select auth.uid()) = user_id);
drop policy if exists "decks owner insert" on public.decks;
create policy "decks owner insert" on public.decks
  for insert to authenticated with check ((select auth.uid()) = user_id);
drop policy if exists "decks owner update" on public.decks;
create policy "decks owner update" on public.decks
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists "decks owner delete" on public.decks;
create policy "decks owner delete" on public.decks
  for delete to authenticated using ((select auth.uid()) = user_id);

-- Anonymous visitors get no access at all.
revoke all on public.profiles from anon;
revoke all on public.decks from anon;

-- Let a signed-in user delete their own account. Profiles and decks are removed by the cascade.
create or replace function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null then
    raise exception 'not signed in';
  end if;
  delete from auth.users where id = auth.uid();
end;
$$;
revoke all on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;

-- Portraits are stored inside the private deck, so the public avatars bucket is no longer used.
-- If an earlier version created it, remove its policies; delete the bucket in Storage when it is empty.
drop policy if exists "avatar owner insert" on storage.objects;
drop policy if exists "avatar owner select" on storage.objects;
drop policy if exists "avatar owner update" on storage.objects;
drop policy if exists "avatar owner delete" on storage.objects;
