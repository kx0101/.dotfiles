import { taskEntityKey } from "./entity-identity.js";

export function buildChatContext(payload, selectedDate, today) {
  const futurePlan =
    selectedDate > today
      ? payload.daily_plans?.[selectedDate] ?? { personal: [], work: [] }
      : null;
  const personalTasks = futurePlan?.personal ?? payload.personal_tasks ?? [];
  const workTasks = futurePlan?.work ?? payload.work_tasks ?? [];
  const agenda = [
    ...(payload.agenda ?? []),
    ...(payload.calendar_plan ?? []),
  ].filter(
    (item, index, items) =>
      item.uid &&
      items.findIndex(
        (candidate) =>
          candidate.uid === item.uid &&
          candidate.calendar === item.calendar,
      ) === index,
  );

  return {
    calendars: payload.calendars ?? [],
    projects: (payload.projects ?? []).map((project) => project.name),
    parents: personalTasks
      .filter((item) => !String(item.line_number).startsWith("pending-"))
      .map((item) => ({
        area: "personal",
        title: item.title,
        parent_line: item.line_number,
        date: item.task_date,
      })),
    personal_tasks: personalTasks.slice(0, 100).map((item) => ({
      title: item.title,
      date: item.task_date,
      completed: Boolean(item.completed),
      entity_key: taskEntityKey("personal", item),
    })),
    work_tasks: workTasks.slice(0, 100).map((item) => ({
      title: item.title,
      date: item.task_date,
      completed: Boolean(item.completed),
      entity_key: taskEntityKey("work", item),
    })),
    reminders: (payload.reminders ?? []).slice(0, 100).map((item) => ({
      id: item.id,
      title: item.title,
      due: item.due ?? null,
      completed: Boolean(item.completed),
      list: item.list ?? "Reminders",
    })),
    agenda: agenda.slice(0, 100).map((item) => ({
      uid: item.uid,
      kind: item.kind,
      title: item.title,
      calendar: item.calendar,
      start: item.start,
      end: item.end,
      ref: item.command_center_ref ?? item.ref ?? null,
    })),
    learning: (payload.learning ?? []).slice(0, 100).map((item) => ({
      id: item.id,
      title: item.title,
      kind: item.kind,
      url: item.url ?? null,
    })),
    project_notes: (payload.projects ?? [])
      .flatMap((project) =>
        (project.notes ?? []).map((note) => ({
          id: note.id,
          project: project.name,
          title: note.text,
        })),
      )
      .slice(0, 100),
  };
}
