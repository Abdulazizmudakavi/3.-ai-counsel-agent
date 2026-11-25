/* Generated from contracts/email_record.schema.json by scripts/gen-types.mjs. Do not edit. */

export type SchemaVersion = "1.0";
export type TenantId = string;
/**
 * RFC 5322 Message-ID
 */
export type MessageId = string;
export type ThreadId = string;
export type ReceivedAt = string;
export type Name = string;
export type Email = string | null;
export type Organisation = string | null;
export type Role = "sender" | "recipient" | "internal_requester" | "counterparty" | "other";
/**
 * Company Identification Number if found
 */
export type Cin = string | null;
export type Code = string;
/**
 * ISO 15924, e.g. "Deva", "Taml", "Latn"
 */
export type Script = string | null;
/**
 * e.g. Hindi written in Latin letters
 */
export type Romanised = boolean;
export type AttachmentId = string;
export type Filename = string;
export type Sha256 = string;
export type OcrUsed = boolean;
/**
 * Pages below the OCR confidence floor; sent to a human
 */
export type LowConfidencePages = number[];
export type Attachments = AttachmentInfo[];
export type IsLegal = boolean;
export type IsLegalReason = string;
export type Category =
  | "contract_review"
  | "vendor_dispute"
  | "customer_dispute"
  | "employment"
  | "regulatory_notice"
  | "data_privacy"
  | "ip"
  | "nda"
  | "procurement"
  | "litigation_threat"
  | "payment_dispute"
  | "compliance"
  | "corporate_governance"
  | "partnership"
  | "confidentiality"
  | "general_inquiry";
export type Intent = "question" | "review_request" | "notice" | "demand" | "fyi" | "scheduling";
export type Parties = Party[];
export type Statement = string;
/**
 * Message ID, attachment ID or chunk ID
 */
export type SourceId = string;
export type Quote = string;
export type Facts = Fact[];
export type Description = string;
/**
 * e.g. "15 days from receipt"
 */
export type Basis = string;
/**
 * Computed by code from the basis, never by the model
 */
export type ComputedDate = string | null;
export type Deadlines = Deadline[];
export type Signal =
  | "dispute"
  | "litigation_threat"
  | "regulator"
  | "breach"
  | "termination"
  | "indemnity_claim"
  | "fraud"
  | "criminal"
  | "data_incident";
export type Signals = Signal[];
export type RuleId = string;
export type MatchedText = string;
export type Language = string;
export type EscalationTriggers = TriggerHit[];
export type MissingInfo = string[];
export type MatterId = string;
export type Score = number;
/**
 * @minItems 1
 */
export type Reasons = [string, ...string[]];
export type MatterCandidates = MatterCandidate[];
/**
 * Set by rules from deadlines and signals, not the model
 */
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
/**
 * Model ID used, for the Jev vs Haiku benchmark
 */
export type TriageModel = string;

export interface EmailRecord {
  schema_version?: SchemaVersion;
  tenant_id: TenantId;
  message_id: MessageId;
  thread_id: ThreadId;
  received_at: ReceivedAt;
  sender: Party;
  language: LanguageInfo;
  attachments?: Attachments;
  is_legal: IsLegal;
  is_legal_reason: IsLegalReason;
  /**
   * Required when is_legal is true
   */
  category?: Category | null;
  intent: Intent;
  parties?: Parties;
  facts?: Facts;
  deadlines?: Deadlines;
  signals?: Signals;
  escalation_triggers?: EscalationTriggers;
  missing_info?: MissingInfo;
  matter_candidates?: MatterCandidates;
  urgency: RiskLevel;
  triage_model: TriageModel;
}
export interface Party {
  name: Name;
  email?: Email;
  organisation?: Organisation;
  role: Role;
  cin?: Cin;
}
export interface LanguageInfo {
  code: Code;
  script?: Script;
  romanised?: Romanised;
}
export interface AttachmentInfo {
  attachment_id: AttachmentId;
  filename: Filename;
  sha256: Sha256;
  language?: LanguageInfo | null;
  ocr_used?: OcrUsed;
  low_confidence_pages?: LowConfidencePages;
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
export interface Deadline {
  description: Description;
  basis: Basis;
  computed_date?: ComputedDate;
  source: SourceQuote;
}
/**
 * A hit from the deterministic escalation rules (keyword / sender), not the model.
 */
export interface TriggerHit {
  rule_id: RuleId;
  matched_text: MatchedText;
  language: Language;
}
export interface MatterCandidate {
  matter_id: MatterId;
  score: Score;
  reasons: Reasons;
}
