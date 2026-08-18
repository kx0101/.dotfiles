alter table public.command_center_commands
  drop constraint if exists command_center_commands_action_check;

alter table public.command_center_commands
  add constraint command_center_commands_action_check check (
    action in (
      'add-personal-task',
      'add-work-task',
      'add-reminder',
      'add-learning',
      'add-calendar-event',
      'complete-personal-task',
      'complete-work-task',
      'complete-reminder',
      'complete-learning'
    )
  );
