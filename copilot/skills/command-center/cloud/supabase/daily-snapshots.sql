create table public.command_center_daily_snapshots (
  user_id uuid not null references auth.users(id) on delete cascade,
  day date not null,
  payload jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, day)
);

alter table public.command_center_daily_snapshots enable row level security;

create policy "Owner reads daily snapshots"
  on public.command_center_daily_snapshots
  for select
  to authenticated
  using (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
  );
