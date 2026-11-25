/* Generated from contracts/analysis_draft_record.schema.json by scripts/gen-types.mjs. Do not edit. */

export type SchemaVersion = "1.0";
export type TenantId = string;
export type MatterId = string;
export type MessageId = string;
export type Statement = string;
/**
 * Message ID, attachment ID or chunk ID
 */
export type SourceId = string;
export type Quote = string;
export type Facts = Fact[];
export type ClaimId = string;
export type Text = string;
/**
 * Every legal statement is cited
 *
 * @minItems 1
 */
export type Citations = [Citation, ...Citation[]];
export type ChunkId = string;
/**
 * e.g. "MSA > 9 Liability > 9.2"
 */
export type HeadingPath = string;
export type Quote1 = string;
export type Interpretation = Claim[];
export type Assumptions = string[];
export type Recommendation = string;
export type ClaimId1 = string;
/**
 * Cited text exists in the retrieved source
 */
export type CitationResolved = boolean;
/**
 * Source supports the claim (independent check)
 */
export type Supported = boolean;
export type Note = string | null;
export type VerifierResults = VerifierResult[];
export type ClauseRef = string;
export type Finding =
  | "preferred"
  | "within_fallback"
  | "beyond_walk_away"
  | "missing_required"
  | "unlimited_liability"
  | "foreign_governing_law"
  | "ambiguity";
/**
 * From the lawyer-owned rules table, not the model
 */
export type Points = number;
export type Evidence = string;
export type RiskFindings = RiskFinding[];
export type RiskPoints = number;
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Subject = string;
export type Body = string;
export type Language = string;
/**
 * Policy engine checks these are thread participants
 *
 * @minItems 1
 */
export type To = [string, ...string[]];
export type InternalNote = string;
export type DraftHash = string | null;
/**
 * @minItems 1
 */
export type ModelIds = [string, ...string[]];

export interface AnalysisDraftRecord {
  schema_version?: SchemaVersion;
  tenant_id: TenantId;
  matter_id: MatterId;
  message_id: MessageId;
  facts?: Facts;
  interpretation?: Interpretation;
  assumptions?: Assumptions;
  recommendation: Recommendation;
  verifier_results?: VerifierResults;
  risk_findings?: RiskFindings;
  risk_points: RiskPoints;
  risk_level: RiskLevel;
  /**
   * Empty for CRITICAL matters: brief for counsel only
   */
  draft_reply?: DraftReply | null;
  internal_note: InternalNote;
  draft_hash?: DraftHash;
  model_ids: ModelIds;
}
export interface Fact {
  statement: Statement;
  source: SourceQuote;
}
/**
 * An exact span from an email, attachment or document that supports a value.
 */
export interface SourceQuote {
  source_id: SourceId;
  quote: Quote;
}
export interface Claim {
  claim_id: ClaimId;
  text: Text;
  citations: Citations;
}
export interface Citation {
  chunk_id: ChunkId;
  heading_path: HeadingPath;
  quote: Quote1;
}
export interface VerifierResult {
  claim_id: ClaimId1;
  citation_resolved: CitationResolved;
  supported: Supported;
  note?: Note;
}
export interface RiskFinding {
  clause_ref: ClauseRef;
  finding: Finding;
  points: Points;
  evidence: Evidence;
}
export interface DraftReply {
  subject: Subject;
  body: Body;
  language: Language;
  to: To;
}
