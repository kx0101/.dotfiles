create table public.command_center_scratchpad (
  user_id uuid primary key references auth.users(id) on delete cascade,
  content text not null default '' check (length(content) <= 20000),
  updated_at timestamptz not null default now()
);

alter table public.command_center_scratchpad enable row level security;

create policy "Owner reads scratchpad"
  on public.command_center_scratchpad
  for select
  to authenticated
  using (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
  );

create policy "Owner creates scratchpad"
  on public.command_center_scratchpad
  for insert
  to authenticated
  with check (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
  );

create policy "Owner updates scratchpad"
  on public.command_center_scratchpad
  for update
  to authenticated
  using (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
  )
  with check (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
  );

create policy "Owner clears scratchpad"
  on public.command_center_scratchpad
  for delete
  to authenticated
  using (
    auth.uid() = user_id
    and auth.uid() = '4965a34f-c6b6-45ec-b595-d9f14f7a9294'::uuid
  );
