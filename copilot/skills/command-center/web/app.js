const state = {
  tasks: null,
  agenda: null,
  health: null,
  appleHealth: null,
  mail: null,
  learning: null,
  learningKind: "book",
  reminders: null,
  calendars: null,
  projects: null,
  scratchpad: null,
};
let scratchpadTimer = null;

const $ = (selector) => document.querySelector(selector);

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function empty(container, message = "Κανένα.") {
  container.replaceChildren(element("p", "empty", message));
}

function titleOf(item) {
  const value = item?.title ?? item?.item ?? "";
  if (typeof value === "object" && value !== null) {
    return (
      value.title ??
      value.item ??
      value.display_name ??
      value.subject ??
      value.label ??
      value.name ??
      value.project ??
      ""
    );
  }
  return String(value);
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

function joinLink(event) {
  const source = `${event.url ?? ""} ${event.description ?? ""}`;
  return (
    source.match(
      /https:\/\/(?:meet\.google\.com|[^/\s]+\.zoom\.us|teams\.microsoft\.com|teams\.live\.com)\/[^\s<>"]+/i,
    )?.[0] ?? null
  );
}

function mailLink(messageId) {
  if (!messageId) return null;
  const normalized = messageId.startsWith("<")
    ? messageId
    : `<${messageId}>`;
  return `message://${encodeURIComponent(normalized)}`;
}

function setStatus(message, error = false) {
  const status = $("#status");
  status.textContent = message;
  status.classList.toggle("error", error);
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
    const time = element(
      "span",
      "agenda-time",
      event.all_day === "true" ? "Όλη μέρα" : formatTime(event.start),
    );
    const copy = element("div", "agenda-copy");
    copy.append(
      element("div", "agenda-title", event.title),
      element("div", "agenda-calendar", event.calendar),
    );
    row.append(time, copy);
    const link = joinLink(event);
    if (link) {
      const anchor = element("a", "meet-link", "Σύνδεση");
      anchor.href = link;
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      row.append(anchor);
    }
    container.append(row);
  }
}

function renderTaskTree(selector, items, area) {
  const container = $(selector);
  container.replaceChildren();
  if (!items.length) {
    empty(container);
    return;
  }
  const seen = new Set();
  for (const item of items) {
    const path = [...(item.parent_path ?? []), item.title];
    const key = path.map((part) => part.toLocaleLowerCase("el")).join("\0");
    if (seen.has(key)) continue;
    seen.add(key);
    const row = element("label", "task-row");
    const checkbox = element("input");
    checkbox.type = "checkbox";
    checkbox.checked = item.completed;
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        completeTask(area, item, checkbox, row);
      } else {
        reopenTask(area, item, checkbox, row);
      }
    });
    if (item.completed) {
      row.classList.add("completed");
    }
    row.append(checkbox, element("span", "", item.title));
    if (!item.completed) {
      const edit = element("button", "task-edit", "Επεξεργασία");
      edit.type = "button";
      edit.addEventListener("click", (event) => {
        event.preventDefault();
        openEdit(area, item);
      });
      row.append(edit);
    }
    const depth = Math.min(item.parent_path?.length ?? 0, 8);
    row.classList.add(`task-depth-${depth}`);
    container.append(row);
  }
}

function renderSimpleList(selector, items, formatter = titleOf) {
  const container = $(selector);
  container.replaceChildren();
  if (!items.length) {
    empty(container);
    return;
  }
  for (const item of items) {
    container.append(element("div", "list-item", formatter(item)));
  }
}

function renderHealth(checks) {
  const container = $("#health");
  container.replaceChildren();
  if (!checks?.length) {
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

function renderAppleHealth(rows) {
  const container = $("#apple-health");
  container.replaceChildren();
  const row = rows?.[0];
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
    const card = element("div", "health-metric");
    card.append(
      element("span", "summary-label", label),
      element("strong", "", value),
    );
    container.append(card);
  }
}

function renderSyncStatus(payload) {
  const summary = $("#sync-summary");
  summary.replaceChildren();
  for (const [label, value] of [
    [
      "Τελευταίο snapshot",
      payload.last_snapshot_at
        ? formatGreekDateTime(payload.last_snapshot_at)
        : "Ποτέ",
    ],
    ["Σε αναμονή", String(payload.counts?.pending ?? 0)],
    ["Εκτελούνται", String(payload.counts?.processing ?? 0)],
    ["Απέτυχαν", String(payload.counts?.failed ?? 0)],
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
  for (const failure of payload.failures ?? []) {
    failures.append(
      element(
        "div",
        "list-item severity-critical",
        `${failure.action}: ${failure.result?.error ?? "Άγνωστο σφάλμα"}`,
      ),
    );
  }
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

function reminderDue(value) {
  if (!value) return "Χωρίς ημερομηνία";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return value;
  return new Intl.DateTimeFormat("el-GR", {
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(parsed);
}

function renderReminders(reminders) {
  const container = $("#reminders");
  container.replaceChildren();
  if (!reminders.length) {
    empty(container);
    return;
  }
  for (const reminder of reminders) {
    const row = element("label", "reminder-row");
    const checkbox = element("input");
    checkbox.type = "checkbox";
    const copy = element("div", "reminder-copy");
    copy.append(
      element("span", "", reminder.title),
      element(
        "span",
        "item-meta",
        `${reminderDue(reminder.due)}${reminder.managed_task ? " · Συγχρονισμένη εργασία" : ""}`,
      ),
    );
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) completeReminder(reminder, checkbox, row);
    });
    row.append(checkbox, copy);
    const edit = element("button", "reminder-edit", "Επεξεργασία");
    edit.type = "button";
    edit.addEventListener("click", (event) => {
      event.preventDefault();
      openEdit("Reminder", reminder);
    });
    row.append(edit);
    container.append(row);
  }
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
    if (message.read === "false") card.classList.add("mail-unread");
    if (target) {
      card.href = target;
      card.title = "Άνοιγμα στο Apple Mail";
    }
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

function renderLearning(items) {
  const container = $("#learning");
  container.replaceChildren();
  const normalizedKind = (kind) =>
    kind === "resource" || kind === "course" ? "article" : kind;
  const filtered = items.filter(
    (item) => normalizedKind(item.kind) === state.learningKind,
  );
  document.querySelectorAll(".learning-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.kind === state.learningKind);
  });
  if (!filtered.length) {
    empty(container);
    return;
  }
  for (const item of filtered) {
    const row = element("article", "learning-row");
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
    if (item.project) {
      copy.append(element("p", "item-meta", item.project));
    }
    const remove = element("button", "learning-remove", "Αφαίρεση");
    remove.type = "button";
    remove.addEventListener("click", () => {
      completeLearning(item, remove, row);
    });
    row.append(copy, remove);
    container.append(row);
  }
}

function renderProjects(projects) {
  const container = $("#projects");
  container.replaceChildren();
  const lifecycleOrder = {
    live: 0,
    development: 1,
    developing: 1,
    planned: 2,
  };
  const active = projects
    .filter((project) => project.status === "active")
    .sort((first, second) => {
      const lifecycle =
        (lifecycleOrder[first.lifecycle] ?? 99) -
        (lifecycleOrder[second.lifecycle] ?? 99);
      return lifecycle || first.name.localeCompare(second.name, "el");
    });
  const projectSelect = $("#capture-project");
  const selectedProject = projectSelect.value;
  projectSelect.replaceChildren(
    new Option("Χωρίς project", ""),
    ...active.map((project) => new Option(project.name, project.name)),
  );
  if ([...projectSelect.options].some((option) => option.value === selectedProject)) {
    projectSelect.value = selectedProject;
  }
  if (!active.length) {
    empty(container);
    return;
  }
  for (const project of active) {
    const card = element("button", "project-card");
    card.type = "button";
    card.append(
      element("strong", "", project.name),
      element(
        "span",
        "item-meta",
        `${project.lifecycle ?? "active"} · ${project.area ?? "personal"}`,
      ),
    );
    card.addEventListener("click", () => openProject(project.name));
    container.append(card);
  }
}

function renderTasks() {
  if (!state.tasks) return;
  renderTaskTree("#work-tree", state.tasks.work ?? [], "Work");
  renderTaskTree("#personal-tasks", state.tasks.personal ?? [], "Personal");
  renderCaptureParents();
  applyVisibility();
}

function renderCaptureParents() {
  const select = $("#capture-parent");
  const selected = select.value;
  select.replaceChildren(new Option("Νέο parent", ""));
  const kind = $("#capture-kind").value;
  const now = new Date();
  const today = new Date(
    now.getTime() - now.getTimezoneOffset() * 60_000,
  )
    .toISOString()
    .slice(0, 10);
  if (
    !["personal-task", "work-task"].includes(kind) ||
    $("#capture-date").value !== today
  ) {
    return;
  }
  const items =
    kind === "work-task"
      ? state.tasks?.work ?? []
      : state.tasks?.personal ?? [];
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

function renderProjectDetail(payload) {
  const project = payload.project;
  $("#project-title").textContent = project.name;
  const detail = $("#project-detail");
  detail.replaceChildren();

  const health = element("div", "list");
  if (payload.health?.length) {
    for (const check of payload.health) {
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
  if (payload.tasks?.length) {
    for (const task of payload.tasks) {
      tasks.append(element("div", "list-item", task.title));
    }
  } else {
    empty(tasks, "Δεν υπάρχουν ανοιχτά tasks.");
  }
  detail.append(detailSection("Εργασίες", tasks));

  const github = payload.github ?? {};
  const githubStats = element("div", "detail-stats");
  githubStats.append(
    element(
      "div",
      "list-item",
      `Ανοιχτά PRs: ${github.authored_open?.length ?? 0}`,
    ),
    element(
      "div",
      "list-item",
      `Αιτήματα review: ${github.review_requested?.length ?? 0}`,
    ),
    element(
      "div",
      "list-item",
      `Αποτυχημένο CI: ${github.failing_ci?.length ?? 0}`,
    ),
  );
  detail.append(detailSection("GitHub", githubStats));

}

function renderBookItBusiness(business, emailPayload) {
  const detail = $("#project-detail");
  if (business) {
    const metrics = business.metrics ?? {};
    const currency = String(metrics.currency ?? "EUR").toUpperCase();
    const money = new Intl.NumberFormat("el-GR", {
      style: "currency",
      currency,
    });
    const stats = element("div", "business-grid");
    const values = [
      ["MRR", money.format((metrics.mrr_cents ?? 0) / 100)],
      ["Active", String(metrics.active ?? 0)],
      ["Trials", String(metrics.trialing ?? 0)],
      ["Cancelling", String(metrics.cancelling ?? 0)],
    ];
    for (const [label, value] of values) {
      const card = element("div", "business-stat");
      card.append(
        element("span", "summary-label", label),
        element("strong", "", value),
      );
      stats.append(card);
    }
    detail.prepend(detailSection("BookIt οικονομικά", stats));

    const upcoming = element("div", "list");
    const rows = [
      ...(business.attention ?? []).map((item) => ({
        ...item,
        state: "Attention",
      })),
      ...(business.cancelling ?? []).map((item) => ({
        ...item,
        state: "Cancelling",
      })),
      ...(business.renewing_soon ?? []).map((item) => ({
        ...item,
        state: "Renewal",
      })),
    ];
    if (rows.length) {
      for (const row of rows) {
        upcoming.append(
          element(
            "div",
            "list-item",
            `${row.state} · ${row.display_name ?? "Unknown"} · ${
              formatGreekDateTime(row.next_billing_at ?? row.ends_at)
            }`,
          ),
        );
      }
    } else {
      empty(upcoming, "Δεν υπάρχουν billing exceptions.");
    }
    detail.insertBefore(
      detailSection("Χρεώσεις και ανανεώσεις", upcoming),
      detail.children[1] ?? null,
    );
  }

  if (emailPayload) {
    const emails = element("div", "list");
    for (const message of emailPayload.emails ?? []) {
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
    if (!(emailPayload.emails ?? []).length) {
      empty(emails);
    }
    detail.append(detailSection("Πρόσφατα email BookIt", emails));
  }
}

async function openProject(name) {
  const dialog = $("#project-dialog");
  $("#project-title").textContent = name;
  $("#project-detail").replaceChildren(
    element("p", "empty", "Φόρτωση project…"),
  );
  if (!dialog.open) dialog.showModal();
  try {
    const project = await fetchJSON(
      `/api/project?name=${encodeURIComponent(name)}`,
    );
    renderProjectDetail(project);
    if (name === "BookIt") {
      const [business, emails] = await Promise.allSettled([
        fetchJSON("/api/project/business?name=BookIt"),
        fetchJSON("/api/project/emails?name=BookIt"),
      ]);
      renderBookItBusiness(
        business.status === "fulfilled" ? business.value : null,
        emails.status === "fulfilled" ? emails.value : null,
      );
    }
  } catch (error) {
    $("#project-detail").replaceChildren(
      element("p", "empty", `Αποτυχία φόρτωσης: ${error.message}`),
    );
  }
}

function renderSearchResults(results) {
  const container = $("#search-results");
  container.replaceChildren();
  if (!results.length) {
    empty(container, "Δεν βρέθηκαν αποτελέσματα.");
    return;
  }
  for (const result of results) {
    let row;
    if (result.kind === "project") {
      row = element("button", "search-result");
      row.type = "button";
      row.addEventListener("click", () => {
        $("#search-dialog").close();
        openProject(result.title);
      });
    } else if (result.url) {
      row = element("a", "search-result");
      row.href = result.url;
      row.target = "_blank";
      row.rel = "noreferrer";
    } else {
      row = element("article", "search-result");
    }
    row.append(
      element("span", "badge", result.kind),
      element("strong", "", result.title),
      element(
        "span",
        "item-meta",
        result.context || result.path || "",
      ),
    );
    container.append(row);
  }
}

async function searchAll(event) {
  event.preventDefault();
  const query = $("#search-query").value.trim();
  const results = $("#search-results");
  results.replaceChildren(element("p", "empty", "Αναζήτηση…"));
  try {
    const payload = await fetchJSON(
      `/api/search?q=${encodeURIComponent(query)}`,
    );
    renderSearchResults(payload.results ?? []);
  } catch (error) {
    results.replaceChildren(
      element("p", "empty", `Αποτυχία αναζήτησης: ${error.message}`),
    );
  }
}

function openSearch() {
  const dialog = $("#search-dialog");
  if (!dialog.open) dialog.showModal();
  $("#search-query").focus();
}

function applyVisibility() {
  $("#personal-panel").classList.toggle("hidden", !$("#show-personal").checked);
  $("#work-panel").classList.toggle("hidden", !$("#show-work").checked);
  localStorage.setItem(
    "command-center-visibility",
    JSON.stringify({
      personal: $("#show-personal").checked,
      work: $("#show-work").checked,
    }),
  );
}

async function fetchJSON(path) {
  const response = await fetch(path, { cache: "no-store" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error ?? `HTTP ${response.status}`);
  return payload;
}

async function mutate(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-Command-Center": "1",
    },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error ?? `HTTP ${response.status}`);
  return result;
}

function openEdit(kind, item) {
  $("#edit-kind").value = kind;
  $("#edit-id").value = item.id ?? "";
  $("#edit-old-title").value = item.title;
  $("#edit-current-date").value =
    item.task_date ?? item.due?.slice(0, 10) ?? "";
  $("#edit-title").value = item.title;
  $("#edit-date").value =
    item.task_date ??
    item.due?.slice(0, 10) ??
    new Date().toISOString().slice(0, 10);
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
    area: kind,
  };
  try {
    if (kind === "Reminder") {
      await mutate("/api/reminder/update", payload);
      await refreshReminders();
    } else {
      await mutate("/api/task/update", payload);
      await refreshTasks();
    }
    $("#edit-dialog").close();
    setStatus(`Ενημερώθηκε: ${payload.title}`);
  } catch (error) {
    setStatus(`Αποτυχία επεξεργασίας: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

async function refreshTasks() {
  const payload = await fetchJSON("/api/tasks");
  state.tasks = payload;
  renderTasks();
}

async function refreshLearning() {
  const payload = await fetchJSON("/api/learning");
  state.learning = payload;
  renderLearning(payload.items ?? []);
}

function renderScratchpad(payload) {
  state.scratchpad = payload;
  $("#scratchpad").value = payload.content ?? "";
  $("#scratchpad-status").textContent = payload.updated_at
    ? `Αποθηκεύτηκε ${formatGreekDateTime(payload.updated_at)}`
    : "Δεν έχει αποθηκευτεί";
}

async function loadScratchpad() {
  renderScratchpad(await fetchJSON("/api/scratchpad"));
}

async function saveScratchpad() {
  $("#scratchpad-status").textContent = "Αποθήκευση…";
  const payload = await mutate("/api/scratchpad", {
    action: "save",
    content: $("#scratchpad").value,
  });
  renderScratchpad(payload);
}

function scheduleScratchpadSave() {
  clearTimeout(scratchpadTimer);
  $("#scratchpad-status").textContent = "Μη αποθηκευμένες αλλαγές";
  scratchpadTimer = setTimeout(() => {
    saveScratchpad().catch((error) => {
      $("#scratchpad-status").textContent = `Αποτυχία: ${error.message}`;
    });
  }, 800);
}

async function clearScratchpad() {
  if (!window.confirm("Να καθαριστεί ολόκληρο το σημειωματάριο;")) return;
  clearTimeout(scratchpadTimer);
  renderScratchpad(
    await mutate("/api/scratchpad", { action: "clear" }),
  );
}

async function refreshReminders() {
  const payload = await fetchJSON("/api/reminders");
  state.reminders = payload;
  renderReminders(payload.reminders ?? []);
}

async function refreshAgenda() {
  const payload = await fetchJSON("/api/agenda");
  state.agenda = payload;
  renderAgenda(
    (payload.events ?? []).filter((event) => event.kind !== "reminder"),
  );
}

function renderCalendars(calendars) {
  const select = $("#event-calendar");
  select.replaceChildren(new Option("Επίλεξε calendar", "", true, true));
  select.options[0].disabled = true;
  for (const calendar of calendars) {
    select.append(new Option(calendar, calendar));
  }
}

async function completeTask(area, item, checkbox, row) {
  checkbox.disabled = true;
  row.classList.add("pending");
  setStatus(`Ολοκλήρωση: ${item.title}…`);
  try {
    await mutate("/api/task/complete", {
      title: item.title,
      area,
      date: item.task_date,
    });
    await refreshTasks();
    setStatus(`Ολοκληρώθηκε: ${item.title}`);
  } catch (error) {
    checkbox.checked = false;
    checkbox.disabled = false;
    row.classList.remove("pending");
    setStatus(`Αποτυχία ολοκλήρωσης: ${error.message}`, true);
  }
}

async function reopenTask(area, item, checkbox, row) {
  checkbox.disabled = true;
  row.classList.add("pending");
  setStatus(`Επαναφορά: ${item.title}…`);
  try {
    await mutate("/api/task/reopen", {
      title: item.title,
      area,
      date: item.task_date,
    });
    await refreshTasks();
    setStatus(`Επαναφέρθηκε: ${item.title}`);
  } catch (error) {
    checkbox.checked = true;
    checkbox.disabled = false;
    row.classList.remove("pending");
    setStatus(`Αποτυχία επαναφοράς: ${error.message}`, true);
  }
}

async function completeLearning(item, button, row) {
  button.disabled = true;
  row.classList.add("pending");
  setStatus(`Ολοκλήρωση μάθησης: ${item.title}…`);
  try {
    await mutate("/api/learning/complete", { id: item.id });
    await refreshLearning();
    setStatus(`Ολοκληρώθηκε: ${item.title}`);
  } catch (error) {
    button.disabled = false;
    row.classList.remove("pending");
    setStatus(`Αποτυχία μάθησης: ${error.message}`, true);
  }
}

async function completeReminder(reminder, checkbox, row) {
  checkbox.disabled = true;
  row.classList.add("pending");
  setStatus(`Ολοκλήρωση υπενθύμισης: ${reminder.title}…`);
  try {
    await mutate("/api/reminder/complete", { id: reminder.id });
    await Promise.all([refreshReminders(), refreshTasks()]);
    setStatus(`Ολοκληρώθηκε: ${reminder.title}`);
  } catch (error) {
    checkbox.checked = false;
    checkbox.disabled = false;
    row.classList.remove("pending");
    setStatus(`Αποτυχία υπενθύμισης: ${error.message}`, true);
  }
}

function updateCaptureFields() {
  const kind = $("#capture-kind").value;
  const dated = new Set(["personal-task", "work-task", "reminder"]).has(kind);
  const learning = new Set(["book", "article", "video"]).has(kind);
  const projectAware = learning || kind === "project-note";
  const todo = ["personal-task", "work-task"].includes(kind);
  $("#capture-date").classList.toggle("hidden", !dated);
  $("#capture-url").classList.toggle("hidden", !learning);
  $("#capture-project").classList.toggle("hidden", !projectAware);
  $("#capture-project").required = kind === "project-note";
  $("#capture-parent").classList.toggle("hidden", !todo);
  renderCaptureParents();
}

async function addCapture(event) {
  event.preventDefault();
  const button = event.submitter ?? $("#capture-form button[type='submit']");
  button.disabled = true;
  const title = $("#capture-title").value.trim();
  const kind = $("#capture-kind").value;
  const captureDate = $("#capture-date").value;
  const url = $("#capture-url").value.trim();
  const project = $("#capture-project").value;
  const parentLine = $("#capture-parent").value;
  setStatus("Καταγραφή…");
  try {
    await mutate("/api/capture", {
      title,
      kind,
      date: captureDate,
      url,
      project,
      parent_line: parentLine ? Number(parentLine) : null,
    });
    $("#capture-title").value = "";
    $("#capture-url").value = "";
    if (kind === "personal-task" || kind === "work-task") {
      await refreshTasks();
    } else if (kind === "reminder") {
      await refreshReminders();
    } else if (new Set(["book", "article", "video"]).has(kind)) {
      state.learningKind = kind;
      await refreshLearning();
    }
    setStatus(`Καταγράφηκε: ${title}`);
  } catch (error) {
    setStatus(`Αποτυχία καταγραφής: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

async function addCalendarEvent(event) {
  event.preventDefault();
  const button = event.submitter ?? $("#event-form button[type='submit']");
  button.disabled = true;
  const title = $("#event-title").value.trim();
  setStatus(`Δημιουργία συμβάντος: ${title}…`);
  try {
    await mutate("/api/calendar/add", {
      title,
      calendar: $("#event-calendar").value,
      start: $("#event-start").value,
      duration: Number($("#event-duration").value),
    });
    $("#event-title").value = "";
    $("#event-dialog").close();
    await refreshAgenda();
    setStatus(`Δημιουργήθηκε συμβάν: ${title}`);
  } catch (error) {
    setStatus(`Αποτυχία συμβάντος: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

async function loadSyncStatus() {
  renderSyncStatus(await fetchJSON("/api/sync-status"));
}

async function loadAudit() {
  const payload = await fetchJSON("/api/audit");
  renderAudit(payload.events ?? []);
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
  const now = new Date();
  const day = new Date(
    now.getTime() - now.getTimezoneOffset() * 60_000,
  )
    .toISOString()
    .slice(0, 10);
  if (localStorage.getItem("command-center-briefing-date") === day) return;
  const content = $("#briefing-content");
  content.replaceChildren(
    briefingSection(
      "Πρόγραμμα",
      (state.agenda?.events ?? []).map(
        (item) => `${formatTime(item.start)} · ${item.title}`,
      ),
    ),
    briefingSection(
      "Δουλειά",
      (state.tasks?.work ?? [])
        .filter((item) => !item.completed),
    ),
    briefingSection(
      "Προσωπικά",
      (state.tasks?.personal ?? [])
        .filter((item) => !item.completed),
    ),
    briefingSection(
      "Υπενθυμίσεις",
      (state.reminders?.reminders ?? []).map((item) => item.title),
    ),
  );
  const dialog = $("#briefing-dialog");
  if (!dialog.open) dialog.showModal();
}

async function refresh() {
  setStatus("Φόρτωση ζωντανών δεδομένων…");
  $("#refresh").disabled = true;
  const requests = [
    refreshTasks(),
    fetchJSON("/api/projects").then((payload) => {
      state.projects = payload;
      renderProjects(payload.projects ?? payload);
    }),
    refreshAgenda(),
    fetchJSON("/api/calendars").then((payload) => {
      state.calendars = payload;
      renderCalendars(payload.calendars ?? []);
    }),
    fetchJSON("/api/health").then((payload) => {
      state.health = payload;
      renderHealth(payload.checks ?? []);
    }),
    fetchJSON("/api/apple-health").then((payload) => {
      state.appleHealth = payload;
      renderAppleHealth(payload.rows ?? []);
    }),
    fetchJSON("/api/mail").then((payload) => {
      state.mail = payload;
      renderMail(payload.messages ?? []);
    }),
    refreshLearning(),
    refreshReminders(),
    loadScratchpad(),
    loadSyncStatus(),
    loadAudit(),
  ];
  const results = await Promise.allSettled(requests);
  const failures = results.filter((result) => result.status === "rejected");
  setStatus(
    failures.length
      ? `${failures.length} πηγές απέτυχαν να φορτώσουν.`
      : `Ενημερώθηκε ${new Intl.DateTimeFormat("el-GR", {
          hour: "2-digit",
          minute: "2-digit",
        }).format(new Date())}`,
    failures.length > 0,
  );
  $("#refresh").disabled = false;
  maybeShowBriefing();
}

function initialize() {
  const now = new Date();
  $("#greeting").textContent = "kx@σήμερα";
  $("#today").textContent = new Intl.DateTimeFormat("el-GR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(now);

  try {
    const visibility = JSON.parse(
      localStorage.getItem("command-center-visibility") ?? "{}",
    );
    if (typeof visibility.personal === "boolean") {
      $("#show-personal").checked = visibility.personal;
    }
    if (typeof visibility.work === "boolean") {
      $("#show-work").checked = visibility.work;
    }
  } catch {
    localStorage.removeItem("command-center-visibility");
  }

  $("#refresh").addEventListener("click", refresh);
  $("#open-search").addEventListener("click", openSearch);
  $("#search-form").addEventListener("submit", searchAll);
  $("#close-search").addEventListener("click", () => {
    $("#search-dialog").close();
  });
  $("#open-event").addEventListener("click", () => {
    const dialog = $("#event-dialog");
    if (!dialog.open) dialog.showModal();
    $("#event-title").focus();
  });
  $("#close-event").addEventListener("click", () => {
    $("#event-dialog").close();
  });
  $("#event-form").addEventListener("submit", addCalendarEvent);
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openSearch();
    }
  });
  $("#capture-form").addEventListener("submit", addCapture);
  $("#edit-form").addEventListener("submit", saveEdit);
  $("#close-edit").addEventListener("click", () => {
    $("#edit-dialog").close();
  });
  $("#close-briefing").addEventListener("click", () => {
    localStorage.setItem(
      "command-center-briefing-date",
      new Date(
        Date.now() - new Date().getTimezoneOffset() * 60_000,
      )
        .toISOString()
        .slice(0, 10),
    );
    $("#briefing-dialog").close();
  });
  $("#scratchpad").addEventListener("input", scheduleScratchpadSave);
  $("#clear-scratchpad").addEventListener("click", clearScratchpad);
  $("#capture-kind").addEventListener("change", updateCaptureFields);
  $("#capture-date").addEventListener("change", renderCaptureParents);
  document.querySelectorAll(".learning-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      state.learningKind = tab.dataset.kind;
      $("#capture-kind").value = state.learningKind;
      updateCaptureFields();
      renderLearning(state.learning?.items ?? []);
    });
  });
  $("#close-project").addEventListener("click", () => {
    $("#project-dialog").close();
  });
  $("#show-personal").addEventListener("change", applyVisibility);
  $("#show-work").addEventListener("change", applyVisibility);
  $("#capture-date").value = new Date(
    now.getTime() - now.getTimezoneOffset() * 60_000,
  )
    .toISOString()
    .slice(0, 10);
  const nextHour = new Date(now);
  nextHour.setMinutes(0, 0, 0);
  nextHour.setHours(nextHour.getHours() + 1);
  $("#event-start").value = new Date(
    nextHour.getTime() - nextHour.getTimezoneOffset() * 60_000,
  )
    .toISOString()
    .slice(0, 16);
  updateCaptureFields();
  applyVisibility();
  refresh();
}

initialize();
