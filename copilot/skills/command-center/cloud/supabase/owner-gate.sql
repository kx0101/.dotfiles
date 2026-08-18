drop policy if exists "Users read own Command Center snapshot"
  on public.command_center_snapshots;
drop policy if exists "Users read own Command Center commands"
  on public.command_center_commands;
drop policy if exists "Users enqueue own Command Center commands"
  on public.command_center_commands;
drop policy if exists "Users read own health summary"
  on public.command_center_health_daily;

create policy "Owner reads Command Center snapshot"
  on public.command_center_snapshots
  for select
  to authenticated
  using (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
  );

create policy "Owner reads Command Center commands"
  on public.command_center_commands
  for select
  to authenticated
  using (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
  );

create policy "Owner enqueues Command Center commands"
  on public.command_center_commands
  for insert
  to authenticated
  with check (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
    and status = 'pending'
  );

create policy "Owner reads health summary"
  on public.command_center_health_daily
  for select
  to authenticated
  using (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
  );
