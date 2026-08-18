import { createClient } from "@supabase/supabase-js";
import "./style.css";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const configured = Boolean(supabaseUrl && supabaseKey);
const supabase = configured ? createClient(supabaseUrl, supabaseKey) : null;
const $ = (selector) => document.querySelector(selector);
const OWNER_USER_ID = "4965a34f-c6b6-45ec-b595-d9f14f7a9294";

let session = null;
let learningKind = "book";
let snapshotPayload = {};
let pendingCommands = [];
let scratchpadTimer = null;

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

function showLogin() {
  const status = $("#status");
  status.replaceChildren(
    element("span", "", "Κάνε GitHub login για να δεις το Command Center. "),
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
    const row = element(
      "label",
      `task-row${item.completed ? " completed" : ""}`,
    );
    const depth = Math.min(item.parent_path?.length ?? 0, 8);
    row.classList.add(`task-depth-${depth}`);
    const checkbox = element("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(item.completed);
    checkbox.disabled = Boolean(item.completed);
    if (!item.completed) {
      checkbox.addEventListener("change", async () => {
        if (!checkbox.checked) return;
        checkbox.disabled = true;
        try {
          await enqueue(action, {
            title: item.title,
            date: item.task_date,
          });
          setStatus("Η ολοκλήρωση περιμένει συγχρονισμό με το Mac.");
        } catch (error) {
          checkbox.checked = false;
          checkbox.disabled = false;
          setStatus(`Αποτυχία: ${error.message}`);
        }
      });
    }
    row.append(checkbox, element("span", "", item.title));
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
      element("div", "agenda-calendar", event.calendar),
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
    container.append(row);
  }
}

function reminderDue(value) {
  if (!value) return "Χωρίς ημερομηνία";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("el-GR", {
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(date);
}

function renderReminders(items) {
  const container = $("#reminders");
  container.replaceChildren();
  if (!items.length) {
    empty(container);
    return;
  }
  for (const item of items) {
    const row = element("label", "reminder-row");
    const checkbox = element("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(item.completed);
    checkbox.disabled = Boolean(item.completed);
    if (item.completed) row.classList.add("completed");
    checkbox.addEventListener("change", async () => {
      if (!checkbox.checked) return;
      checkbox.disabled = true;
      try {
        await enqueue("complete-reminder", { id: item.id });
        setStatus("Η ολοκλήρωση περιμένει συγχρονισμό με το Mac.");
      } catch (error) {
        checkbox.checked = false;
        checkbox.disabled = false;
        setStatus(`Αποτυχία: ${error.message}`);
      }
    });
    const copy = element("div", "reminder-copy");
    copy.append(
      element("span", "", item.title),
      element("span", "item-meta", reminderDue(item.due)),
    );
    row.append(checkbox, copy);
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
    const remove = element("button", "learning-remove", "Αφαίρεση");
    remove.type = "button";
    remove.addEventListener("click", async () => {
      remove.disabled = true;
      try {
        await enqueue("complete-learning", { id: item.id });
        setStatus("Η αφαίρεση περιμένει συγχρονισμό με το Mac.");
      } catch (error) {
        remove.disabled = false;
        setStatus(`Αποτυχία: ${error.message}`);
      }
    });
    row.append(copy, remove);
    container.append(row);
  }
}

function renderProjects(projects) {
  const lifecycleOrder = { live: 0, development: 1, planned: 2 };
  const sorted = [...projects].sort((first, second) => {
    const lifecycle =
      (lifecycleOrder[first.lifecycle] ?? 99) -
      (lifecycleOrder[second.lifecycle] ?? 99);
    return lifecycle || first.name.localeCompare(second.name, "el");
  });
  const container = $("#projects");
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
      element("span", "item-meta", project.lifecycle),
    );
    card.addEventListener("click", () => openProject(project));
    container.append(card);
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
      ["Active", String(metrics.active ?? 0)],
      ["Trials", String(metrics.trialing ?? 0)],
      ["Cancelling", String(metrics.cancelling ?? 0)],
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
}

function renderSnapshot(snapshot) {
  snapshotPayload = snapshot?.payload ?? {};
  const pending = (action, predicate) =>
    pendingCommands.some(
      (command) => command.action === action && predicate(command.payload),
    );
  const personalTasks = (snapshotPayload.personal_tasks ?? []).map((item) => ({
    ...item,
    completed:
      item.completed ||
      pending(
        "complete-personal-task",
        (payload) =>
          payload.title === item.title && payload.date === item.task_date,
      ),
  }));
  const workTasks = (snapshotPayload.work_tasks ?? []).map((item) => ({
    ...item,
    completed:
      item.completed ||
      pending(
        "complete-work-task",
        (payload) =>
          payload.title === item.title && payload.date === item.task_date,
      ),
  }));
  const reminders = (snapshotPayload.reminders ?? []).map((item) => ({
    ...item,
    completed:
      item.completed ||
      pending(
        "complete-reminder",
        (payload) => payload.id === item.id,
      ),
  }));
  const learning = (snapshotPayload.learning ?? []).filter(
    (item) =>
      !pending(
        "complete-learning",
        (payload) => payload.id === item.id,
      ),
  );
  renderAgenda(snapshotPayload.agenda ?? []);
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
  renderCalendars(snapshotPayload.calendars ?? []);
  setStatus(
    snapshot
      ? `Ενημερώθηκε ${new Date(snapshot.updated_at).toLocaleString("el-GR")}`
      : "Δεν υπάρχει ακόμη snapshot από το Mac.",
  );
}

async function loadSnapshot() {
  const { data, error } = await supabase
    .from("command_center_snapshots")
    .select("payload, updated_at")
    .single();
  if (error && error.code !== "PGRST116") throw error;
  return data;
}

async function loadPendingCommands() {
  const { data, error } = await supabase
    .from("command_center_commands")
    .select("action,payload,status")
    .in("status", ["pending", "processing"]);
  if (error) throw error;
  return data ?? [];
}

async function loadHealth() {
  const { data, error } = await supabase
    .from("command_center_health_daily")
    .select(
      "day,steps,sleep_minutes,active_energy_kcal,resting_heart_rate,updated_at",
    )
    .order("day", { ascending: false })
    .limit(1)
    .maybeSingle();
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
  const { error } = await supabase
    .from("command_center_scratchpad")
    .delete()
    .eq("user_id", session.user.id);
  if (error) throw error;
  renderScratchpad(null);
}

async function enqueue(action, payload) {
  const { error } = await supabase
    .from("command_center_commands")
    .insert({ action, payload });
  if (error) throw error;
  setTimeout(refresh, 65_000);
}

function updateCaptureFields() {
  const kind = $("#capture-kind").value;
  const learning = ["book", "article", "video"].includes(kind);
  $("#capture-url").classList.toggle("hidden", !learning);
  $("#capture-date").classList.toggle("hidden", learning);
}

async function capture(event) {
  event.preventDefault();
  const button = event.submitter ?? $("#capture-form button[type='submit']");
  button.disabled = true;
  const kind = $("#capture-kind").value;
  const action =
    kind === "personal-task"
      ? "add-personal-task"
      : kind === "work-task"
        ? "add-work-task"
      : kind === "reminder"
        ? "add-reminder"
        : "add-learning";
  const payload = {
    title: $("#capture-title").value.trim(),
    date: $("#capture-date").value || null,
  };
  if (action === "add-learning") {
    payload.kind = kind;
    const url = $("#capture-url").value.trim();
    if (url) payload.url = url;
  }
  try {
    await enqueue(action, payload);
    $("#capture-title").value = "";
    $("#capture-url").value = "";
    setStatus("Η καταγραφή περιμένει συγχρονισμό με το Mac.");
  } catch (error) {
    setStatus(`Αποτυχία: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function addCalendarEvent(event) {
  event.preventDefault();
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

async function refresh() {
  if (!session) return;
  setStatus("Ανανέωση…");
  const [snapshot, commands] = await Promise.all([
    loadSnapshot(),
    loadPendingCommands(),
    loadHealth(),
    loadScratchpad(),
  ]);
  pendingCommands = commands;
  renderSnapshot(snapshot);
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
  if (session) {
    await refresh();
  } else {
    showLogin();
  }
}

function initializeDate() {
  const now = new Date();
  $("#greeting").textContent = "kx@σήμερα";
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
  applyVisibility();
  if (!configured) {
    setStatus("Λείπουν τα Supabase environment variables.");
    return;
  }
  $("#refresh").addEventListener("click", refresh);
  $("#capture-form").addEventListener("submit", capture);
  $("#capture-kind").addEventListener("change", updateCaptureFields);
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
  document.querySelectorAll(".learning-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      learningKind = tab.dataset.kind;
      $("#capture-kind").value = learningKind;
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
  updateCaptureFields();
  const { data } = await supabase.auth.getSession();
  await updateAuth(data.session);
  supabase.auth.onAuthStateChange((_event, nextSession) => {
    updateAuth(nextSession);
  });
  setInterval(refresh, 30_000);
}

initialize();
