"use client";

import { useCallback, useEffect, useState } from "react";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { DraftPanel, type ReviewerKey } from "@/components/DraftPanel";
import { EmailPanel } from "@/components/EmailPanel";
import {
  api,
  ApiError,
  type Action,
  type AuditEvent,
  type DemoUsers,
  type EmailRecord,
  type InboundEmail,
  type MatterRecord,
  type ReviewItem,
} from "@/lib/api";

const SAMPLE_LABELS: Record<string, string> = {
  nda_external: "NDA from vendor",
  policy_question_internal: "Leave policy question",
  show_cause_hindi: "Show-cause notice (Hindi)",
  legal_threat_customer: "Customer legal threat",
  invoice_query: "Invoice query",
  newsletter: "Newsletter",
  prompt_injection: "Prompt injection",
};

interface Loaded {
  sample: string;
  item: ReviewItem;
  record: EmailRecord | null;
  matter: MatterRecord | null;
  audit: AuditEvent[];
}

export default function ReviewConsole() {
  const [samples, setSamples] = useState<Record<string, InboundEmail> | null>(null);
  const [users, setUsers] = useState<DemoUsers | null>(null);
  const [reviewer, setReviewer] = useState<ReviewerKey>("responsible_lawyer");
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.samples(), api.users()])
      .then(([s, u]) => {
        setSamples(s);
        setUsers(u);
      })
      .catch((e: unknown) => setError(message(e)));
  }, []);

  const refresh = useCallback(async (sample: string, item: ReviewItem): Promise<Loaded> => {
    const [record, matter, audit] = await Promise.all([
      item.route === "quarantine" ? null : api.email(item.message_id).catch(() => null),
      item.matter_id ? api.matter(item.matter_id) : null,
      item.matter_id ? api.audit(item.matter_id) : ([] as AuditEvent[]),
    ]);
    return { sample, item, record, matter, audit };
  }, []);

  async function run(sample: string) {
    setBusy(true);
    setError(null);
    try {
      const item = await api.runSample(sample);
      setLoaded(await refresh(sample, item));
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  async function decide(action: Action, extra?: { reason?: string; edited_body?: string }) {
    if (!loaded || !users) return;
    setBusy(true);
    setError(null);
    try {
      const item = await api.decide(loaded.item.item_id, {
        reviewer_id: users[reviewer],
        action,
        ...extra,
      });
      setLoaded(await refresh(loaded.sample, item));
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    setBusy(true);
    try {
      await api.reset();
      setLoaded(null);
      setError(null);
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  const email = loaded && samples ? samples[loaded.sample] : undefined;

  return (
    <>
      <header className="topbar">
        <div className="topbar-row">
          <div className="brand">
            Review Console<small>AI Corporate Counsel Agent · prototype</small>
          </div>
          <span className="safe-flag">Sending disabled</span>
          <button className="btn ghost" onClick={reset} disabled={busy}>
            Reset
          </button>
        </div>
        <nav className="pill-row" aria-label="Sample emails">
          {samples
            ? Object.keys(samples).map((name) => (
                <button
                  key={name}
                  className="pill"
                  aria-pressed={loaded?.sample === name}
                  disabled={busy}
                  onClick={() => run(name)}
                >
                  {SAMPLE_LABELS[name] ?? name}
                </button>
              ))
            : !error && <span className="hash">Loading samples…</span>}
        </nav>
        {error && (
          <div className="alert error" role="alert">
            {error}
          </div>
        )}
      </header>

      {loaded && email ? (
        <main className="grid">
          <EmailPanel email={email} record={loaded.record} item={loaded.item} />
          <AnalysisPanel item={loaded.item} matter={loaded.matter} audit={loaded.audit} />
          <DraftPanel
            item={loaded.item}
            reviewer={reviewer}
            onReviewer={setReviewer}
            onDecide={decide}
            busy={busy}
          />
        </main>
      ) : (
        <main className="empty">
          Pick a sample email above. It runs through the gateway, triage, analysis and policy
          engine, then appears here for review.
        </main>
      )}
    </>
  );
}

function message(e: unknown): string {
  if (e instanceof ApiError) {
    const prefix: Record<number, string> = {
      403: "Not allowed",
      409: "Conflict",
      422: "Invalid",
    };
    return `${prefix[e.status] ?? `Error ${e.status}`}: ${e.message}`;
  }
  return e instanceof Error ? e.message : String(e);
}
