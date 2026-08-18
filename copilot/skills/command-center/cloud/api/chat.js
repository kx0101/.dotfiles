import { z } from "zod";
import { parseChat } from "../lib/chat-parser.js";

const OWNER_USER_ID = "4965a34f-c6b6-45ec-b595-d9f14f7a9294";

const dateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/);

const strictDateSchema = dateSchema.refine((value) => {
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.valueOf()) && date.toISOString().slice(0, 10) === value;
});

const proposalSchema = z.discriminatedUnion("action", [
  z.object({
    action: z.literal("add-personal-task"),
    payload: z.object({
      title: z.string().min(1).max(300),
      date: strictDateSchema.nullable(),
      parent_line: z.number().int().positive().nullable(),
    }),
  }),
  z.object({
    action: z.literal("add-work-task"),
    payload: z.object({
      title: z.string().min(1).max(300),
      date: strictDateSchema,
      parent_line: z.number().int().positive().nullable(),
    }),
  }),
  z.object({
    action: z.literal("add-reminder"),
    payload: z.object({
      title: z.string().min(1).max(300),
      date: strictDateSchema.nullable(),
    }),
  }),
  z.object({
    action: z.literal("add-learning"),
    payload: z.object({
      title: z.string().min(1).max(300),
      kind: z.enum(["book", "article", "video"]),
      url: z.string().url().nullable(),
    }),
  }),
  z.object({
    action: z.literal("add-project-note"),
    payload: z.object({
      title: z.string().min(1).max(1000),
      project: z.string().min(1).max(100),
    }),
  }),
  z.object({
    action: z.literal("add-calendar-event"),
    payload: z.object({
      title: z.string().min(1).max(300),
      calendar: z.string().min(1).max(200),
      start: z
        .string()
        .regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/),
      duration: z.number().int().min(5).max(480),
    }),
  }),
]);

function json(response, status, payload) {
  response.setHeader("Cache-Control", "no-store");
  response.setHeader("X-Content-Type-Options", "nosniff");
  return response.status(status).json(payload);
}

async function authenticatedUser(request) {
  const authorization = request.headers.authorization ?? "";
  if (!authorization.startsWith("Bearer ")) return null;
  const response = await fetch(
    `${process.env.VITE_SUPABASE_URL}/auth/v1/user`,
    {
      headers: {
        apikey: process.env.VITE_SUPABASE_ANON_KEY,
        Authorization: authorization,
      },
    },
  );
  if (!response.ok) return null;
  return response.json();
}

function athensNow() {
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Europe/Athens",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date());
}

function boundedStrings(value, limit, maxLength) {
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (item) =>
        typeof item === "string" &&
        item.trim().length > 0 &&
        item.length <= maxLength,
    )
    .slice(0, limit)
    .map((item) => item.trim());
}

function boundedParents(value) {
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (item) =>
        item &&
        ["personal", "work"].includes(item.area) &&
        typeof item.title === "string" &&
        item.title.trim().length > 0 &&
        item.title.length <= 300 &&
        Number.isInteger(item.parent_line) &&
        item.parent_line > 0 &&
        strictDateSchema.safeParse(item.date).success,
    )
    .slice(0, 100)
    .map((item) => ({
      area: item.area,
      title: item.title.trim(),
      parent_line: item.parent_line,
      date: item.date,
    }));
}

function hasValidReference(draft, calendars, projects, parents) {
  if (
    draft.action === "add-calendar-event" &&
    !calendars.includes(draft.calendar)
  ) {
    return false;
  }
  if (
    draft.action === "add-project-note" &&
    !projects.includes(draft.project)
  ) {
    return false;
  }
  if (
    ["add-personal-task", "add-work-task"].includes(draft.action) &&
    draft.parent_line !== null
  ) {
    const area = draft.action === "add-work-task" ? "work" : "personal";
    return parents.some(
      (parent) =>
        parent.area === area &&
        parent.parent_line === draft.parent_line &&
        parent.date === draft.date,
    );
  }
  return true;
}

export default async function handler(request, response) {
  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    return json(response, 405, { error: "Επιτρέπεται μόνο POST." });
  }
  const origin = request.headers.origin;
  const allowedOrigins = new Set([
    "https://command-center-mobile-kappa.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
  ]);
  if (process.env.VERCEL_URL) {
    allowedOrigins.add(`https://${process.env.VERCEL_URL}`);
  }
  if (!origin || !allowedOrigins.has(origin)) {
    return json(response, 403, { error: "Μη επιτρεπτή προέλευση." });
  }

  const user = await authenticatedUser(request);
  if (!user || user.id !== OWNER_USER_ID) {
    return json(response, 403, { error: "Απαγορεύεται η πρόσβαση." });
  }

  const body = request.body;
  if (!body || typeof body !== "object") {
    return json(response, 400, { error: "Μη έγκυρο JSON." });
  }
  if (JSON.stringify(body).length > 30_000) {
    return json(response, 413, { error: "Το αίτημα είναι πολύ μεγάλο." });
  }

  const messages = Array.isArray(body.messages)
    ? body.messages
        .slice(-12)
        .filter(
          (message) =>
            ["user", "assistant"].includes(message?.role) &&
            typeof message?.content === "string" &&
            message.content.length <= 2000,
        )
        .map(({ role, content }) => ({ role, content: content.trim() }))
        .filter(({ content }) => content)
    : [];
  if (!messages.length || messages.at(-1).role !== "user") {
    return json(response, 400, { error: "Απαιτείται μήνυμα χρήστη." });
  }

  const calendars = boundedStrings(body.context?.calendars, 50, 200);
  const projects = boundedStrings(body.context?.projects, 50, 100);
  const parents = boundedParents(body.context?.parents);
  try {
    const result = parseChat({
      message: messages.at(-1).content,
      draft: body.draft,
      context: {
        today: athensNow().slice(0, 10),
        selectedDate: strictDateSchema.safeParse(
          body.context?.selected_date,
        ).success
          ? body.context.selected_date
          : null,
        calendars,
        projects,
        parents,
      },
    });
    let { reply, draft } = result;
    let proposal = null;
    if (result.proposal) {
      const parsed = proposalSchema.safeParse(result.proposal);
      if (
        parsed.success &&
        hasValidReference(
          {
            action: parsed.data.action,
            ...parsed.data.payload,
          },
          calendars,
          projects,
          parents,
        )
      ) {
        proposal = parsed.data;
      } else {
        reply =
          "Δεν μπόρεσα να αντιστοιχίσω με ασφάλεια τα στοιχεία. " +
          "Πες μου ξανά το ακριβές calendar, project, parent ή ημερομηνία.";
      }
    }
    return json(response, 200, {
      reply,
      proposal,
      draft,
    });
  } catch (error) {
    console.error(
      "command_center_chat_failed",
      error?.name ?? "Error",
      error?.message ?? "Unknown",
    );
    return json(response, 500, {
      error: "Δεν μπόρεσα να επεξεργαστώ το μήνυμα.",
    });
  }
}
