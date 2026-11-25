"use client";

import { useEffect, useState } from "react";
import type { Action, DemoUsers, ReviewItem } from "@/lib/api";
import { Panel, StatusBadge, shortTime } from "./ui";

export type ReviewerKey = keyof DemoUsers;

const REVIEWERS: Record<ReviewerKey, string> = {
  responsible_lawyer: "Responsible lawyer",
  hr_legal_delegate: "HR legal delegate",
  outsider: "Outsider (no access)",
};

export function DraftPanel({
  item,
  reviewer,
  onReviewer,
  onDecide,
  busy,
}: {
  item: ReviewItem;
  reviewer: ReviewerKey;
  onReviewer: (r: ReviewerKey) => void;
  onDecide: (action: Action, extra?: { reason?: string; edited_body?: string }) => void;
  busy: boolean;
}) {
  const draft = item.analysis?.draft_reply ?? null;
  const [body, setBody] = useState(draft?.body ?? "");
  const [reason, setReason] = useState("");

  useEffect(() => {
    setBody(draft?.body ?? "");
    setReason("");
  }, [item.item_id, draft?.body]);

  const pending = item.status === "pending";
  const edited = draft !== null && body !== draft.body;
  const canAct = pending && !busy && draft !== null;

  return (
    <Panel title="Draft reply" aside={<StatusBadge status={item.status} />}>
      <label className="field">
        Acting as
        <select value={reviewer} onChange={(e) => onReviewer(e.target.value as ReviewerKey)}>
          {Object.entries(REVIEWERS).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
      </label>

      {draft === null ? (
        <div className="alert info">
          {item.route === "escalate"
            ? "No reply is drafted for critical matters. Counsel decides the response from the brief."
            : item.route === "quarantine"
              ? "Nothing to review: the email was quarantined before analysis."
              : "Nothing to send: this email was not routed for a reply."}
        </div>
      ) : (
        <>
          <dl className="meta">
            <dt>To</dt>
            <dd>{draft.to.join(", ")}</dd>
            <dt>Subject</dt>
            <dd>{draft.subject}</dd>
          </dl>
          <label className="field">
            Body {edited && <em>(unsaved edit)</em>}
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              disabled={!pending}
              lang={draft.language}
            />
          </label>
          <div className="hash">
            Draft hash <code>{item.analysis?.draft_hash?.slice(0, 16)}…</code> · approval is bound
            to this exact text
          </div>

          <div className="actions">
            <button
              className="btn primary"
              disabled={!canAct || edited}
              title={edited ? "Save the edit first, then approve the new version" : undefined}
              onClick={() => onDecide("approve")}
            >
              Approve
            </button>
            <button
              className="btn"
              disabled={!canAct || !edited || body.trim() === ""}
              onClick={() => onDecide("edit", { edited_body: body })}
            >
              Save edit
            </button>
          </div>
          <div className="reject-row">
            <input
              type="text"
              placeholder="Reason for rejecting"
              aria-label="Reason for rejecting"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={!pending}
            />
            <button
              className="btn danger"
              disabled={!canAct || reason.trim() === ""}
              onClick={() => onDecide("reject", { reason })}
            >
              Reject
            </button>
          </div>
          <button className="btn ghost" disabled={!canAct} onClick={() => onDecide("escalate")}>
            Escalate to counsel
          </button>

          {item.status === "approved_not_sent" && (
            <div className="alert success" role="status">
              Approved. Not sent: sending is disabled in the prototype.
            </div>
          )}
        </>
      )}

      {item.history.length > 0 && (
        <section className="section">
          <h3>Decisions</h3>
          <ol className="timeline">
            {item.history.map((h, i) => (
              <li key={i}>
                <time dateTime={h.at}>{shortTime(h.at)}</time>
                <span>
                  <strong>{h.action}</strong>
                  {h.reason ? ` · ${h.reason}` : ""}
                  {h.new_hash ? ` · new hash ${h.new_hash.slice(0, 8)}…` : ""}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </Panel>
  );
}
