create extension if not exists pgcrypto;

create table public.command_center_health_daily (
  user_id uuid not null references auth.users(id) on delete cascade,
  day date not null,
  steps integer check (steps is null or steps >= 0),
  sleep_minutes integer check (sleep_minutes is null or sleep_minutes >= 0),
  active_energy_kcal numeric check (
    active_energy_kcal is null or active_energy_kcal >= 0
  ),
  resting_heart_rate numeric check (
    resting_heart_rate is null or resting_heart_rate > 0
  ),
  updated_at timestamptz not null default now(),
  primary key (user_id, day)
);

create table public.command_center_health_ingest_tokens (
  user_id uuid primary key references auth.users(id) on delete cascade,
  token_hash text not null,
  created_at timestamptz not null default now()
);

alter table public.command_center_health_daily enable row level security;
alter table public.command_center_health_ingest_tokens enable row level security;

create policy "Users read own health summary"
  on public.command_center_health_daily
  for select
  to authenticated
  using (auth.uid() = user_id);

create or replace function public.ingest_command_center_health(
  ingest_secret text,
  metric_day date,
  metric_steps integer,
  metric_sleep_minutes integer,
  metric_active_energy_kcal numeric,
  metric_resting_heart_rate numeric
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  target_user uuid;
begin
  select user_id
    into target_user
    from public.command_center_health_ingest_tokens
   where token_hash = encode(digest(ingest_secret, 'sha256'), 'hex');

  if target_user is null then
    raise exception 'Invalid health ingest token';
  end if;

  insert into public.command_center_health_daily (
    user_id,
    day,
    steps,
    sleep_minutes,
    active_energy_kcal,
    resting_heart_rate,
    updated_at
  )
  values (
    target_user,
    metric_day,
    metric_steps,
    metric_sleep_minutes,
    metric_active_energy_kcal,
    metric_resting_heart_rate,
    now()
  )
  on conflict (user_id, day) do update set
    steps = excluded.steps,
    sleep_minutes = excluded.sleep_minutes,
    active_energy_kcal = excluded.active_energy_kcal,
    resting_heart_rate = excluded.resting_heart_rate,
    updated_at = now();
end;
$$;

revoke all on function public.ingest_command_center_health(
  text,
  date,
  integer,
  integer,
  numeric,
  numeric
) from public;

grant execute on function public.ingest_command_center_health(
  text,
  date,
  integer,
  integer,
  numeric,
  numeric
) to anon, authenticated;
