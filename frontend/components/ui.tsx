import type { ReactNode } from "react";
import type { ItemStatus, Route } from "@/lib/api";

type Level = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export function RiskBadge({ level }: { level: Level }) {
  return <span className={`risk risk-${level}`}>{level}</span>;
}

export function StatusBadge({ status }: { status: ItemStatus }) {
  return <span className={`status ${status}`}>{STATUS_LABEL[status]}</span>;
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

export function Panel({
  title,
  aside,
  children,
}: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel" aria-label={title}>
      <header className="panel-head">
        <h2>{title}</h2>
        {aside}
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export const STATUS_LABEL: Record<ItemStatus, string> = {
  pending: "Pending review",
  approved_not_sent: "Approved · not sent",
  rejected: "Rejected",
  escalated: "Escalated",
  closed: "Closed",
};

export const ROUTE_INFO: Record<Route, { name: string; why: string }> = {
  lawyer_review: {
    name: "Lawyer review",
    why: "A lawyer must approve before anything leaves the company.",
  },
  delegate_review: {
    name: "Delegate review",
    why: "Internal, low-risk, fully cited policy answer. An authorised delegate may approve.",
  },
  escalate: {
    name: "Escalated to counsel",
    why: "Critical matter. No reply is drafted; the agent prepared a brief and alerted humans.",
  },
  quarantine: {
    name: "Quarantined",
    why: "Blocked by the security gateway before the AI saw it. A human must check it.",
  },
  archive: { name: "Archived", why: "Not a legal matter and nothing to act on." },
  assign_department: {
    name: "Assigned to department",
    why: "Not a legal matter. Forwarded internally to the right team.",
  },
  auto_answer: {
    name: "Auto-answer",
    why: "Pre-approved template for a proven category (disabled in the prototype).",
  },
};

export function shortTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
