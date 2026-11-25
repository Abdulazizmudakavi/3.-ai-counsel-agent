import type { EmailRecord, InboundEmail, ReviewItem } from "@/lib/api";
import { Panel, RiskBadge, Section } from "./ui";

const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  hi: "Hindi",
  mr: "Marathi",
  ta: "Tamil",
  te: "Telugu",
  kn: "Kannada",
  bn: "Bengali",
  gu: "Gujarati",
};

export function EmailPanel({
  email,
  record,
  item,
}: {
  email: InboundEmail;
  record: EmailRecord | null;
  item: ReviewItem;
}) {
  const lang = record?.language.code;
  return (
    <Panel title="Original email">
      <p className="subject">{email.subject || "(no subject)"}</p>
      <dl className="meta">
        <dt>From</dt>
        <dd>
          {email.sender_name} &lt;{email.sender_email}&gt;
        </dd>
        <dt>To</dt>
        <dd>{email.to.join(", ")}</dd>
        {record && (
          <>
            <dt>Received</dt>
            <dd>{new Date(record.received_at).toLocaleString()}</dd>
          </>
        )}
      </dl>
      <div className="email-body" lang={lang}>
        {email.body}
      </div>

      {item.route === "quarantine" ? (
        <div className="alert error" role="status">
          Quarantined by the security gateway. This email never reached triage or the AI.
        </div>
      ) : record ? (
        <>
          <Section title="Triage">
            <div className="chips">
              <span className="chip">
                {LANGUAGE_NAMES[record.language.code] ?? record.language.code}
                {record.language.script ? ` · ${record.language.script}` : ""}
              </span>
              <span className="chip">{record.is_legal ? record.category : "not legal"}</span>
              <span className="chip">{record.intent}</span>
              <span className="chip">
                urgency <RiskBadge level={record.urgency} />
              </span>
            </div>
            <p className="hash" style={{ margin: "6px 0 0" }}>
              {record.is_legal_reason} · model <code>{record.triage_model}</code>
            </p>
          </Section>

          {(record.escalation_triggers?.length ?? 0) > 0 && (
            <Section title="Escalation rules hit">
              <table>
                <tbody>
                  {record.escalation_triggers?.map((t) => (
                    <tr key={t.rule_id}>
                      <td>
                        <code>{t.rule_id}</code>
                      </td>
                      <td lang={t.language}>“{t.matched_text}”</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>
          )}

          {(record.deadlines?.length ?? 0) > 0 && (
            <Section title="Deadlines (computed by code)">
              <table>
                <tbody>
                  {record.deadlines?.map((d, i) => (
                    <tr key={i}>
                      <td>{d.basis}</td>
                      <td className="num">{d.computed_date ?? "needs a human"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>
          )}
        </>
      ) : null}
    </Panel>
  );
}
