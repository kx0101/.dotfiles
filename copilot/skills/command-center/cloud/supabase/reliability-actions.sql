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
      'add-project-note',
      'archive-project-note',
      'delete-agenda-item',
      'complete-personal-task',
      'complete-work-task',
      'complete-reminder',
      'complete-learning',
      'reopen-personal-task',
      'reopen-work-task',
      'delete-personal-task',
      'delete-work-task',
      'update-personal-task',
      'update-work-task',
      'update-reminder'
    )
  );
