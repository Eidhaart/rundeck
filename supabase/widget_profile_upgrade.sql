-- Operator Profile widget extension for RunDeck.
-- Run this SQL ONCE in your existing Supabase SQL Editor AFTER widget_uplink.sql.
-- It doesn't alter existing tables, user accounts, or stored deck data.
-- The existing widget_snapshot RPC remains available for older KWGT presets.
--
-- The random 256-bit widget URL token is a read-only bearer credential.
-- Treat the URL as private; it may appear in server/device logs.
--
-- A profile summary returns only the handle, progress, credits, today's task
-- counts, and enabled event state. The portrait is available separately through
-- widget_profile_image, which checks the same token before returning the jpeg.
--
create or replace function public.widget_profile_snapshot(p_token text)
returns jsonb
language plpgsql stable security definer
set search_path = ''
as $$
declare
  baseline jsonb;
  d jsonb;
  settings jsonb;
  task jsonb;
  tasks jsonb;
  local_today date := (now() at time zone 'Europe/Stockholm')::date;
  fresh boolean;
  finished int := 0;
  unfinished int := 0;
  credits int;
  xp_total int;
  lvl int := 1;
  xp_part int;
  level_need int;
  has_portrait boolean;
  operator_handle text;
  initials text;
  weekend_event boolean;
  payday_event boolean;
  payday_setting int;
  last_day int;
  event_label text;
begin
  -- This existing auth RPC rejects missing/invalid widget keys.
  baseline := public.widget_snapshot(p_token);
  if baseline is null then return null; end if;

  select deck.data into d
  from public.widget_keys k
  join public.decks deck on deck.user_id = k.user_id
  where k.token_hash =
    pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(p_token, 'UTF8')), 'hex');
  if d is null then return null; end if;

  settings := coalesce(d->'set', '{}'::jsonb);
  operator_handle := coalesce(nullif(pg_catalog.btrim(settings->>'handle'), ''), 'OPERATOR');
  initials := pg_catalog.upper(pg_catalog.substring(
    pg_catalog.regexp_replace(operator_handle, '[^[:alnum:]]', '', 'g') from 1 for 2
  ));
  if initials = '' then initials := 'OP'; end if;
  has_portrait := pg_catalog.left(coalesce(settings->>'avatar', ''), 23) = 'data:image/jpeg;base64,';

  fresh := d->>'day' = local_today::text;
  tasks := case when pg_catalog.jsonb_typeof(d->'tasks') = 'array'
      then d->'tasks' else '[]'::jsonb end;
  for task in select value from pg_catalog.jsonb_array_elements(tasks) loop
    if task->>'list' = 'today' then
      if fresh and coalesce((task->>'done')::boolean, false) then
        finished := finished + 1;
      elsif not coalesce((task->>'done')::boolean, false)
          and not coalesce((task->>'failed')::boolean, false) then
        unfinished := unfinished + 1;
      end if;
    end if;
  end loop;

  credits := greatest(0, coalesce((d->>'cred')::int, 0));
  xp_total := greatest(0, coalesce((d->>'xp')::int, 0));
  xp_part := xp_total;
  while lvl < 10000 and xp_part >= 80 + 40 * lvl loop
    xp_part := xp_part - (80 + 40 * lvl);
    lvl := lvl + 1;
  end loop;
  level_need := 80 + 40 * lvl;

  weekend_event := coalesce(settings->>'evWk', 'normal') <> 'off'
    and extract(isodow from local_today) in (6, 7);
  payday_setting := greatest(1, least(31, coalesce((settings->>'payDay')::int, 25)));
  last_day := extract(day from (
      date_trunc('month', local_today::timestamp)
      + interval '1 month - 1 day'
    ))::int;
  payday_event := coalesce(settings->>'evPay', 'normal') <> 'off'
    and extract(day from local_today)::int = least(payday_setting, last_day);
  event_label := case
    when weekend_event and payday_event then 'WEEKEND + PAYDAY'
    when weekend_event then 'WEEKEND'
    when payday_event then 'PAYDAY'
    else 'NO EVENT'
  end;

  return baseline || pg_catalog.jsonb_build_object(
    'handle', operator_handle,
    'initials', initials,
    'avatar_present', has_portrait,
    'avatar_style', coalesce(settings->>'avStyle', 'duo'),
    'credits', credits,
    'creds', credits,
    'today_open', unfinished,
    'open_display', pg_catalog.lpad(unfinished::text, 2, '0'),
    'today_done', finished,
    'today_total', finished + unfinished,
    'total_display', pg_catalog.lpad((finished + unfinished)::text, 2, '0'),
    'progress_pct', case when (finished + unfinished) = 0 then 0
      else round(100.0 * finished / (finished + unfinished))::int end,
    'level', lvl,
    'level_display', pg_catalog.lpad(lvl::text, 2, '0'),
    'xp', xp_total,
    'xp_into_level', xp_part,
    'xp_for_level', level_need,
    'xp_to_next', level_need - xp_part,
    'event_active', weekend_event or payday_event,
    'event_name', event_label
  );
end;
$$;
revoke all on function public.widget_profile_snapshot(text) from public, anon, authenticated;
grant execute on function public.widget_profile_snapshot(text) to anon, authenticated;

-- JPEG is stored in the account's private deck (set.avatar) as a data URL.
-- Returning it only via this token-gated function does NOT make the entire
-- deck or portraits of other users publicly readable.
create or replace function public.widget_profile_image(p_token text)
returns text
language plpgsql stable security definer
set search_path = ''
as $$
declare
  photo text;
begin
  if p_token is null or p_token !~ '^[0-9a-f]{64}$' then return null; end if;
  select d.data #>> '{set,avatar}' into photo
  from public.widget_keys k
  join public.decks d on d.user_id = k.user_id
  where k.token_hash =
    pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(p_token, 'UTF8')), 'hex');

  if pg_catalog.left(coalesce(photo, ''), 23) != 'data:image/jpeg;base64,' then
    return null;
  end if;
  return photo;
end;
$$;
revoke all on function public.widget_profile_image(text) from public, anon, authenticated;
grant execute on function public.widget_profile_image(text) to anon, authenticated;
