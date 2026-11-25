import type { AuditEvent, MatterRecord, ReviewItem } from "@/lib/api";
import { Panel, RiskBadge, ROUTE_INFO, Section, shortTime } from "./ui";

const CRITICAL_POINTS = 30;

export function AnalysisPanel({
  item,
  matter,
  audit,
}: {
  item: ReviewItem;
  matter: MatterRecord | null;
  audit: AuditEvent[];
}) {
  const a = item.analysis;
  const route = ROUTE_INFO[item.route];
  const verdicts = new Map((a?.verifier_results ?? []).map((v) => [v.claim_id, v]));

  return (
    <Panel title="Analysis" aside={a ? <RiskBadge level={a.risk_level} /> : undefined}>
      <div className={`route-card ${item.route}`}>
        <div className="route-name">Route: {route.name}</div>
        <p>{route.why}</p>
        {item.reasons.length > 0 && (
          <ul className="reasons">
            {item.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </div>

      {a && (
        <>
          <Section title="Risk score">
            <div className="score-row">
              <span className="score-num">{a.risk_points}</span>
              <span>points</span>
              <RiskBadge level={a.risk_level} />
            </div>
            <div
              className="meter"
              role="meter"
              aria-valuemin={0}
              aria-valuemax={CRITICAL_POINTS}
              aria-valuenow={a.risk_points}
              aria-label="Risk points"
            >
              <span style={{ width: `${Math.min(100, (a.risk_points / CRITICAL_POINTS) * 100)}%` }} />
            </div>
            {(a.risk_findings?.length ?? 0) === 0 && (
              <p className="hash" style={{ margin: "6px 0 0" }}>
                {a.risk_level === "CRITICAL"
                  ? "Critical because an escalation rule fired, not because of contract points."
                  : "No contract clauses scored for this email."}
              </p>
            )}
            {(a.risk_findings?.length ?? 0) > 0 && (
              <table style={{ marginTop: 8 }}>
                <thead>
                  <tr>
                    <th>Clause</th>
                    <th>Finding</th>
                    <th>Evidence</th>
                    <th className="num">Pts</th>
                  </tr>
                </thead>
                <tbody>
                  {a.risk_findings?.map((f, i) => (
                    <tr key={i}>
                      <td>{f.clause_ref}</td>
                      <td>{f.finding.replaceAll("_", " ")}</td>
                      <td>“{f.evidence}”</td>
                      <td className="num">{f.points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Section>

          {(a.interpretation?.length ?? 0) > 0 && (
            <Section title="Findings and citations">
              {a.interpretation?.map((c) => {
                const v = verdicts.get(c.claim_id);
                const passed = v ? v.citation_resolved && v.supported : false;
                return (
                  <div className="claim" key={c.claim_id}>
                    <div className="claim-text">{c.text}</div>
                    {c.citations.map((cit) => (
                      <div className="citation" key={cit.chunk_id}>
                        <div className="path">{cit.heading_path}</div>
                        <code>{cit.chunk_id}</code>
                        <blockquote>“{cit.quote}”</blockquote>
                      </div>
                    ))}
                    <div className={passed ? "ok" : "bad"} style={{ fontSize: 12 }}>
                      Verifier: {v ? `${v.citation_resolved ? "citation found" : "citation missing"} · ${v.supported ? "supports claim" : "does not support claim"}` : "no result"}
                    </div>
                  </div>
                );
              })}
            </Section>
          )}

          <Section title="Recommendation">
            <div>{a.recommendation}</div>
          </Section>

          <Section title={a.risk_level === "CRITICAL" ? "Brief for counsel" : "Internal note"}>
            <div className={`note${a.risk_level === "CRITICAL" ? " brief" : ""}`}>{a.internal_note}</div>
          </Section>

          {(a.assumptions?.length ?? 0) > 0 && (
            <Section title="Assumptions">
              <ul className="reasons">
                {a.assumptions?.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </Section>
          )}
        </>
      )}

      {matter && (
        <Section title="Matter">
          <div className="chips">
            <span className="chip">{matter.title}</span>
            <span className="chip">{matter.status.replaceAll("_", " ")}</span>
            {matter.legal_hold && <span className="chip bad">legal hold</span>}
            <span className="chip">{matter.access_list.length} with access</span>
          </div>
        </Section>
      )}

      {audit.length > 0 && (
        <Section title="Audit trail">
          <ol className="timeline">
            {audit.map((e) => (
              <li key={e.id}>
                <time dateTime={e.occurred_at}>{shortTime(e.occurred_at)}</time>
                <span>
                  <code>{e.action}</code> · {e.actor.startsWith("user:") ? "reviewer" : e.actor}
                </span>
              </li>
            ))}
          </ol>
        </Section>
      )}
    </Panel>
  );
}
