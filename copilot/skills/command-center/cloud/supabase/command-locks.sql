alter table public.command_center_commands
  add column if not exists entity_key text;

create unique index if not exists command_center_one_active_entity
  on public.command_center_commands (user_id, entity_key)
  where entity_key is not null
    and status in ('pending', 'processing');
