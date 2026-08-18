import { createClient } from "@supabase/supabase-js";
import "./style.css";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const configured = Boolean(supabaseUrl && supabaseKey);
const supabase = configured ? createClient(supabaseUrl, supabaseKey) : null;
const $ = (selector) => document.querySelector(selector);
const OWNER_USER_ID = "4965a34f-c6b6-45ec-b595-d9f14f7a9294";
const CHAT_STORAGE_KEY = "command-center-chat-v2";

let session = null;
let learningKind = "book";
let snapshotPayload = {};
let pendingCommands = [];
let scratchpadTimer = null;
let selectedDate = localDate();
let availableSnapshots = [];
let chatMessages = [];
let chatPending = false;

function localDate(value = new Date()) {
  return new Date(value.getTime() - value.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 10);
}

function formatGreekDateValue(value) {
  if (!value) return "";
  const hasTime = String(value).includes("T");
  const date = new Date(hasTime ? value : `${value}T12:00:00`);
  if (Number.isNaN(date.valueOf())) return String(value).replace("T", " ");
  const options = {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  };
  if (hasTime) {
    options.hour = "2-digit";
    options.minute = "2-digit";
    options.hour12 = false;
    options.hourCycle = "h23";
  }
  return new Intl.DateTimeFormat("el-GR", options).format(date);
}

function isHistorical() {
  return selectedDate < localDate();
}

function isFuture() {
  return selectedDate > localDate();
}

function taskEntityKey(area, item) {
  return [
    "task",
    area,
    item.path ?? "",
    item.line_number ?? "",
    item.task_date ?? "",
  ].join(":");
}

function reminderEntityKey(item) {
  return `reminder:${item.id}`;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function empty(container, message = "Κανένα.") {
  container.replaceChildren(element("p", "empty", message));
}

function setStatus(message) {
  $("#status").replaceChildren(element("span", "", message));
}

function pendingActionLabel(action, payload = {}) {
  if (action === "add-calendar-event" && payload.operation === "update") {
    return "Επεξεργασία Calendar event";
  }
  return {
    "add-personal-task": "Personal task",
    "add-work-task": "Work task",
    "add-reminder": "Reminder",
    "add-learning": "Learning",
    "add-project-note": "Σημείωση έργου",
    "add-calendar-event": "Calendar event",
    "update-calendar-event": "Επεξεργασία Calendar event",
    "complete-personal-task": "Ολοκλήρωση Personal task",
    "complete-work-task": "Ολοκλήρωση Work task",
    "complete-reminder": "Ολοκλήρωση Reminder",
    "complete-learning": "Ολοκλήρωση Learning",
    "update-personal-task": "Επεξεργασία Personal task",
    "update-work-task": "Επεξεργασία Work task",
    "update-reminder": "Επεξεργασία Reminder",
    "delete-personal-task": "Διαγραφή Personal task",
    "delete-work-task": "Διαγραφή Work task",
    "delete-agenda-item": "Διαγραφή από Πρόγραμμα",
    "archive-project-note": "Αρχειοθέτηση σημείωσης",
  }[action] ?? action;
}

function renderPendingQueue(commands) {
  const container = $("#pending-queue");
  container.replaceChildren();
  container.classList.toggle("hidden", !commands.length);
  if (!commands.length) return;
  const heading = element("div", "pending-queue-heading");
  heading.append(
    element("strong", "", "Σε αναμονή"),
    element("span", "count", String(commands.length)),
  );
  const list = element("div", "pending-queue-list");
  for (const command of commands) {
    const row = element("div", "pending-queue-row");
    const copy = element("div");
    copy.append(
      element(
        "strong",
        "",
        command.payload.title ??
          pendingActionLabel(command.action, command.payload),
      ),
      element(
        "span",
        "item-meta",
        [
          pendingActionLabel(command.action, command.payload),
          formatGreekDateValue(
            command.payload.start ?? command.payload.date ?? "",
          ),
        ]
          .filter(Boolean)
          .join(" · "),
      ),
    );
    row.append(
      copy,
      element(
        "span",
        "pending-state",
        command.status === "processing" ? "Εκτελείται" : "Αναμονή",
      ),
    );
    list.append(row);
  }
  container.append(heading, list);
}

function loadChatHistory() {
  try {
    const value = JSON.parse(
      localStorage.getItem(CHAT_STORAGE_KEY) ?? "[]",
    );
    chatMessages = Array.isArray(value) ? value.slice(-40) : [];
  } catch {
    chatMessages = [];
    localStorage.removeItem(CHAT_STORAGE_KEY);
  }
}

function saveChatHistory() {
  localStorage.setItem(
    CHAT_STORAGE_KEY,
    JSON.stringify(chatMessages.slice(-40)),
  );
}

function proposalLabel(action) {
  return {
    "add-personal-task": "Νέο Personal task",
    "add-work-task": "Νέο Work task",
    "add-reminder": "Νέα υπενθύμιση",
    "add-learning": "Νέο Learning item",
    "add-project-note": "Νέα σημείωση έργου",
    "add-calendar-event": "Νέο συμβάν",
    "complete-personal-task": "Ολοκλήρωση Personal task",
    "complete-work-task": "Ολοκλήρωση Work task",
    "reopen-personal-task": "Επαναφορά Personal task",
    "reopen-work-task": "Επαναφορά Work task",
    "delete-personal-task": "Διαγραφή Personal task",
    "delete-work-task": "Διαγραφή Work task",
    "update-personal-task": "Επεξεργασία Personal task",
    "update-work-task": "Επεξεργασία Work task",
    "complete-reminder": "Ολοκλήρωση υπενθύμισης",
    "update-reminder": "Επεξεργασία υπενθύμισης",
    "delete-agenda-item": "Διαγραφή από Πρόγραμμα",
    "update-calendar-event": "Επεξεργασία συμβάντος",
    "complete-learning": "Ολοκλήρωση Learning item",
    "archive-project-note": "Αρχειοθέτηση σημείωσης έργου",
  }[action] ?? action;
}

function proposalDetails(proposal) {
  const payload = proposal.payload;
  const labels = {
    title: "Τίτλος",
    date: "Ημερομηνία",
    calendar: "Calendar",
    start: "Έναρξη",
    duration: "Διάρκεια",
    project: "Έργο",
    kind: "Τύπος",
    url: "URL",
  };
  if (
    ["update-personal-task", "update-work-task"].includes(proposal.action)
  ) {
    return [
      ["Από", payload.old_title],
      ["Σε", payload.title],
      ["Ημερομηνία", formatGreekDateValue(payload.date)],
    ];
  }
  if (proposal.action === "update-calendar-event") {
    return [
      ["Τίτλος", payload.title],
      ["Έναρξη", formatGreekDateValue(payload.start)],
      ["Διάρκεια", `${payload.duration} λεπτά`],
      ["Calendar", payload.calendar],
    ];
  }
  if (proposal.action === "delete-agenda-item") {
    return [
      ["Τίτλος", payload.title],
      ["Τύπος", payload.kind === "reminder" ? "Reminder" : "Event"],
      ["Calendar", payload.calendar],
    ];
  }
  return Object.entries(payload)
    .filter(
      ([key, value]) =>
        value !== null &&
        value !== "" &&
        !["id", "uid", "ref", "parent_line", "current_date"].includes(key),
    )
    .map(([key, value]) => [
      labels[key] ?? key,
      ["date", "start"].includes(key)
        ? formatGreekDateValue(value)
        : key === "duration"
          ? `${value} λεπτά`
          : String(value),
    ]);
}

function renderChat() {
  const container = $("#chat-messages");
  container.replaceChildren();
  if (!chatMessages.length) {
    container.append(
      element(
        "div",
        "chat-message assistant",
        "Είμαι εδώ. Μίλησέ μου φυσικά ή πες μου τι θέλεις να καταγράψεις.",
      ),
    );
  }
  for (const message of chatMessages) {
    container.append(
      element("div", `chat-message ${message.role}`, message.content),
    );
    const proposals = Array.isArray(message.proposals)
      ? message.proposals
      : message.proposal
        ? [message.proposal]
        : [];
    for (const [index, proposalData] of proposals.entries()) {
      const proposal = element("section", "chat-proposal");
      proposal.append(
        element("strong", "", proposalLabel(proposalData.action)),
      );
      const details = element("dl");
      for (const [label, value] of proposalDetails(proposalData)) {
        details.append(
          element("dt", "", label),
          element("dd", "", String(value)),
        );
      }
      proposal.append(details);
      const executed = (message.executedProposals ?? []).includes(index);
      const execute = element(
        "button",
        "",
        executed
          ? "Καταγράφηκε"
          : message.superseded
            ? "Αντικαταστάθηκε"
            : "Εκτέλεση",
      );
      execute.type = "button";
      execute.disabled = executed || Boolean(message.superseded);
      execute.addEventListener("click", () =>
        executeProposal(message, proposalData, index, execute),
      );
      proposal.append(execute);
      container.append(proposal);
    }
  }
  if (chatPending) {
    const loader = element("div", "chat-message assistant chat-loading");
    loader.setAttribute("role", "status");
    loader.setAttribute("aria-label", "Η Πυξίδα απαντά");
    loader.append(element("span"), element("span"), element("span"));
    container.append(loader);
  }
  container.scrollTop = container.scrollHeight;
}

function chatContext() {
  const parents = [
    ...(snapshotPayload.personal_tasks ?? []).map((item) => ({
      area: "personal",
      title: item.title,
      parent_line: item.line_number,
      date: item.task_date,
    })),
  ].filter((item) => !String(item.parent_line).startsWith("pending-"));
  const agenda = [
    ...(snapshotPayload.agenda ?? []),
    ...(snapshotPayload.calendar_plan ?? []),
  ].filter(
    (item, index, items) =>
      items.findIndex(
        (candidate) =>
          candidate.uid === item.uid &&
          candidate.calendar === item.calendar,
      ) === index,
  );
  return {
    calendars: snapshotPayload.calendars ?? [],
    projects: (snapshotPayload.projects ?? []).map((project) => project.name),
    parents,
    personal_tasks: (snapshotPayload.personal_tasks ?? [])
      .slice(0, 100)
      .map((item) => ({
        title: item.title,
        date: item.task_date,
        completed: Boolean(item.completed),
        entity_key: taskEntityKey("personal", item),
      })),
    work_tasks: (snapshotPayload.work_tasks ?? [])
      .slice(0, 100)
      .map((item) => ({
        title: item.title,
        date: item.task_date,
        completed: Boolean(item.completed),
        entity_key: taskEntityKey("work", item),
      })),
    reminders: (snapshotPayload.all_reminders ?? snapshotPayload.reminders ?? [])
      .slice(0, 100)
      .map((item) => ({
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
      ref: item.command_center_ref ?? null,
    })),
    learning: (snapshotPayload.learning ?? []).slice(0, 100).map((item) => ({
      id: item.id,
      title: item.title,
      kind: item.kind,
      url: item.url ?? null,
    })),
    project_notes: (snapshotPayload.projects ?? [])
      .flatMap((project) =>
        (project.notes ?? []).map((note) => ({
          id: note.id,
          project: project.name,
          title: note.text,
        })),
      )
      .slice(0, 100),
    selected_date: selectedDate,
  };
}

async function sendChatMessage(event) {
  event.preventDefault();
  const input = $("#chat-input");
  const content = input.value.trim();
  if (!content) return;
  const button = event.submitter ?? $("#chat-form button[type='submit']");
  button.disabled = true;
  input.value = "";
  chatMessages.push({
    id: crypto.randomUUID(),
    role: "user",
    content,
  });
  chatPending = true;
  renderChat();
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        messages: chatMessages.map(({ role, content: text }) => ({
          role,
          content: text,
        })),
        context: chatContext(),
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error ?? `HTTP ${response.status}`);
    }
    for (const message of chatMessages) {
      if (message.role === "assistant" && (message.proposals ?? []).length) {
        message.superseded = true;
      }
    }
    chatPending = false;
    chatMessages.push({
      id: crypto.randomUUID(),
      role: "assistant",
      content: payload.reply,
      proposals: payload.proposals,
      executedProposals: [],
    });
    saveChatHistory();
    renderChat();
  } catch (error) {
    chatPending = false;
    chatMessages.push({
      id: crypto.randomUUID(),
      role: "assistant",
      content: `Αποτυχία: ${error.message}`,
    });
    saveChatHistory();
    renderChat();
  } finally {
    chatPending = false;
    button.disabled = false;
    input.focus();
  }
}

async function executeProposal(message, proposal, index, button) {
  const allowed = new Set([
    "add-personal-task",
    "add-work-task",
    "add-reminder",
    "add-learning",
    "add-project-note",
    "add-calendar-event",
    "complete-personal-task",
    "complete-work-task",
    "reopen-personal-task",
    "reopen-work-task",
    "delete-personal-task",
    "delete-work-task",
    "update-personal-task",
    "update-work-task",
    "complete-reminder",
    "update-reminder",
    "delete-agenda-item",
    "update-calendar-event",
    "complete-learning",
    "archive-project-note",
  ]);
  if (!allowed.has(proposal.action)) {
    throw new Error("Μη επιτρεπτή ενέργεια.");
  }
  button.disabled = true;
  try {
    const queueAction =
      proposal.action === "update-calendar-event"
        ? "add-calendar-event"
        : proposal.action;
    const queuePayload =
      proposal.action === "update-calendar-event"
        ? { ...proposal.payload, operation: "update" }
        : proposal.payload;
    await enqueue(
      queueAction,
      queuePayload,
      proposal.entity_key ?? `chat:${message.id}:${index}`,
    );
    message.executedProposals = [
      ...new Set([...(message.executedProposals ?? []), index]),
    ];
    saveChatHistory();
    renderChat();
    setStatus("Η ενέργεια περιμένει συγχρονισμό με το Mac.");
    await refresh();
  } catch (error) {
    button.disabled = false;
    setStatus(`Αποτυχία εκτέλεσης: ${error.message}`);
  }
}

function showLogin() {
  const status = $("#status");
  status.replaceChildren(
    element("span", "", "Κάνε GitHub login για να δεις την Πυξίδα. "),
  );
  const login = element("button", "", "GitHub login");
  login.type = "button";
  login.addEventListener("click", () => {
    supabase.auth.signInWithOAuth({
      provider: "github",
      options: { redirectTo: window.location.origin },
    });
  });
  status.append(login);
}

function renderTasks(selector, items, action) {
  const container = $(selector);
  container.replaceChildren();
  if (!items.length) {
    empty(container);
    return;
  }
  for (const item of items) {
    const area =
      action === "complete-work-task" ? "work" : "personal";
    const entityKey = taskEntityKey(area, item);
    const locked =
      item.pending === true ||
      pendingCommands.some(
        (command) => command.entity_key === entityKey,
      );
    const row = element(
      "label",
      `task-row${item.completed ? " completed" : ""}`,
    );
    const depth = Math.min(item.parent_path?.length ?? 0, 8);
    row.classList.add(`task-depth-${depth}`);
    const checkbox = element("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(item.completed);
    checkbox.disabled = isHistorical() || locked;
    if (locked) row.classList.add("pending");
    if (!isHistorical() && !locked) {
      checkbox.addEventListener("change", async () => {
        checkbox.disabled = true;
        try {
          const nextAction = checkbox.checked
            ? action
            : action === "complete-work-task"
              ? "reopen-work-task"
              : "reopen-personal-task";
          await enqueue(nextAction, {
            title: item.title,
            date: item.task_date,
          }, entityKey);
          setStatus("Η αλλαγή περιμένει συγχρονισμό με το Mac.");
          await refresh();
        } catch (error) {
          checkbox.checked = !checkbox.checked;
          checkbox.disabled = false;
          setStatus(`Αποτυχία: ${error.message}`);
        }
      });
    }
    row.append(checkbox, element("span", "", item.title));
    if (!item.completed && !isHistorical() && !locked) {
      const edit = element("button", "task-edit", "Επεξεργασία");
      edit.type = "button";
      edit.addEventListener("click", (event) => {
        event.preventDefault();
        openEdit(
          action === "complete-work-task" ? "Work" : "Personal",
          item,
          entityKey,
        );
      });
      row.append(edit);
    }
    if (!isHistorical() && !locked) {
      const remove = element("button", "task-delete", "Διαγραφή");
      remove.type = "button";
      remove.addEventListener("click", (event) => {
        event.preventDefault();
        deleteTodo(area, item, entityKey, remove);
      });
      row.append(remove);
    }
    container.append(row);
  }
}

function formatTime(value) {
  if (!value) return "Ολοήμερο";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value.slice(11, 16);
  return new Intl.DateTimeFormat("el-GR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    hourCycle: "h23",
  }).format(date);
}

function joinLink(event) {
  const source = `${event.url ?? ""} ${event.description ?? ""}`;
  return (
    source.match(
      /https:\/\/(?:meet\.google\.com|[^/\s]+\.zoom\.us|teams\.microsoft\.com|teams\.live\.com)\/[^\s<>"]+/i,
    )?.[0] ?? null
  );
}

function renderAgenda(events) {
  const container = $("#agenda");
  container.replaceChildren();
  if (!events.length) {
    empty(container);
    return;
  }
  for (const event of events) {
    const row = element("div", "agenda-row");
    if (event.pending) row.classList.add("pending");
    const completed =
      event.completed === true ||
      event.title.startsWith("✓ ") ||
      (event.all_day === "false" &&
        event.end &&
        new Date(event.end) <= new Date());
    if (completed) row.classList.add("agenda-completed");
    row.append(
      element(
        "span",
        "agenda-time",
        event.all_day === "true" ? "Όλη μέρα" : formatTime(event.start),
      ),
    );
    const copy = element("div", "agenda-copy");
    copy.append(
      element("div", "agenda-title", event.title),
      element(
        "div",
        "agenda-calendar",
        event.pending
          ? `${event.calendar} · Σε αναμονή`
          : event.calendar,
      ),
    );
    row.append(copy);
    const link = joinLink(event);
    if (link) {
      const anchor = element("a", "meet-link", "Σύνδεση");
      anchor.href = link;
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      row.append(anchor);
    }
    if (event.uid && !isHistorical()) {
      const remove = element("button", "agenda-delete", "Διαγραφή");
      remove.type = "button";
      remove.addEventListener("click", () => deleteAgendaItem(event, remove));
      row.append(remove);
    }
    container.append(row);
  }
}

function reminderDue(value) {
  if (!value) return "Χωρίς ημερομηνία";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  const options = {
    weekday: "short",
    day: "numeric",
    month: "short",
  };
  if (/T(?!00:00)\d{2}:\d{2}/.test(value)) {
    options.hour = "2-digit";
    options.minute = "2-digit";
    options.hour12 = false;
    options.hourCycle = "h23";
  }
  return new Intl.DateTimeFormat("el-GR", options).format(date);
}

function renderReminders(items) {
  const container = $("#reminders");
  container.replaceChildren();
  if (!items.length) {
    empty(container);
    return;
  }
  for (const item of items) {
    const entityKey = reminderEntityKey(item);
    const locked =
      item.pending === true ||
      pendingCommands.some(
        (command) => command.entity_key === entityKey,
      );
    const row = element("label", "reminder-row");
    const checkbox = element("input");
    checkbox.type = "checkbox";
    checkbox.disabled = isHistorical() || locked || Boolean(item.completed);
    if (locked) row.classList.add("pending");
    checkbox.checked = Boolean(item.completed);
    if (item.completed) row.classList.add("completed");
    if (!isHistorical() && !locked && !item.completed) {
      checkbox.addEventListener("change", async () => {
        if (!checkbox.checked) return;
        checkbox.disabled = true;
        try {
          await enqueue("complete-reminder", { id: item.id }, entityKey);
          setStatus("Η ολοκλήρωση περιμένει συγχρονισμό με το Mac.");
        } catch (error) {
          checkbox.checked = false;
          checkbox.disabled = false;
          setStatus(`Αποτυχία: ${error.message}`);
        }
      });
    }
    const copy = element("div", "reminder-copy");
    copy.append(
      element("span", "", item.title),
      element("span", "item-meta", reminderDue(item.due)),
    );
    row.append(checkbox, copy);
    if (!isHistorical() && !locked) {
      const edit = element("button", "reminder-edit", "Επεξεργασία");
      edit.type = "button";
      edit.addEventListener("click", (event) => {
        event.preventDefault();
        openEdit("Reminder", item, entityKey);
      });
      row.append(edit);
    }
    container.append(row);
  }
}

function normalizedLearningKind(kind) {
  return kind === "resource" || kind === "course" ? "article" : kind;
}

function renderLearning(items) {
  document.querySelectorAll(".learning-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.kind === learningKind);
  });
  const filtered = items.filter(
    (item) => normalizedLearningKind(item.kind) === learningKind,
  );
  const container = $("#learning");
  container.replaceChildren();
  if (!filtered.length) {
    empty(container);
    return;
  }
  for (const item of filtered) {
    const entityKey = `learning:${item.id}`;
    const locked =
      item.pending === true ||
      pendingCommands.some(
        (command) => command.entity_key === entityKey,
      );
    const row = element("article", "learning-row");
    if (locked) row.classList.add("pending");
    const copy = element("div", "learning-copy");
    if (item.url) {
      const link = element("a", "learning-link", item.title);
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      copy.append(link);
    } else {
      copy.append(element("strong", "", item.title));
    }
    row.append(copy);
    if (!isHistorical() && !locked) {
      const remove = element("button", "learning-remove", "Αφαίρεση");
      remove.type = "button";
      remove.addEventListener("click", async () => {
        remove.disabled = true;
        try {
          await enqueue("complete-learning", { id: item.id }, entityKey);
          setStatus("Η αφαίρεση περιμένει συγχρονισμό με το Mac.");
        } catch (error) {
          remove.disabled = false;
          setStatus(`Αποτυχία: ${error.message}`);
        }
      });
      row.append(remove);
    }
    container.append(row);
  }
}

function renderProjects(projects) {
  const lifecycleOrder = { live: 0, development: 1, planned: 2 };
  const lifecycleLabels = {
    live: "Σε λειτουργία",
    development: "Σε ανάπτυξη",
    planned: "Σχεδιασμένο",
  };
  const sorted = [...projects].sort((first, second) => {
    const lifecycle =
      (lifecycleOrder[first.lifecycle] ?? 99) -
      (lifecycleOrder[second.lifecycle] ?? 99);
    return lifecycle || first.name.localeCompare(second.name, "el");
  });
  const container = $("#projects");
  const projectSelect = $("#capture-project");
  const selectedProject = projectSelect.value;
  projectSelect.replaceChildren(new Option("Χωρίς έργο", ""));
  for (const project of sorted) {
    projectSelect.append(new Option(project.name, project.name));
  }
  if (
    [...projectSelect.options].some(
      (option) => option.value === selectedProject,
    )
  ) {
    projectSelect.value = selectedProject;
  }
  container.replaceChildren();
  if (!sorted.length) {
    empty(container);
    return;
  }
  for (const project of sorted) {
    const card = element("button", "project-card");
    card.type = "button";
    card.append(
      element("strong", "", project.name),
      element(
        "span",
        "item-meta",
        lifecycleLabels[project.lifecycle] ?? project.lifecycle,
      ),
    );
    card.addEventListener("click", () => openProject(project));
    container.append(card);
  }
}

function selectedCaptureKind() {
  const kind = $("#capture-kind").value;
  return ["task", "learning"].includes(kind)
    ? $("#capture-subtype").value
    : kind;
}

function configureCaptureSubtype() {
  const kind = $("#capture-kind").value;
  const select = $("#capture-subtype");
  const previous = select.value;
  const options =
    kind === "task"
      ? [
          ["personal-task", "Προσωπικά"],
          ["work-task", "Δουλειά"],
        ]
      : kind === "learning"
        ? [
            ["book", "Βιβλίο"],
            ["article", "Άρθρο"],
            ["video", "Βίντεο"],
          ]
        : [];
  select.replaceChildren(
    ...options.map(([value, label]) => new Option(label, value)),
  );
  select.classList.toggle("hidden", !options.length);
  if (options.some(([value]) => value === previous)) {
    select.value = previous;
  }
  updateCaptureFields();
}

function renderCaptureParents() {
  const select = $("#capture-parent");
  const selected = select.value;
  select.replaceChildren(new Option("Νέο κύριο todo", ""));
  const kind = selectedCaptureKind();
  if (
    !["personal-task", "work-task"].includes(kind) ||
    $("#capture-date").value !== selectedDate ||
    isHistorical()
  ) {
    return;
  }
  const items =
    kind === "work-task"
      ? snapshotPayload.work_tasks ?? []
      : snapshotPayload.personal_tasks ?? [];
  for (const item of items.filter((task) => !task.completed)) {
    const label = [...(item.parent_path ?? []), item.title].join(" → ");
    select.append(new Option(label, String(item.line_number)));
  }
  if ([...select.options].some((option) => option.value === selected)) {
    select.value = selected;
  }
}

function detailSection(title, content) {
  const section = element("section", "detail-section");
  section.append(element("h3", "", title), content);
  return section;
}

function projectRepository(item) {
  return item?.repository?.nameWithOwner ?? item?.repository ?? "";
}

function formatGreekDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("el-GR", {
    timeZone: "Europe/Athens",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function openProject(project) {
  $("#project-title").textContent = project.name;
  const detail = $("#project-detail");
  detail.replaceChildren();

  const health = element("div", "list");
  const checks = (snapshotPayload.system_health ?? []).filter(
    (check) => check.project === project.name,
  );
  if (checks.length) {
    for (const check of checks) {
      const row = element("div", "health-row");
      row.append(
        element("span", "", check.label),
        element(
          "span",
          check.up ? "health-up" : "health-down",
          check.up ? "UP" : "DOWN",
        ),
      );
      health.append(row);
    }
  } else {
    empty(health);
  }
  detail.append(detailSection("Κατάσταση", health));

  const tasks = element("div", "list");
  if (project.tasks?.length) {
    for (const task of project.tasks) {
      tasks.append(element("div", "list-item", task.title));
    }
  } else {
    empty(tasks, "Δεν υπάρχουν ανοιχτά tasks.");
  }
  detail.append(detailSection("Εργασίες", tasks));

  const notes = element("div", "list");
  const projectNotes = (project.notes ?? []).filter(
    (note) =>
      !pendingCommands.some(
        (command) =>
          command.action === "archive-project-note" &&
          command.payload.project === project.name &&
          command.payload.id === note.id,
      ),
  );
  if (projectNotes.length) {
    for (const note of projectNotes) {
      const card = element("article", "list-item");
      card.append(
        element("p", "", note.text),
        element(
          "p",
          "item-meta",
          `${formatGreekDateTime(note.timestamp)} · ${note.source}`,
        ),
      );
      if (!isHistorical()) {
        const remove = element("button", "note-delete", "Διαγραφή");
        remove.type = "button";
        remove.addEventListener("click", () => {
          archiveProjectNote(project, note, remove);
        });
        card.append(remove);
      }
      notes.append(card);
    }
  } else {
    empty(notes, "Δεν υπάρχουν σημειώσεις έργου.");
  }
  detail.append(detailSection("Σημειώσεις έργου", notes));

  const github = snapshotPayload.github ?? {};
  const authored = (github.authored_open ?? []).filter(
    (item) => projectRepository(item) === project.github,
  );
  const reviews = (github.review_requested ?? []).filter(
    (item) => projectRepository(item) === project.github,
  );
  const failures = (github.failing_ci ?? []).filter(
    (item) => item.repository === project.github,
  );
  const githubStats = element("div", "detail-stats");
  githubStats.append(
    element("div", "list-item", `Ανοιχτά PRs: ${authored.length}`),
    element("div", "list-item", `Αιτήματα review: ${reviews.length}`),
    element("div", "list-item", `Αποτυχημένο CI: ${failures.length}`),
  );
  detail.append(detailSection("GitHub", githubStats));

  if (project.name === "BookIt") {
    const business = snapshotPayload.bookit_business ?? {};
    const metrics = business.metrics ?? {};
    const money = new Intl.NumberFormat("el-GR", {
      style: "currency",
      currency: String(metrics.currency ?? "EUR").toUpperCase(),
    });
    const businessStats = element("div", "business-grid");
    for (const [label, value] of [
      ["MRR", money.format((metrics.mrr_cents ?? 0) / 100)],
      ["Ενεργές", String(metrics.active ?? 0)],
      ["Δοκιμές", String(metrics.trialing ?? 0)],
      ["Υπό ακύρωση", String(metrics.cancelling ?? 0)],
    ]) {
      const card = element("div", "business-stat");
      card.append(
        element("span", "summary-label", label),
        element("strong", "", value),
      );
      businessStats.append(card);
    }
    detail.prepend(detailSection("BookIt οικονομικά", businessStats));

    const billing = element("div", "list");
    const billingRows = [
      ...(business.attention ?? []).map((item) => ({
        ...item,
        state: "Προσοχή",
      })),
      ...(business.cancelling ?? []).map((item) => ({
        ...item,
        state: "Ακύρωση",
      })),
      ...(business.renewing_soon ?? []).map((item) => ({
        ...item,
        state: "Ανανέωση",
      })),
    ];
    if (billingRows.length) {
      for (const row of billingRows) {
        billing.append(
          element(
            "div",
            "list-item",
            `${row.state} · ${row.display_name ?? "Unknown"} · ${formatGreekDateTime(
              row.next_billing_at ?? row.ends_at,
            )}`,
          ),
        );
      }
    } else {
      empty(billing, "Δεν υπάρχουν billing exceptions.");
    }
    detail.append(detailSection("Χρεώσεις και ανανεώσεις", billing));

    const emails = element("div", "list");
    for (const message of snapshotPayload.bookit_emails?.emails ?? []) {
      const card = element("article", "mail-card");
      card.append(
        element("strong", "", message.subject),
        element(
          "p",
          "item-meta",
          `${message.last_event} · ${(message.recipients ?? []).join(", ")}`,
        ),
      );
      emails.append(card);
    }
    detail.append(detailSection("Πρόσφατα email BookIt", emails));
  }

  const dialog = $("#project-dialog");
  if (!dialog.open) dialog.showModal();
}

function renderHealth(row) {
  const container = $("#apple-health");
  container.replaceChildren();
  if (!row) {
    const note = element("div", "local-only");
    note.append(
      element("strong", "", "Περιμένει συγχρονισμό Apple Health"),
      element("span", "", "Το daily Shortcut δεν έχει στείλει ακόμη δεδομένα."),
    );
    container.append(note);
    return;
  }
  const metrics = [
    ["Βήματα", new Intl.NumberFormat("el-GR").format(row.steps ?? 0)],
    [
      "Ύπνος",
      `${Math.floor((row.sleep_minutes ?? 0) / 60)}ω ${
        (row.sleep_minutes ?? 0) % 60
      }λ`,
    ],
    ["Ενεργή ενέργεια", `${Math.round(row.active_energy_kcal ?? 0)} kcal`],
    ["Καρδιακός ρυθμός ηρεμίας", `${Math.round(row.resting_heart_rate ?? 0)} bpm`],
  ];
  for (const [label, value] of metrics) {
    const result = element("div", "health-metric");
    result.append(
      element("span", "summary-label", label),
      element("strong", "", value),
    );
    container.append(result);
  }
}

function renderSystemHealth(checks) {
  const container = $("#health");
  container.replaceChildren();
  if (!checks.length) {
    empty(container);
    return;
  }
  for (const check of checks) {
    const row = element("div", "health-row");
    row.append(
      element("span", "", `${check.project} · ${check.label}`),
      element(
        "span",
        check.up ? "health-up" : "health-down",
        check.up ? "UP" : "DOWN",
      ),
    );
    container.append(row);
  }
}

function mailLink(messageId) {
  if (!messageId) return null;
  const normalized = messageId.startsWith("<")
    ? messageId
    : `<${messageId}>`;
  return `message://${encodeURIComponent(normalized)}`;
}

function renderMail(messages) {
  const container = $("#mail");
  container.replaceChildren();
  if (!messages.length) {
    empty(container, "Κανένα πρόσφατο μήνυμα.");
    return;
  }
  for (const message of messages) {
    const target = mailLink(message.message_id);
    const card = element(target ? "a" : "article", "mail-card");
    if (target) card.href = target;
    if (message.read === "false") card.classList.add("mail-unread");
    card.append(
      element("strong", "", message.subject),
      element(
        "p",
        "item-meta",
        `${message.read === "false" ? "Μη αναγνωσμένο" : "Αναγνωσμένο"} · ${message.sender}`,
      ),
      element(
        "p",
        "item-meta",
        new Intl.DateTimeFormat("el-GR", {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }).format(new Date(message.received)),
      ),
    );
    container.append(card);
  }
}

function renderCalendars(calendars) {
  const select = $("#event-calendar");
  select.replaceChildren(new Option("Επίλεξε calendar", "", true, true));
  select.options[0].disabled = true;
  for (const calendar of calendars) {
    select.append(new Option(calendar, calendar));
  }
  if (calendars.includes("Work")) select.value = "Work";
}

function renderSnapshot(snapshot) {
  const rawPayload = snapshot?.payload ?? {};
  if (isFuture()) {
    const plan = rawPayload.daily_plans?.[selectedDate] ?? {
      personal: [],
      work: [],
    };
    snapshotPayload = {
      ...rawPayload,
      agenda: (rawPayload.calendar_plan ?? []).filter(
        (item) => item.start?.slice(0, 10) === selectedDate,
      ),
      personal_tasks: plan.personal,
      work_tasks: plan.work,
      reminders: (rawPayload.reminders ?? []).filter(
        (item) => item.due?.slice(0, 10) === selectedDate,
      ),
    };
  } else {
    snapshotPayload = rawPayload;
  }
  snapshotPayload = {
    ...snapshotPayload,
    reminders: (snapshotPayload.reminders ?? []).filter((item) =>
      item.due
        ? item.due.slice(0, 10) === selectedDate
        : selectedDate === localDate() && !isHistorical(),
    ),
    all_reminders: rawPayload.reminders ?? [],
  };
  const pending = (action, predicate) =>
    pendingCommands.some(
      (command) => command.action === action && predicate(command.payload),
    );
  const updatedTasks = (items, action) =>
    items.flatMap((item) => {
      const area = action === "update-work-task" ? "work" : "personal";
      const entityKey = taskEntityKey(area, item);
      const deleteAction =
        area === "work" ? "delete-work-task" : "delete-personal-task";
      if (
        pendingCommands.some(
          (entry) =>
            entry.action === deleteAction &&
            entry.entity_key === entityKey,
        )
      ) {
        return [];
      }
      const command = pendingCommands.find(
        (entry) =>
          entry.action === action &&
          entry.payload.old_title === item.title &&
          entry.payload.current_date === item.task_date,
      );
      if (!command) return [item];
      if (command.payload.date !== item.task_date) return [];
      return [{ ...item, title: command.payload.title }];
    });
  const withPendingAdds = (items, action) => {
    const result = [...items];
    for (const command of pendingCommands.filter(
      (entry) => entry.action === action,
    )) {
      const exists = result.some(
        (item) =>
          item.title === command.payload.title &&
          item.task_date === command.payload.date,
      );
      if (!exists) {
        result.push({
          title: command.payload.title,
          task_date: command.payload.date,
          parent_path: [],
          line_number: `pending-${command.created_at}`,
          completed: false,
          pending: true,
        });
      }
    }
    return result;
  };
  const personalTasks = updatedTasks(
    withPendingAdds(
      snapshotPayload.personal_tasks ?? [],
      "add-personal-task",
    ),
    "update-personal-task",
  ).map((item) => ({
    ...item,
    completed: pending(
      "reopen-personal-task",
      (payload) =>
        payload.title === item.title && payload.date === item.task_date,
    )
      ? false
      : item.completed ||
        pending(
          "complete-personal-task",
          (payload) =>
            payload.title === item.title && payload.date === item.task_date,
        ),
  }));
  const workTasks = updatedTasks(
    withPendingAdds(snapshotPayload.work_tasks ?? [], "add-work-task"),
    "update-work-task",
  ).map((item) => ({
    ...item,
    completed: pending(
      "reopen-work-task",
      (payload) =>
        payload.title === item.title && payload.date === item.task_date,
    )
      ? false
      : item.completed ||
        pending(
          "complete-work-task",
          (payload) =>
            payload.title === item.title && payload.date === item.task_date,
        ),
  }));
  const remindersWithPending = [...(snapshotPayload.reminders ?? [])];
  for (const command of pendingCommands.filter(
    (entry) => entry.action === "add-reminder",
  )) {
    const pendingDate = command.payload.date ?? "";
    if (
      (pendingDate && pendingDate.slice(0, 10) !== selectedDate) ||
      (!pendingDate && selectedDate !== localDate())
    ) {
      continue;
    }
    if (
      !remindersWithPending.some(
        (item) => {
          const existingDate = pendingDate.includes("T")
            ? item.due?.slice(0, 16)
            : item.due?.slice(0, 10);
          return (
            item.title === command.payload.title &&
            existingDate === pendingDate
          );
        },
      )
    ) {
      remindersWithPending.push({
        id: `pending-${command.created_at}`,
        title: command.payload.title,
        due: command.payload.date,
        completed: false,
        pending: true,
      });
    }
  }
  const reminders = remindersWithPending
    .map((item) => {
      const update = pendingCommands.find(
        (command) =>
          command.action === "update-reminder" &&
          command.payload.id === item.id,
      );
      return {
        ...item,
        title: update?.payload.title ?? item.title,
        due: update?.payload.date ?? item.due,
        completed:
          item.completed ||
          pending(
            "complete-reminder",
            (payload) => payload.id === item.id,
          ),
      };
    })
    .filter((item) =>
      item.due
        ? item.due.slice(0, 10) === selectedDate
        : selectedDate === localDate() && !isHistorical(),
    );
  const learningWithPending = [...(snapshotPayload.learning ?? [])];
  for (const command of pendingCommands.filter(
    (entry) => entry.action === "add-learning",
  )) {
    if (
      !learningWithPending.some(
        (item) =>
          item.title === command.payload.title &&
          item.kind === command.payload.kind,
      )
    ) {
      learningWithPending.push({
        id: `pending-${command.created_at}`,
        title: command.payload.title,
        kind: command.payload.kind,
        url: command.payload.url ?? null,
        pending: true,
      });
    }
  }
  const learning = learningWithPending.filter(
    (item) =>
      !pending(
        "complete-learning",
        (payload) => payload.id === item.id,
      ),
  );
  const agenda = (snapshotPayload.agenda ?? [])
    .map((item) => {
      const update = pendingCommands.find(
        (command) =>
          command.action === "add-calendar-event" &&
          command.payload.operation === "update" &&
          command.payload.uid === item.uid &&
          command.payload.calendar === item.calendar,
      );
      return update
        ? {
            ...item,
            title: update.payload.title,
            start: update.payload.start,
            end: null,
            pending: true,
          }
        : item;
    })
    .filter(
      (item) =>
        !pending(
          "delete-agenda-item",
          (payload) =>
            payload.uid === item.uid && payload.calendar === item.calendar,
        ),
    );
  for (const command of pendingCommands.filter(
    (entry) =>
      entry.action === "add-calendar-event" &&
      entry.payload.operation !== "update" &&
      entry.payload.start?.slice(0, 10) === selectedDate,
  )) {
    if (
      !agenda.some(
        (item) =>
          item.title === command.payload.title &&
          item.calendar === command.payload.calendar &&
          item.start?.slice(0, 16) === command.payload.start,
      )
    ) {
      agenda.push({
        uid: null,
        title: command.payload.title,
        calendar: command.payload.calendar,
        start: command.payload.start,
        end: null,
        all_day: "false",
        kind: "event",
        pending: true,
      });
    }
  }
  agenda.sort((left, right) =>
    String(left.start ?? "").localeCompare(String(right.start ?? "")),
  );
  renderAgenda(agenda);
  renderTasks(
    "#work-tree",
    workTasks,
    "complete-work-task",
  );
  renderTasks(
    "#personal-tasks",
    personalTasks,
    "complete-personal-task",
  );
  renderReminders(reminders);
  renderSystemHealth(snapshotPayload.system_health ?? []);
  renderMail(snapshotPayload.mail ?? []);
  renderLearning(learning);
  renderProjects(snapshotPayload.projects ?? []);
  renderCaptureParents();
  renderCalendars(snapshotPayload.calendars ?? []);
  renderAudit(snapshotPayload.audit ?? []);
  setStatus(
    snapshot
      ? `Ενημερώθηκε ${new Date(snapshot.updated_at).toLocaleString("el-GR")}`
      : "Δεν υπάρχει ακόμη στιγμιότυπο από το Mac.",
  );
}

async function loadSnapshot() {
  const query = isHistorical()
    ? supabase
        .from("command_center_daily_snapshots")
        .select("payload, updated_at")
        .eq("day", selectedDate)
        .maybeSingle()
    : supabase
        .from("command_center_snapshots")
        .select("payload, updated_at")
        .single();
  const { data, error } = await query;
  if (error && error.code !== "PGRST116") throw error;
  return data;
}

async function loadAvailableSnapshots() {
  const { data, error } = await supabase
    .from("command_center_daily_snapshots")
    .select("day")
    .order("day", { ascending: false })
    .limit(365);
  if (error) throw error;
  availableSnapshots = (data ?? []).map((row) => row.day);
}

async function loadPendingCommands() {
  const { data, error } = await supabase
    .from("command_center_commands")
    .select("action,payload,status,entity_key,created_at")
    .in("status", ["pending", "processing"]);
  if (error) throw error;
  return data ?? [];
}

function renderSyncStatus(payload) {
  const summary = $("#sync-summary");
  summary.replaceChildren();
  for (const [label, value] of [
    [
      "Τελευταίο στιγμιότυπο",
      payload.last_snapshot_at
        ? formatGreekDateTime(payload.last_snapshot_at)
        : "Ποτέ",
    ],
    ["Σε αναμονή", String(payload.counts.pending)],
    ["Εκτελούνται", String(payload.counts.processing)],
    ["Απέτυχαν", String(payload.counts.failed)],
  ]) {
    const card = element("div", "sync-stat");
    card.append(
      element("span", "summary-label", label),
      element("strong", "", value),
    );
    summary.append(card);
  }
  const failures = $("#sync-failures");
  failures.replaceChildren();
  for (const failure of payload.failures) {
    failures.append(
      element(
        "div",
        "list-item severity-critical",
        `${failure.action}: ${failure.result?.error ?? "Άγνωστο σφάλμα"}`,
      ),
    );
  }
}

async function loadSyncStatus(snapshot) {
  const { data, error } = await supabase
    .from("command_center_commands")
    .select("action,status,result,created_at")
    .in("status", ["pending", "processing", "failed"])
    .order("created_at", { ascending: false })
    .limit(50);
  if (error) throw error;
  const rows = data ?? [];
  renderSyncStatus({
    last_snapshot_at: snapshot?.updated_at ?? null,
    counts: {
      pending: rows.filter((row) => row.status === "pending").length,
      processing: rows.filter((row) => row.status === "processing").length,
      failed: rows.filter((row) => row.status === "failed").length,
    },
    failures: rows.filter((row) => row.status === "failed").slice(0, 10),
  });
}

function renderAudit(events) {
  const container = $("#audit-timeline");
  container.replaceChildren();
  if (!events.length) {
    empty(container);
    return;
  }
  const actions = {
    added: "Προστέθηκε",
    completed: "Ολοκληρώθηκε",
    rescheduled: "Μετακινήθηκε",
    updated: "Ενημερώθηκε",
    recorded: "Καταγράφηκε",
    reopened: "Επαναφέρθηκε",
    deleted: "Διαγράφηκε",
  };
  for (const event of events) {
    const row = element("div", "audit-row");
    row.append(
      element("span", "audit-time", formatGreekDateTime(event.timestamp)),
      element("span", "audit-source", event.source),
      element(
        "span",
        "audit-title",
        `${actions[event.action] ?? event.action}: ${event.title}`,
      ),
    );
    container.append(row);
  }
}

async function loadHealth() {
  let query = supabase
    .from("command_center_health_daily")
    .select(
      "day,steps,sleep_minutes,active_energy_kcal,resting_heart_rate,updated_at",
    );
  query = selectedDate !== localDate()
    ? query.eq("day", selectedDate).maybeSingle()
    : query.order("day", { ascending: false }).limit(1).maybeSingle();
  const { data, error } = await query;
  renderHealth(error ? null : data);
}

function renderScratchpad(row) {
  $("#scratchpad").value = row?.content ?? "";
  $("#scratchpad-status").textContent = row?.updated_at
    ? `Αποθηκεύτηκε ${formatGreekDateTime(row.updated_at)}`
    : "Δεν έχει αποθηκευτεί";
}

async function loadScratchpad() {
  const { data, error } = await supabase
    .from("command_center_scratchpad")
    .select("content,updated_at")
    .maybeSingle();
  if (error) throw error;
  renderScratchpad(data);
}

async function saveScratchpad() {
  $("#scratchpad-status").textContent = "Αποθήκευση…";
  const content = $("#scratchpad").value;
  const updatedAt = new Date().toISOString();
  const { error } = await supabase
    .from("command_center_scratchpad")
    .upsert(
      {
        user_id: session.user.id,
        content,
        updated_at: updatedAt,
      },
      { onConflict: "user_id" },
    );
  if (error) throw error;
  renderScratchpad({ content, updated_at: updatedAt });
}

function scheduleScratchpadSave() {
  if (isHistorical()) return;
  clearTimeout(scratchpadTimer);
  $("#scratchpad-status").textContent = "Μη αποθηκευμένες αλλαγές";
  scratchpadTimer = setTimeout(() => {
    saveScratchpad().catch((error) => {
      $("#scratchpad-status").textContent = `Αποτυχία: ${error.message}`;
    });
  }, 800);
}

async function clearScratchpad() {
  if (isHistorical()) return;
  if (!window.confirm("Να καθαριστεί ολόκληρο το σημειωματάριο;")) return;
  clearTimeout(scratchpadTimer);
  const { error } = await supabase
    .from("command_center_scratchpad")
    .delete()
    .eq("user_id", session.user.id);
  if (error) throw error;
  renderScratchpad(null);
}

async function enqueue(action, payload, entityKey = null) {
  if (isHistorical()) {
    throw new Error("Οι παλιές ημερομηνίες είναι μόνο για ανάγνωση.");
  }
  const { error } = await supabase
    .from("command_center_commands")
    .insert({ action, payload, entity_key: entityKey });
  if (error) throw error;
  setTimeout(refresh, 65_000);
}

function openEdit(kind, item, entityKey = "") {
  $("#edit-kind").value = kind;
  $("#edit-id").value = item.id ?? "";
  $("#edit-old-title").value = item.title;
  $("#edit-current-date").value =
    item.task_date ?? item.due?.slice(0, 10) ?? "";
  $("#edit-entity-key").value = entityKey;
  $("#edit-title").value = item.title;
  const dateInput = $("#edit-date");
  dateInput.type = kind === "Reminder" ? "datetime-local" : "date";
  dateInput.value =
    item.task_date ??
    (kind === "Reminder"
      ? item.due?.slice(0, 16)
      : item.due?.slice(0, 10)) ??
    (kind === "Reminder" ? `${localDate()}T09:00` : localDate());
  const dialog = $("#edit-dialog");
  if (!dialog.open) dialog.showModal();
  $("#edit-title").focus();
}

async function saveEdit(event) {
  event.preventDefault();
  const button = event.submitter ?? $("#edit-form button[type='submit']");
  button.disabled = true;
  const kind = $("#edit-kind").value;
  const payload = {
    id: $("#edit-id").value,
    old_title: $("#edit-old-title").value,
    current_date: $("#edit-current-date").value,
    title: $("#edit-title").value.trim(),
    date: $("#edit-date").value,
  };
  const action =
    kind === "Reminder"
      ? "update-reminder"
      : kind === "Work"
        ? "update-work-task"
        : "update-personal-task";
  try {
    await enqueue(action, payload, $("#edit-entity-key").value || null);
    $("#edit-dialog").close();
    setStatus("Η ενημέρωση περιμένει συγχρονισμό με το Mac.");
    await refresh();
  } catch (error) {
    setStatus(`Αποτυχία επεξεργασίας: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function deleteTodo(area, item, entityKey, button) {
  if (!window.confirm(`Να διαγραφεί το todo «${item.title}»;`)) return;
  button.disabled = true;
  try {
    await enqueue(
      area === "work" ? "delete-work-task" : "delete-personal-task",
      { title: item.title, date: item.task_date },
      entityKey,
    );
    setStatus("Η διαγραφή περιμένει συγχρονισμό με το Mac.");
    await refresh();
  } catch (error) {
    button.disabled = false;
    setStatus(`Αποτυχία διαγραφής: ${error.message}`);
  }
}

function updateCaptureFields() {
  const kind = selectedCaptureKind();
  const learning = ["book", "article", "video"].includes(kind);
  const todo = ["personal-task", "work-task"].includes(kind);
  const projectNote = kind === "project-note";
  $("#capture-url").classList.toggle("hidden", !learning);
  $("#capture-date").classList.toggle("hidden", learning);
  $("#capture-project").classList.toggle("hidden", !projectNote);
  $("#capture-project").required = projectNote;
  $("#capture-parent").classList.toggle("hidden", !todo);
  renderCaptureParents();
}

async function capture(event) {
  event.preventDefault();
  if (isHistorical()) return;
  const button = event.submitter ?? $("#capture-form button[type='submit']");
  button.disabled = true;
  const kind = selectedCaptureKind();
  const action = {
    "personal-task": "add-personal-task",
    "work-task": "add-work-task",
    reminder: "add-reminder",
    book: "add-learning",
    article: "add-learning",
    video: "add-learning",
    "project-note": "add-project-note",
  }[kind];
  const payload = {
    title: $("#capture-title").value.trim(),
    date: $("#capture-date").value || null,
    parent_line: $("#capture-parent").value
      ? Number($("#capture-parent").value)
      : null,
  };
  if (action === "add-learning") {
    payload.kind = kind;
    const url = $("#capture-url").value.trim();
    if (url) payload.url = url;
  }
  if (action === "add-project-note") {
    payload.project = $("#capture-project").value;
  }
  try {
    await enqueue(action, payload);
    $("#capture-title").value = "";
    $("#capture-url").value = "";
    setStatus("Η καταγραφή περιμένει συγχρονισμό με το Mac.");
    await refresh();
  } catch (error) {
    setStatus(`Αποτυχία: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function addCalendarEvent(event) {
  event.preventDefault();
  if (isHistorical()) return;
  const button = event.submitter ?? $("#event-form button[type='submit']");
  button.disabled = true;
  const title = $("#event-title").value.trim();
  try {
    await enqueue("add-calendar-event", {
      title,
      calendar: $("#event-calendar").value,
      start: $("#event-start").value,
      duration: Number($("#event-duration").value),
    });
    $("#event-title").value = "";
    $("#event-dialog").close();
    setStatus("Το συμβάν περιμένει συγχρονισμό με το Mac.");
  } catch (error) {
    setStatus(`Αποτυχία: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function deleteAgendaItem(item, button) {
  if (!window.confirm(`Να διαγραφεί το «${item.title}» από το Πρόγραμμα;`)) {
    return;
  }
  button.disabled = true;
  try {
    await enqueue("delete-agenda-item", {
      kind: item.kind === "reminder" ? "reminder" : "event",
      calendar: item.calendar,
      uid: item.uid,
      title: item.title,
      ref: item.command_center_ref,
    }, `agenda:${item.kind}:${item.calendar}:${item.uid}`);
    setStatus("Η διαγραφή περιμένει συγχρονισμό με το Mac.");
    await refresh();
  } catch (error) {
    button.disabled = false;
    setStatus(`Αποτυχία διαγραφής: ${error.message}`);
  }
}

async function archiveProjectNote(project, note, button) {
  if (!window.confirm("Να διαγραφεί αυτή η σημείωση έργου;")) return;
  button.disabled = true;
  try {
    await enqueue("archive-project-note", {
      project: project.name,
      id: note.id,
      title: note.text,
    }, `project-note:${project.name}:${note.id}`);
    setStatus("Η διαγραφή περιμένει συγχρονισμό με το Mac.");
    await refresh();
    openProject(project);
  } catch (error) {
    button.disabled = false;
    setStatus(`Αποτυχία διαγραφής: ${error.message}`);
  }
}

function searchableItems() {
  return [
    ...(snapshotPayload.work_tasks ?? []).map((item) => ({
      kind: "work",
      title: item.title,
      context: "Δουλειά",
    })),
    ...(snapshotPayload.personal_tasks ?? []).map((item) => ({
      kind: "task",
      title: item.title,
      context: "Προσωπικά",
    })),
    ...(snapshotPayload.reminders ?? []).map((item) => ({
      kind: "reminder",
      title: item.title,
      context: reminderDue(item.due),
    })),
    ...(snapshotPayload.learning ?? []).map((item) => ({
      kind: item.kind,
      title: item.title,
      context: "Μάθηση",
      url: item.url,
    })),
    ...(snapshotPayload.projects ?? []).map((item) => ({
      kind: "project",
      title: item.name,
      context: item.lifecycle,
    })),
    ...(snapshotPayload.agenda ?? []).map((item) => ({
      kind: "calendar",
      title: item.title,
      context: `${formatTime(item.start)} · ${item.calendar}`,
      url: joinLink(item),
    })),
    ...(snapshotPayload.mail ?? []).map((item) => ({
      kind: "mail",
      title: item.subject,
      context: item.sender,
      url: mailLink(item.message_id),
    })),
  ];
}

function search(event) {
  event.preventDefault();
  const query = $("#search-query").value.trim().toLocaleLowerCase("el");
  const results = searchableItems().filter((item) =>
    `${item.title} ${item.context}`.toLocaleLowerCase("el").includes(query),
  );
  const container = $("#search-results");
  container.replaceChildren();
  if (!results.length) {
    empty(container, "Δεν βρέθηκαν αποτελέσματα.");
    return;
  }
  for (const result of results) {
    const row = element(result.url ? "a" : "article", "search-result");
    if (result.url) {
      row.href = result.url;
      row.target = "_blank";
      row.rel = "noreferrer";
    }
    row.append(
      element("span", "badge", result.kind),
      element("strong", "", result.title),
      element("span", "item-meta", result.context),
    );
    container.append(row);
  }
}

function applyVisibility() {
  $("#personal-panel").classList.toggle(
    "hidden",
    !$("#show-personal").checked,
  );
  $("#work-panel").classList.toggle("hidden", !$("#show-work").checked);
}

function briefingSection(title, items) {
  const section = element("section", "briefing-section");
  section.append(element("h3", "", title));
  const list = element("div", "briefing-items");
  if (!items.length) {
    list.append(element("div", "briefing-item empty", "Κανένα."));
  } else {
    for (const item of items.slice(0, 20)) {
      const title = typeof item === "string" ? item : item.title;
      const depth =
        typeof item === "string" ? 0 : Math.min(item.parent_path?.length ?? 0, 8);
      const row = element("div", "briefing-item", title);
      row.classList.add(`briefing-depth-${depth}`);
      list.append(row);
    }
  }
  section.append(list);
  return section;
}

function maybeShowBriefing() {
  if (selectedDate !== localDate()) return;
  const day = localDate();
  if (localStorage.getItem("command-center-briefing-date") === day) return;
  const content = $("#briefing-content");
  content.replaceChildren(
    briefingSection(
      "Πρόγραμμα",
      (snapshotPayload.agenda ?? []).map(
        (item) => `${formatTime(item.start)} · ${item.title}`,
      ),
    ),
    briefingSection(
      "Δουλειά",
      (snapshotPayload.work_tasks ?? [])
        .filter((item) => !item.completed),
    ),
    briefingSection(
      "Προσωπικά",
      (snapshotPayload.personal_tasks ?? [])
        .filter((item) => !item.completed),
    ),
    briefingSection(
      "Υπενθυμίσεις",
      (snapshotPayload.reminders ?? []).map((item) => item.title),
    ),
  );
  const dialog = $("#briefing-dialog");
  if (!dialog.open) dialog.showModal();
}

async function refresh() {
  if (!session) return;
  setStatus("Ανανέωση…");
  const commands = isHistorical() ? [] : await loadPendingCommands();
  const [snapshot] = await Promise.all([
    loadSnapshot(),
    loadHealth(),
    isHistorical() ? Promise.resolve() : loadScratchpad(),
  ]);
  pendingCommands = commands;
  renderPendingQueue(pendingCommands);
  renderSnapshot(snapshot);
  if (isHistorical()) {
    renderScratchpad(snapshot?.payload?.scratchpad ?? null);
    $("#scratchpad").readOnly = true;
    document.body.classList.add("history-mode");
    $("#history-mode").textContent =
      `Στιγμιότυπο ${formatGreekDateValue(selectedDate)}`;
    setStatus(
      snapshot
        ? `Ιστορικό στιγμιότυπο ${formatGreekDateValue(selectedDate)}`
        : `Δεν υπάρχει στιγμιότυπο για ${formatGreekDateValue(selectedDate)}`,
    );
  } else {
    $("#scratchpad").readOnly = false;
    document.body.classList.remove("history-mode");
    $("#history-mode").textContent = isFuture()
      ? `Προγραμματισμός ${formatGreekDateValue(selectedDate)}`
      : "Ζωντανή προβολή";
    if (isFuture()) {
      setStatus(`Προγραμματισμός για ${formatGreekDateValue(selectedDate)}`);
    }
  }
  await loadSyncStatus(snapshot);
  maybeShowBriefing();
}

async function updateAuth(nextSession) {
  session = nextSession;
  const authorized = session?.user?.id === OWNER_USER_ID;
  if (session && !authorized) {
    $(".shell").classList.add("hidden");
    $("#access-denied").classList.remove("hidden");
    return;
  }
  $(".shell").classList.remove("hidden");
  $("#access-denied").classList.add("hidden");
  $("#app").classList.toggle("hidden", !session);
  $("#capture-form").classList.toggle("hidden", !session);
  $("#open-chat").classList.toggle("hidden", !session);
  if (session) {
    await loadAvailableSnapshots();
    $("#history-date").value = selectedDate;
    await refresh();
  } else {
    showLogin();
  }
}

async function selectHistoryDate(value) {
  selectedDate = value;
  $("#history-date").value = value;
  if (!isHistorical()) {
    $("#capture-date").value = value;
    const start = new Date(`${value}T09:00:00`);
    $("#event-start").value = new Date(
      start.getTime() - start.getTimezoneOffset() * 60_000,
    )
      .toISOString()
      .slice(0, 16);
  }
  await refresh();
}

function shiftHistoryDate(days) {
  const date = new Date(`${selectedDate}T12:00:00`);
  date.setDate(date.getDate() + days);
  selectHistoryDate(localDate(date));
}

function initializeDate() {
  const now = new Date();
  $("#greeting").textContent = "kx";
  $("#today").textContent = new Intl.DateTimeFormat("el-GR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(now);
  $("#capture-date").value = new Date(
    now.getTime() - now.getTimezoneOffset() * 60_000,
  )
    .toISOString()
    .slice(0, 10);
  $("#history-date").value = selectedDate;
  const nextHour = new Date(now);
  nextHour.setMinutes(0, 0, 0);
  nextHour.setHours(nextHour.getHours() + 1);
  $("#event-start").value = new Date(
    nextHour.getTime() - nextHour.getTimezoneOffset() * 60_000,
  )
    .toISOString()
    .slice(0, 16);
}

async function initialize() {
  initializeDate();
  loadChatHistory();
  renderChat();
  applyVisibility();
  if (!configured) {
    setStatus("Λείπουν τα Supabase environment variables.");
    return;
  }
  $("#refresh").addEventListener("click", refresh);
  $("#capture-form").addEventListener("submit", capture);
  $("#capture-kind").addEventListener("change", configureCaptureSubtype);
  $("#capture-subtype").addEventListener("change", updateCaptureFields);
  $("#capture-date").addEventListener("change", renderCaptureParents);
  $("#scratchpad").addEventListener("input", scheduleScratchpadSave);
  $("#clear-scratchpad").addEventListener("click", () => {
    clearScratchpad().catch((error) => {
      $("#scratchpad-status").textContent = `Αποτυχία: ${error.message}`;
    });
  });
  $("#show-personal").addEventListener("change", applyVisibility);
  $("#show-work").addEventListener("change", applyVisibility);
  $("#open-search").addEventListener("click", () => {
    const dialog = $("#search-dialog");
    if (!dialog.open) dialog.showModal();
    $("#search-query").focus();
  });
  $("#close-search").addEventListener("click", () => {
    $("#search-dialog").close();
  });
  $("#search-form").addEventListener("submit", search);
  $("#close-project").addEventListener("click", () => {
    $("#project-dialog").close();
  });
  $("#close-event").addEventListener("click", () => {
    $("#event-dialog").close();
  });
  $("#open-event").addEventListener("click", () => {
    const dialog = $("#event-dialog");
    if (!dialog.open) dialog.showModal();
    $("#event-title").focus();
  });
  $("#event-form").addEventListener("submit", addCalendarEvent);
  $("#edit-form").addEventListener("submit", saveEdit);
  $("#close-edit").addEventListener("click", () => {
    $("#edit-dialog").close();
  });
  $("#close-briefing").addEventListener("click", () => {
    localStorage.setItem(
      "command-center-briefing-date",
      localDate(),
    );
    $("#briefing-dialog").close();
  });
  $("#open-chat").addEventListener("click", () => {
    const dialog = $("#chat-dialog");
    if (!dialog.open) dialog.showModal();
    renderChat();
    $("#chat-input").focus();
  });
  $("#close-chat").addEventListener("click", () => {
    $("#chat-dialog").close();
  });
  $("#clear-chat").addEventListener("click", () => {
    if (!window.confirm("Να καθαριστεί το ιστορικό συνομιλίας;")) return;
    chatMessages = [];
    saveChatHistory();
    renderChat();
  });
  $("#chat-form").addEventListener("submit", sendChatMessage);
  $("#chat-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      $("#chat-form").requestSubmit();
    }
  });
  $("#history-date").addEventListener("change", (event) => {
    selectHistoryDate(event.target.value);
  });
  $("#history-previous").addEventListener("click", () => {
    shiftHistoryDate(-1);
  });
  $("#history-next").addEventListener("click", () => {
    shiftHistoryDate(1);
  });
  $("#history-today").addEventListener("click", () => {
    selectHistoryDate(localDate());
  });
  document.querySelectorAll(".learning-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      learningKind = tab.dataset.kind;
      $("#capture-kind").value = "learning";
      configureCaptureSubtype();
      $("#capture-subtype").value = learningKind;
      updateCaptureFields();
      renderLearning(snapshotPayload.learning ?? []);
    });
  });
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      const dialog = $("#search-dialog");
      if (!dialog.open) dialog.showModal();
      $("#search-query").focus();
    }
  });
  configureCaptureSubtype();
  const { data } = await supabase.auth.getSession();
  await updateAuth(data.session);
  supabase.auth.onAuthStateChange((_event, nextSession) => {
    updateAuth(nextSession);
  });
  setInterval(refresh, 30_000);
}

initialize();
