function normalize(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("el-GR");
}

function addDays(value, days) {
  const date = new Date(`${value}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function inferredDate(text, today) {
  const explicit = text.match(/\b(\d{4}-\d{2}-\d{2})\b/);
  if (explicit) return explicit[1];
  if (/μεθαυριο|methavrio|metavrio/.test(text)) return addDays(today, 2);
  if (/αυριο|aurio|avrio|tomorrow/.test(text)) return addDays(today, 1);
  if (/σημερα|simera|today/.test(text)) return today;
  return null;
}

function inferredTime(text) {
  const explicit = text.match(/\b(\d{1,2}):(\d{2})\b/);
  if (explicit) {
    return `${explicit[1].padStart(2, "0")}:${explicit[2]}`;
  }
  const natural = text.match(
    /(?:στις|stis)\s+(\d{1,2})(?:\s+το)?\s*(πρωι|proi|prwi|μεσημερι|mesimeri|meshmeri|απογευμα|apogevma|apogeuma|βραδυ|vradi|vrady)?/,
  );
  if (!natural) return null;
  let hour = Number(natural[1]);
  const period = natural[2] ?? "";
  if (
    /μεσημερι|mesimeri|meshmeri|απογευμα|apogevma|apogeuma|βραδυ|vradi|vrady/.test(
      period,
    ) &&
    hour < 12
  ) {
    hour += 12;
  }
  if (/πρωι|proi|prwi/.test(period) && hour === 12) return null;
  return `${String(hour).padStart(2, "0")}:00`;
}

export function inferEntitySearch(messages, today) {
  const text = normalize(
    messages
      .filter((message) => message.role === "user")
      .map((message) => message.content)
      .join(" "),
  );
  const needsExisting =
    /διαγραψ|σβησ|delete|remove|αλλαξ|edit|update|μεταφερ|ολοκληρ|complete|reopen|επαναφερ|τι εχω|τι υπαρχει|ο,?τι|βλεπ|δειξε|show/.test(
      text,
    );
  if (!needsExisting) return null;

  const types = [];
  if (/task|todo|εργασ|personal|work|δουλεια/.test(text)) {
    types.push("personal-task", "work-task");
  }
  if (/reminder|υπενθυμι/.test(text)) types.push("reminder");
  if (
    /call|κλησ|klis|klhs|event|calendar|συμβαν|ραντεβου|στις|stis/.test(
      text,
    )
  ) {
    types.push("agenda", "reminder");
  }
  if (/learning|βιβλι|book|αρθρ|article|βιντεο|video/.test(text)) {
    types.push("learning");
  }
  if (/σημειω|note|project/.test(text)) types.push("project-note");
  if (!types.length) {
    types.push(
      "personal-task",
      "work-task",
      "reminder",
      "agenda",
      "learning",
      "project-note",
    );
  }
  return {
    types: [...new Set(types)],
    date: inferredDate(text, today),
    time: inferredTime(text),
    query: null,
    completed: null,
  };
}

export function searchEntities(context, filters) {
  const items = [
    ...context.personalTasks.map(({ entity_key, ...item }) => ({
      type: "personal-task",
      ...item,
    })),
    ...context.workTasks.map(({ entity_key, ...item }) => ({
      type: "work-task",
      ...item,
    })),
    ...context.reminders.map((item) => ({
      type: "reminder",
      ...item,
    })),
    ...context.agenda.map((item) => ({
      type: "agenda",
      ...item,
    })),
    ...context.learning.map((item) => ({
      type: "learning",
      ...item,
    })),
    ...context.projectNotes.map((item) => ({
      type: "project-note",
      ...item,
    })),
  ];
  const query = normalize(filters.query);
  return items
    .filter((item) => filters.types.includes(item.type))
    .filter((item) => {
      if (!filters.date) return true;
      const value = item.date ?? item.due ?? item.start ?? "";
      return String(value).slice(0, 10) === filters.date;
    })
    .filter((item) => {
      if (!filters.time) return true;
      const value = item.due ?? item.start ?? "";
      return String(value).slice(11, 16) === filters.time;
    })
    .filter(
      (item) =>
        filters.completed === null ||
        Boolean(item.completed) === filters.completed,
    )
    .filter(
      (item) =>
        !query ||
        normalize(item.title).includes(query) ||
        query.includes(normalize(item.title)),
    )
    .slice(0, 30);
}
