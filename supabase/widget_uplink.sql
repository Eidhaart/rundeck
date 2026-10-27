-- RunDeck / KWGT widget uplink.
-- Run ONCE in Supabase SQL Editor after the existing supabase/schema.sql.
-- No service_role key, account password or Vercel secrets are needed.
-- One widget key per account. Only a SHA-256 hash is stored.
-- The token grants READ ONLY access to a tiny, user-scoped snapshot.

create table if not exists public.widget_keys (
  user_id uuid primary key references auth.users(id) on delete cascade,
  token_hash text not null unique check (token_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);

alter table public.widget_keys enable row level security;
alter table public.widget_keys force row level security;
revoke all on public.widget_keys from public, anon, authenticated;

-- The logged-in user supplies a SHA-256 hash computed in their browser.
-- Replacing the key immediately invalidates the previous widget URL.
create or replace function public.widget_rotate_key(p_hash text)
returns void
language plpgsql volatile security definer
set search_path = ''
as $$
begin
  if auth.uid() is null then raise exception 'Sign in first'; end if;
  if p_hash is null or p_hash !~ '^[0-9a-f]{64}$' then
    raise exception 'Invalid SHA-256 hash';
  end if;
  insert into public.widget_keys (user_id, token_hash, created_at)
  values (auth.uid(), p_hash, now())
  on conflict (user_id) do update
    set token_hash = excluded.token_hash, created_at = now();
end;
$$;
revoke all on function public.widget_rotate_key(text) from public, anon, authenticated;
grant execute on function public.widget_rotate_key(text) to authenticated;

create or replace function public.widget_revoke_key()
returns void
language plpgsql volatile security definer
set search_path = ''
as $$
begin
  if auth.uid() is null then raise exception 'Sign in first'; end if;
  delete from public.widget_keys where user_id = auth.uid();
end;
$$;
revoke all on function public.widget_revoke_key() from public, anon, authenticated;
grant execute on function public.widget_revoke_key() to authenticated;

create or replace function public.widget_has_key()
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select auth.uid() is not null
     and exists(select 1 from public.widget_keys where user_id = auth.uid());
$$;
revoke all on function public.widget_has_key() from public, anon, authenticated;
grant execute on function public.widget_has_key() to authenticated;

-- The public RPC only accepts a 256-bit bearer key and returns summary
-- fields; it never returns an email, user ID, password or entire deck.
-- A security-definer function is needed because the anonymous API role
-- must NOT be allowed to SELECT the decks table directly.
create or replace function public.widget_snapshot(p_token text)
returns jsonb
language plpgsql stable security definer
set search_path = ''
as $$
declare
  owner_id uuid;
  deck jsonb;
  task jsonb;
  all_tasks jsonb;
  task_list text;
  task_done boolean;
  task_failed boolean;
  today date := (now() at time zone 'Europe/Stockholm')::date;
  yesterday text;
  two_days_ago text;
  monday text;
  fresh boolean;
  open_count int := 0;
  done_count int := 0;
  total_count int := 0;
  live_streak int := 0;
  total_xp int := 0;
  level_no int := 1;
  remaining_xp int;
  target_id text;
  priority_title text;
  next_title text;
  task_title text;
  streak_data jsonb;
  last_streak text;
  shield_available boolean;
  pct int;
begin
  -- Cheap validation before running a hash lookup.
  if p_token is null or p_token !~ '^[0-9a-f]{64}$' then return null; end if;
  select k.user_id into owner_id
    from public.widget_keys k
    where k.token_hash =
      pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(p_token, 'UTF8')), 'hex');
  if owner_id is null then return null; end if;

  select d.data into deck from public.decks d where d.user_id = owner_id;
  if deck is null then return null; end if;

  fresh := (deck->>'day') = today::text;
  all_tasks := case when jsonb_typeof(deck->'tasks') = 'array'
                    then deck->'tasks' else '[]'::jsonb end;
  target_id := deck->>'target';
  for task in select value from pg_catalog.jsonb_array_elements(all_tasks) loop
    task_list := task->>'list';
    task_done := coalesce((task->>'done')::boolean, false);
    task_failed := coalesce((task->>'failed')::boolean, false);
    task_title := coalesce(nullif(pg_catalog.btrim(
      pg_catalog.regexp_replace(coalesce(task->>'title', ''), '[[:space:]]+', ' ', 'g')), ''), 'UNTITLED');

    if target_id is not null and task->>'id' = target_id and
       not task_done and not task_failed then
      priority_title := task_title;
    end if;

    if task_list in ('today', 'routine') and
       (fresh or task_list = 'routine' or (not task_done and not task_failed)) then
      total_count := total_count + 1;
      -- A routine's completion resets when a new local day begins.
      if fresh and (task_done or task_failed) then
        done_count := done_count + 1;
      elsif not fresh or (not task_done and not task_failed) then
        open_count := open_count + 1;
        if next_title is null then next_title := task_title; end if;
      end if;
    end if;
  end loop;

  total_xp := pg_catalog.greatest(0, coalesce((deck->>'xp')::int, 0));
  remaining_xp := total_xp;
  -- Same level thresholds as RunDeck's lvl(): 80 + 40 * current level.
  while remaining_xp >= (80 + 40 * level_no) and level_no < 10000 loop
    remaining_xp := remaining_xp - (80 + 40 * level_no);
    level_no := level_no + 1;
  end loop;

  streak_data := coalesce(deck->'streak', '{}'::jsonb);
  yesterday := (today - 1)::text;
  two_days_ago := (today - 2)::text;
  monday := (today - (pg_catalog.extract(isodow from today)::int - 1))::text;
  last_streak := streak_data->>'last';
  shield_available := coalesce(streak_data->>'shield', '') <> monday
     or exists (
       select 1 from pg_catalog.jsonb_array_elements(
         case when jsonb_typeof(deck->'items') = 'array'
              then deck->'items' else '[]'::jsonb end
       ) as item(value) where item.value->>'t' = 'shield'
     );
  if last_streak in (today::text, yesterday) or
     (last_streak = two_days_ago and shield_available) then
    live_streak := pg_catalog.greatest(0, coalesce((streak_data->>'n')::int, 0));
  end if;

  pct := case when total_count = 0 then 0
    else pg_catalog.round(100.0 * done_count / total_count)::int end;
  next_title := coalesce(priority_title, next_title, 'ALL OBJECTIVES CLEAR');
  if length(next_title) > 27 then
    next_title := left(next_title, 26) || '…';
  end if;

  return pg_catalog.jsonb_build_object(
    'status', 'LIVE',
    'today_open', open_count,
    'open_display', pg_catalog.lpad(open_count::text, 2, '0'),
    'today_done', done_count,
    'today_total', total_count,
    'total_display', pg_catalog.lpad(total_count::text, 2, '0'),
    'progress_pct', pct,
    'level', level_no,
    'level_display', pg_catalog.lpad(level_no::text, 2, '0'),
    'streak', live_streak,
    'xp', total_xp,
    'next_title', next_title,
    'synced_at', now()
  );
end;
$$;
revoke all on function public.widget_snapshot(text) from public, anon, authenticated;
grant execute on function public.widget_snapshot(text) to anon, authenticated;
