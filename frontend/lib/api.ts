// Typed client for the FastAPI stub endpoints. Requests go to /api/*, which next.config.ts
// rewrites to COUNSEL_API_URL (default http://localhost:8000), so the browser never needs CORS.
import type { AnalysisDraftRecord } from "./contracts/analysis_draft_record";
import type { EmailRecord } from "./contracts/email_record";
import type { MatterRecord } from "./contracts/matter_record";

export type { AnalysisDraftRecord, EmailRecord, MatterRecord };

export type Route =
  | "quarantine"
  | "auto_answer"
  | "delegate_review"
  | "lawyer_review"
  | "escalate"
  | "archive"
  | "assign_department";

export type ItemStatus = "pending" | "approved_not_sent" | "rejected" | "escalated" | "closed";
export type Action = "approve" | "edit" | "reject" | "escalate";

export interface HistoryEntry {
  at: string;
  action: Action;
  reviewer_id: string;
  reason: string | null;
  send?: string;
  draft_hash?: string;
  old_hash?: string;
  new_hash?: string;
  old_body?: string;
  new_body?: string;
}

export interface ReviewItem {
  item_id: string;
  message_id: string;
  matter_id: string | null;
  route: Route;
  reasons: string[];
  analysis: AnalysisDraftRecord | null;
  status: ItemStatus;
  approval_token: "present" | null;
  history: HistoryEntry[];
}

export interface InboundEmail {
  sender_name: string;
  sender_email: string;
  to: string[];
  subject: string;
  body: string;
}

export interface AuditEvent {
  id: number;
  occurred_at: string;
  actor: string;
  action: string;
  matter_id: string | null;
  payload: Record<string, unknown>;
}

export interface DemoUsers {
  responsible_lawyer: string;
  hr_legal_delegate: string;
  outsider: string;
}

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: { "content-type": "application/json" },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Cannot reach the API. Is FastAPI running on http://localhost:8000?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body: unknown = await res.json();
      if (body && typeof body === "object" && "detail" in body) {
        const d = (body as { detail: unknown }).detail;
        detail = typeof d === "string" ? d : JSON.stringify(d);
      }
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

const post = (body?: unknown): RequestInit => ({
  method: "POST",
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  users: () => call<DemoUsers>("/stub/users"),
  samples: () => call<Record<string, InboundEmail>>("/stub/samples"),
  runSample: (name: string) => call<ReviewItem>(`/stub/samples/${encodeURIComponent(name)}`, post()),
  item: (id: string) => call<ReviewItem>(`/stub/items/${id}`),
  email: (messageId: string) => call<EmailRecord>(`/stub/emails/${encodeURIComponent(messageId)}`),
  matter: (id: string) => call<MatterRecord>(`/stub/matters/${id}`),
  audit: (matterId: string) => call<AuditEvent[]>(`/stub/audit?matter_id=${matterId}`),
  decide: (
    id: string,
    body: { reviewer_id: string; action: Action; reason?: string; edited_body?: string },
  ) => call<ReviewItem>(`/stub/items/${id}/decision`, post(body)),
  reset: () => call<{ status: string }>("/stub/reset", post()),
};
