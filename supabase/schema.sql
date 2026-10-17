-- RunDeck database schema. Run once in the Supabase SQL editor.

-- Public operator card: handle, portrait, level. Readable by signed-in users
-- so leaderboards or friends can be added later; writable only by the owner.
create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  handle text,
  avatar_url text,
  lang text default 'en',
  level int default 1,
  xp int default 0,
  updated_at timestamptz default now()
);

-- The whole deck (tasks, rewards, shards, settings) as one JSON document per user.
create table if not exists public.decks (
  user_id uuid primary key references auth.users on delete cascade,
  data jsonb not null,
  updated_at timestamptz default now()
);

alter table public.profiles enable row level security;
alter table public.decks enable row level security;

drop policy if exists "profiles readable by signed-in users" on public.profiles;
create policy "profiles readable by signed-in users" on public.profiles
  for select to authenticated using (true);

drop policy if exists "profiles owner insert" on public.profiles;
create policy "profiles owner insert" on public.profiles
  for insert to authenticated with check (auth.uid() = id);

drop policy if exists "profiles owner update" on public.profiles;
create policy "profiles owner update" on public.profiles
  for update to authenticated using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists "decks owner all" on public.decks;
create policy "decks owner all" on public.decks
  for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Portraits: public bucket, each user writes only inside a folder named after their id.
insert into storage.buckets (id, name, public)
values ('avatars', 'avatars', true)
on conflict (id) do nothing;

drop policy if exists "avatar owner insert" on storage.objects;
create policy "avatar owner insert" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "avatar owner select" on storage.objects;
create policy "avatar owner select" on storage.objects
  for select to authenticated
  using (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "avatar owner update" on storage.objects;
create policy "avatar owner update" on storage.objects
  for update to authenticated
  using (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "avatar owner delete" on storage.objects;
create policy "avatar owner delete" on storage.objects
  for delete to authenticated
  using (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);
