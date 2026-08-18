const ACTIONS = new Set([
  "add-personal-task",
  "add-work-task",
  "add-reminder",
  "add-learning",
  "add-project-note",
  "add-calendar-event",
]);

const WEEKDAYS = new Map([
  ["δευτερα", 1],
  ["deftera", 1],
  ["deutera", 1],
  ["τριτη", 2],
  ["triti", 2],
  ["trith", 2],
  ["τεταρτη", 3],
  ["tetarti", 3],
  ["tetarth", 3],
  ["πεμπτη", 4],
  ["pemti", 4],
  ["pempti", 4],
  ["pempth", 4],
  ["παρασκευη", 5],
  ["paraskevi", 5],
  ["paraskeuh", 5],
  ["σαββατο", 6],
  ["savvato", 6],
  ["κυριακη", 0],
  ["kyriaki", 0],
  ["kuriakh", 0],
]);

function fold(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("el-GR")
    .replaceAll("ς", "σ")
    .trim();
}

function hasAny(text, terms) {
  const padded = ` ${text.replace(/[^\p{L}\p{N}:./-]+/gu, " ")} `;
  return terms.some((term) => padded.includes(` ${term} `));
}

function isDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value ?? "")) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.valueOf()) && date.toISOString().slice(0, 10) === value;
}

function isoDate(year, month, day) {
  const value = [
    String(year).padStart(4, "0"),
    String(month).padStart(2, "0"),
    String(day).padStart(2, "0"),
  ].join("-");
  return isDate(value) ? value : null;
}

function addDays(value, days) {
  const date = new Date(`${value}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function parseDate(text, today) {
  const normalized = fold(text);
  const iso = normalized.match(/\b(\d{4}-\d{2}-\d{2})\b/);
  if (iso && isDate(iso[1])) return iso[1];

  const numeric = normalized.match(/\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\b/);
  if (numeric) {
    const currentYear = Number(today.slice(0, 4));
    const value = isoDate(
      Number(numeric[3] ?? currentYear),
      Number(numeric[2]),
      Number(numeric[1]),
    );
    if (value) return value;
  }

  if (hasAny(normalized, ["μεθαυριο", "methavrio", "metavrio", "day after tomorrow"])) {
    return addDays(today, 2);
  }
  if (hasAny(normalized, ["αυριο", "avrio", "tomorrow"])) return addDays(today, 1);
  if (hasAny(normalized, ["σημερα", "simera", "today"])) return today;

  const monthDay = normalized.match(
    /\b(?:στισ?\s+)?(\d{1,2})\s+(?:του\s+)?μηνα/,
  );
  if (monthDay) {
    const [year, month, currentDay] = today.split("-").map(Number);
    const day = Number(monthDay[1]);
    const thisMonth = isoDate(year, month, day);
    if (thisMonth && day >= currentDay) return thisMonth;
    const next = new Date(Date.UTC(year, month, 1));
    return isoDate(next.getUTCFullYear(), next.getUTCMonth() + 1, day);
  }

  for (const [name, weekday] of WEEKDAYS) {
    if (!hasAny(normalized, [name])) continue;
    const current = new Date(`${today}T12:00:00Z`).getUTCDay();
    const offset = (weekday - current + 7) % 7;
    return addDays(today, offset);
  }
  return null;
}

function parseTime(text) {
  const normalized = fold(text);
  if (hasAny(normalized, ["μεσανυχτα", "mesanyxta", "mesanixta", "midnight"])) {
    return { value: "00:00", ambiguous: false };
  }
  if (
    hasAny(normalized, ["μεσημερι", "mesimeri", "meshmeri", "noon"]) &&
    !/\d/.test(normalized)
  ) {
    return { value: "12:00", ambiguous: false };
  }

  const match =
    normalized.match(
      /(?:στισ?|stis|ωρα|ora)\s+(\d{1,2})(?::(\d{2}))?\s*(?:(?:το|to)\s+)?(πρωι|proi|prwi|πμ|am|μεσημερι|mesimeri|meshmeri|απογευμα|apogevma|apogeuma|βραδυ|vrady|vradi|μμ|pm)?/,
    ) ??
    normalized.match(
      /\b(\d{1,2}):(\d{2})\s*(πρωι|proi|prwi|πμ|am|μεσημερι|mesimeri|meshmeri|απογευμα|apogevma|apogeuma|βραδυ|vrady|vradi|μμ|pm)?/,
    ) ??
    normalized.match(
      /\b(\d{1,2})\s*(?:(?:το|to)\s+)?(πρωι|proi|prwi|πμ|am|μεσημερι|mesimeri|meshmeri|απογευμα|apogevma|apogeuma|βραδυ|vrady|vradi|μμ|pm)/,
    );
  if (!match) return { value: null, ambiguous: false };
  let hour = Number(match[1]);
  const hasMinute = match[2] && /^\d{2}$/.test(match[2]);
  const minute = Number(hasMinute ? match[2] : 0);
  const period = match[3] ?? (hasMinute ? "" : match[2]) ?? "";
  if (hour > 23 || minute > 59) return { value: null, ambiguous: false };

  if (hour === 12 && ["", "πρωι", "proi", "prwi", "πμ", "am"].includes(period)) {
    return { value: null, ambiguous: true };
  }
  if (["μεσημερι", "mesimeri", "meshmeri", "απογευμα", "apogevma", "apogeuma", "μμ", "pm"].includes(period)) {
    if (hour < 12) hour += 12;
  } else if (["βραδυ", "vrady", "vradi"].includes(period) && hour < 12) {
    hour += 12;
  }
  return {
    value: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`,
    ambiguous: false,
  };
}

function parseDuration(text) {
  const normalized = fold(text);
  const minutes = normalized.match(
    /\b(\d{1,3})\s*(?:λεπτα|λεπτο|lepta|lepto|mins?|minutes?)/,
  );
  if (minutes) {
    const value = Number(minutes[1]);
    return value >= 5 && value <= 480 ? value : null;
  }
  const hours = normalized.match(
    /\b(\d+(?:[.,]\d+)?)\s*(?:ωρεσ?|ωρα|wres?|wra|ora|hours?|hrs?)/,
  );
  if (hours) {
    const value = Math.round(Number(hours[1].replace(",", ".")) * 60);
    return value >= 5 && value <= 480 ? value : null;
  }
  return null;
}

function exactLabel(text, values) {
  const normalized = fold(text);
  return values.find((value) => normalized.includes(fold(value))) ?? null;
}

function removeLabel(text, label) {
  if (!label) return text;
  const index = fold(text).indexOf(fold(label));
  if (index < 0) return text;
  return `${text.slice(0, index)} ${text.slice(index + label.length)}`
    .replace(/(?:στο|στον|στη|στην|sto|calendar)\s*$/iu, "")
    .replace(/\s+/g, " ")
    .trim();
}

function quotedText(text) {
  return text.match(/[«"']([^»"']+)[»"']/)?.[1]?.trim() ?? null;
}

function removeFoldedMatches(text, pattern) {
  const matches = [...fold(text).matchAll(pattern)];
  let result = text;
  for (const match of matches.reverse()) {
    result =
      result.slice(0, match.index) +
      " ".repeat(match[0].length) +
      result.slice(match.index + match[0].length);
  }
  return result;
}

function removeFoldedPrefix(text, pattern) {
  const match = fold(text).match(pattern);
  return match ? text.slice(match[0].length) : text;
}

function cleanTitle(text, action) {
  const quoted = quotedText(text);
  if (quoted) return quoted;
  let title = String(text).trim();
  const removals = [
    /https?:\/\/\S+/g,
    /(?:για\s+)?(σημερα|simera|today|αυριο|avrio|tomorrow|μεθαυριο|methavrio|metavrio)/gu,
    /\b\d{4}-\d{2}-\d{2}\b/g,
    /\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{4})?\b/g,
    /(?:στισ?|stis)\s+\d{1,2}(?::\d{2})?(?:\s+(?:(?:το|to)\s+)?(?:πρωι|πμ|μεσημερι|απογευμα|βραδυ|proi|prwi|mesimeri|meshmeri|apogevma|apogeuma|vrady|vradi|am|pm))?/gu,
    /(?:(?:για|gia)\s+)?\d+(?:[.,]\d+)?\s*(?:λεπτα|λεπτο|lepta|lepto|mins?|minutes?|ωρεσ?|ωρα|wres?|wra|ora|hours?|hrs?)/gu,
    /(?:στισ?\s+)?\d{1,2}\s+(?:του\s+)?μηνα/gu,
    /(δευτερα|τριτη|τεταρτη|πεμπτη|παρασκευη|σαββατο|κυριακη)/gu,
  ];
  for (const pattern of removals) title = removeFoldedMatches(title, pattern);

  const prefixes = {
    "add-personal-task":
      /^(?:μπορεισ\s+να\s+|mporeis\s+na\s+)?(?:βαλε|βαλεισ|προσθεσε|προσθεσεισ|φτιαξε|φτιαξεισ|καταγραψε|καταγραψεισ|γραψε|γραψεισ|vale|valeis|prosthese|ftiakse)\s+(?:μου|mou)?\s*(?:ενα|ena)?\s*(?:προσωπικο\s+|personal\s+)?(?:task|todo|εργασια)\s*/u,
    "add-work-task":
      /^(?:μπορεισ\s+να\s+|mporeis\s+na\s+)?(?:βαλε|βαλεισ|προσθεσε|προσθεσεισ|φτιαξε|φτιαξεισ|καταγραψε|καταγραψεισ|γραψε|γραψεισ|vale|valeis|prosthese|ftiakse)\s+(?:μου|mou)?\s*(?:ενα|ena)?\s*(?:work|δουλεια(?:σ)?)\s+(?:task|todo|εργασια)?\s*/u,
    "add-reminder":
      /^(?:μπορεισ\s+να\s+|mporeis\s+na\s+)?(?:(?:βαλε|βαλεισ|προσθεσε|προσθεσεισ|φτιαξε|φτιαξεισ|καταγραψε|καταγραψεισ|vale|valeis|prosthese|ftiakse)\s+(?:μου|mou)?\s*(?:ενα|ena)?\s*(?:reminder|υπενθυμιση)|θυμισε\s+μου|thimise\s+mou)\s*/u,
    "add-learning":
      /^(?:μπορεισ\s+να\s+|mporeis\s+na\s+)?(?:βαλε|βαλεισ|προσθεσε|προσθεσεισ|φτιαξε|φτιαξεισ|καταγραψε|καταγραψεισ|κρατα|krata|vale|valeis|prosthese|ftiakse)\s+(?:μου|mou)?\s*(?:ενα|ena)?\s*(?:βιβλιο|αρθρο|βιντεο|book|article|video)\s*/u,
    "add-project-note":
      /^(?:μπορεισ\s+να\s+|mporeis\s+na\s+)?(?:βαλε|βαλεισ|προσθεσε|προσθεσεισ|φτιαξε|φτιαξεισ|καταγραψε|καταγραψεισ|κρατα|krata|γραψε|γραψεισ|vale|valeis|prosthese|ftiakse)\s+(?:μου|mou)?\s*(?:μια|mia)?\s*(?:σημειωση|simeiosi|shmeiosi|note)\s*/u,
    "add-calendar-event":
      /^(?:μπορεισ\s+να\s+|mporeis\s+na\s+)?(?:βαλε|βαλεισ|προσθεσε|προσθεσεισ|φτιαξε|φτιαξεισ|καταγραψε|καταγραψεισ|κλεισε|κλεισεισ|vale|valeis|prosthese|ftiakse)\s+(?:μου|mou)?\s*(?:μια|mia|ενα|ena)?\s*/u,
  };
  title = removeFoldedPrefix(title.trim(), prefixes[action]);
  if (action === "add-project-note") {
    title = removeFoldedPrefix(
      title.trim(),
      /^(?:στο|για\s+το|for)\s+\S+\s+(?:οτι|πωσ|that)?\s*/u,
    );
  }
  if (action === "add-learning") {
    title = removeFoldedPrefix(
      title.trim(),
      /^(?:βιβλιο|αρθρο|βιντεο|book|article|video)\s*/u,
    );
  }
  return title.replace(/\s+/g, " ").replace(/^[,;:–—-]+|[,;:?.!–—-]+$/g, "").trim();
}

function classify(text) {
  const normalized = fold(text);
  const hasReminder = hasAny(normalized, [
    "reminder",
    "υπενθυμιση",
    "θυμισε",
    "thimise",
  ]);
  const hasEvent = hasAny(normalized, [
    "call",
    "κληση",
    "meeting",
    "συναντηση",
    "ραντεβου",
    "event",
    "συμβαν",
  ]);
  if (hasReminder && hasEvent) return "choose-reminder-or-event";
  if (hasEvent) return "add-calendar-event";
  if (hasReminder) return "add-reminder";
  if (hasAny(normalized, ["σημειωση", "simeiosi", "shmeiosi", "project note"])) {
    return "add-project-note";
  }
  if (hasAny(normalized, ["βιβλιο", "book", "αρθρο", "article", "βιντεο", "video"])) {
    return "add-learning";
  }
  if (
    hasAny(normalized, ["work", "δουλεια", "δουλειασ"]) &&
    hasAny(normalized, ["task", "todo", "εργασια"])
  ) {
    return "add-work-task";
  }
  if (hasAny(normalized, ["task", "todo", "εργασια"])) return "add-personal-task";
  return null;
}

function learningKind(text) {
  const normalized = fold(text);
  if (hasAny(normalized, ["βιβλιο", "book"])) return "book";
  if (hasAny(normalized, ["βιντεο", "video"])) return "video";
  if (hasAny(normalized, ["αρθρο", "article"])) return "article";
  return null;
}

function requestedParent(text, parents, area) {
  const normalized = fold(text);
  if (!hasAny(normalized, ["κατω απο", "μεσα στο", "under", "parent"])) return null;
  return (
    parents.find(
      (parent) => parent.area === area && normalized.includes(fold(parent.title)),
    ) ?? "missing"
  );
}

function newDraft(action, text, context, options = {}) {
  if (action === "choose-reminder-or-event") {
    return { action, original: text, payload: {} };
  }
  const date = parseDate(text, context.today);
  const time = parseTime(text);
  const payload = {
    title: cleanTitle(text, action),
    date,
    parent_line: null,
    kind: action === "add-learning" ? learningKind(text) : null,
    url: text.match(/https?:\/\/\S+/i)?.[0]?.replace(/[),.;]+$/, "") ?? null,
    project: exactLabel(text, context.projects),
    calendar: exactLabel(text, context.calendars),
    start: null,
    duration: parseDuration(text),
  };

  if (
    action === "add-reminder" &&
    (time.value || time.ambiguous) &&
    !options.allowTimedReminder
  ) {
    return { action: "choose-reminder-or-event", original: text, payload: {} };
  }

  if (action === "add-calendar-event") {
    payload.title = removeLabel(payload.title, payload.calendar);
    if (hasAny(fold(text), ["call", "κληση"])) {
      payload.title = payload.title || "Κλήση";
    } else if (hasAny(fold(text), ["meeting", "συναντηση"])) {
      payload.title = payload.title || "Συνάντηση";
    }
    if (date && time.value) payload.start = `${date}T${time.value}`;
  }

  if (["add-personal-task", "add-work-task"].includes(action)) {
    const area = action === "add-work-task" ? "work" : "personal";
    const parent = requestedParent(text, context.parents, area);
    if (parent && parent !== "missing" && (!date || parent.date === date)) {
      payload.parent_line = parent.parent_line;
      payload.date = payload.date ?? parent.date;
    } else if (parent === "missing") {
      payload.parent_requested = true;
    }
  }
  return {
    action,
    payload,
    ambiguity: time.ambiguous ? "time-12" : null,
  };
}

function pendingField(draft) {
  if (draft.action === "choose-reminder-or-event") return "capture-kind";
  if (draft.ambiguity === "time-12") return "ambiguous-time";
  const { action, payload } = draft;
  if (!payload.title) return "title";
  if (payload.parent_requested) return "parent";
  if (action === "add-work-task" && !payload.date) return "date";
  if (action === "add-learning" && !payload.kind) return "kind";
  if (action === "add-project-note" && !payload.project) return "project";
  if (action === "add-calendar-event") {
    if (!payload.date) return "date";
    if (!payload.start) return "time";
    if (!payload.calendar) return "calendar";
    if (!payload.duration) return "duration";
  }
  return null;
}

function questionFor(draft, context) {
  const field = pendingField(draft);
  const options = {
    "capture-kind":
      "Θέλεις date-only Reminder ή Calendar event με συγκεκριμένη ώρα;",
    "ambiguous-time":
      "Με «12 το πρωί» εννοείς 12:00 το μεσημέρι ή 00:00 τα μεσάνυχτα;",
    title: "Ποιος είναι ο ακριβής τίτλος;",
    parent: "Δεν βρήκα αυτό το parent. Πες μου το ακριβές όνομά του.",
    date: "Για ποια ημερομηνία;",
    time: "Τι ώρα;",
    kind: "Είναι βιβλίο, άρθρο ή βίντεο;",
    project: `Σε ποιο project; Διαθέσιμα: ${context.projects.join(", ") || "κανένα"}.`,
    calendar: `Σε ποιο calendar; Διαθέσιμα: ${context.calendars.join(", ") || "κανένα"}.`,
    duration: "Πόση διάρκεια σε λεπτά;",
  };
  return options[field] ?? "";
}

function continueDraft(draft, text, context) {
  const normalized = fold(text);
  if (["ακυρο", "akyro", "cancel", "ξεχνα το", "forget it"].some(
    (value) => normalized.startsWith(value),
  )) {
    return { cancelled: true };
  }
  if (draft.action === "choose-reminder-or-event") {
    if (hasAny(normalized, ["calendar", "event", "συμβαν"])) {
      return newDraft("add-calendar-event", draft.original, context);
    }
    if (hasAny(normalized, ["reminder", "υπενθυμιση"])) {
      return newDraft("add-reminder", draft.original, context, {
        allowTimedReminder: true,
      });
    }
    return draft;
  }

  const field = pendingField(draft);
  const payload = { ...draft.payload };
  const next = { ...draft, payload };
  if (field === "ambiguous-time") {
    if (hasAny(normalized, ["μεσημερι", "mesimeri", "noon", "12:00"])) {
      const date = payload.date ?? parseDate(text, context.today);
      if (date) payload.start = `${date}T12:00`;
      next.ambiguity = null;
    } else if (hasAny(normalized, ["μεσανυχτα", "mesanyxta", "midnight", "00:00"])) {
      const date = payload.date ?? parseDate(text, context.today);
      if (date) payload.start = `${date}T00:00`;
      next.ambiguity = null;
    }
  } else if (field === "title") {
    payload.title = quotedText(text) ?? text.trim();
  } else if (field === "date") {
    payload.date = parseDate(text, context.today);
    if (draft.action === "add-calendar-event" && payload.date) {
      const time = parseTime(text);
      if (time.value) payload.start = `${payload.date}T${time.value}`;
      if (time.ambiguous) next.ambiguity = "time-12";
    }
  } else if (field === "time") {
    const time = parseTime(text);
    if (time.ambiguous) {
      next.ambiguity = "time-12";
    } else if (time.value && payload.date) {
      payload.start = `${payload.date}T${time.value}`;
    }
  } else if (field === "calendar") {
    payload.calendar = exactLabel(text, context.calendars);
  } else if (field === "duration") {
    const duration = parseDuration(text) ?? Number(text.match(/\d{1,3}/)?.[0]);
    payload.duration = duration >= 5 && duration <= 480 ? duration : null;
  } else if (field === "project") {
    payload.project = exactLabel(text, context.projects);
  } else if (field === "kind") {
    payload.kind = learningKind(text);
  } else if (field === "parent") {
    const area = draft.action === "add-work-task" ? "work" : "personal";
    const parent = context.parents.find(
      (item) => item.area === area && fold(text).includes(fold(item.title)),
    );
    if (parent) {
      payload.parent_line = parent.parent_line;
      payload.date = payload.date ?? parent.date;
      payload.parent_requested = false;
    }
  }
  return next;
}

function proposalFrom(draft) {
  const { action, payload } = draft;
  const payloads = {
    "add-personal-task": {
      title: payload.title,
      date: payload.date,
      parent_line: payload.parent_line,
    },
    "add-work-task": {
      title: payload.title,
      date: payload.date,
      parent_line: payload.parent_line,
    },
    "add-reminder": {
      title: payload.title,
      date: payload.date,
    },
    "add-learning": {
      title: payload.title,
      kind: payload.kind,
      url: payload.url,
    },
    "add-project-note": {
      title: payload.title,
      project: payload.project,
    },
    "add-calendar-event": {
      title: payload.title,
      calendar: payload.calendar,
      start: payload.start,
      duration: payload.duration,
    },
  };
  return { action, payload: payloads[action] };
}

function proposalReply(proposal) {
  const labels = {
    "add-personal-task": "Προτείνω αυτό το Personal task.",
    "add-work-task": "Προτείνω αυτό το Work task.",
    "add-reminder": "Προτείνω αυτή την υπενθύμιση.",
    "add-learning": "Προτείνω αυτό το Learning item.",
    "add-project-note": "Προτείνω αυτή τη σημείωση έργου.",
    "add-calendar-event": "Προτείνω αυτό το Calendar event.",
  };
  return `${labels[proposal.action]} Περιμένει επιβεβαίωση.`;
}

function sanitizeDraft(value) {
  if (!value || typeof value !== "object") return null;
  if (value.action === "choose-reminder-or-event") {
    return typeof value.original === "string" && value.original.length <= 2000
      ? { action: value.action, original: value.original, payload: {} }
      : null;
  }
  if (!ACTIONS.has(value.action) || !value.payload || typeof value.payload !== "object") {
    return null;
  }
  return {
    action: value.action,
    ambiguity: value.ambiguity === "time-12" ? "time-12" : null,
    payload: { ...value.payload },
  };
}

export function parseChat({ message, draft, context }) {
  const safeContext = {
    today: isDate(context.today) ? context.today : new Date().toISOString().slice(0, 10),
    calendars: Array.isArray(context.calendars) ? context.calendars : [],
    projects: Array.isArray(context.projects) ? context.projects : [],
    parents: Array.isArray(context.parents) ? context.parents : [],
  };
  const previous = sanitizeDraft(draft);
  const action = classify(message);
  let nextDraft =
    previous && !action
      ? continueDraft(previous, message, safeContext)
      : action
        ? newDraft(action, message, safeContext)
        : null;

  if (nextDraft?.cancelled) {
    return { reply: "Εντάξει, ακυρώθηκε.", proposal: null, draft: null };
  }
  if (!nextDraft) {
    const normalized = fold(message);
    if (["γεια", "γεια σου", "τι γινεται", "hello", "hi"].some(
      (value) => normalized.startsWith(value),
    )) {
      return {
        reply:
          "Μπορώ να προτείνω task, reminder, Calendar event, Learning item ή σημείωση έργου.",
        proposal: null,
        draft: null,
      };
    }
    return {
      reply:
        "Δεν κατάλαβα τι θέλεις να καταγράψω. Πες μου αν είναι task, reminder, event, Learning ή σημείωση έργου.",
      proposal: null,
      draft: null,
    };
  }

  const missing = pendingField(nextDraft);
  if (missing) {
    return {
      reply: questionFor(nextDraft, safeContext),
      proposal: null,
      draft: nextDraft,
    };
  }
  const proposal = proposalFrom(nextDraft);
  return {
    reply: proposalReply(proposal),
    proposal,
    draft: null,
  };
}
