create table public.command_center_snapshots (
  user_id uuid primary key references auth.users(id) on delete cascade,
  payload jsonb not null default '{}'::jsonb,
  version bigint not null default 1,
  updated_at timestamptz not null default now()
);

create table public.command_center_commands (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  action text not null check (
    action in (
      'add-personal-task',
      'add-reminder',
      'add-learning',
      'complete-personal-task',
      'complete-reminder',
      'complete-learning'
    )
  ),
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'pending' check (
    status in ('pending', 'processing', 'done', 'failed')
  ),
  result jsonb,
  created_at timestamptz not null default now(),
  processed_at timestamptz
);

alter table public.command_center_snapshots enable row level security;
alter table public.command_center_commands enable row level security;

create policy "Users read own Command Center snapshot"
  on public.command_center_snapshots
  for select
  to authenticated
  using (auth.uid() = user_id);

create policy "Users read own Command Center commands"
  on public.command_center_commands
  for select
  to authenticated
  using (auth.uid() = user_id);

create policy "Users enqueue own Command Center commands"
  on public.command_center_commands
  for insert
  to authenticated
  with check (auth.uid() = user_id and status = 'pending');

revoke update, delete on public.command_center_snapshots from authenticated;
revoke update, delete on public.command_center_commands from authenticated;
