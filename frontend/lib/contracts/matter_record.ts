/* Generated from contracts/matter_record.schema.json by scripts/gen-types.mjs. Do not edit. */

export type SchemaVersion = "1.0";
export type MatterId = string;
export type TenantId = string;
export type Title = string;
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
export type Name = string;
export type Email = string | null;
export type Organisation = string | null;
export type Role = "sender" | "recipient" | "internal_requester" | "counterparty" | "other";
/**
 * Company Identification Number if found
 */
export type Cin = string | null;
export type Parties = Party[];
/**
 * Establishment, employee workplace, place of execution, counterparty location
 */
export type States = string[];
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Status = "open" | "awaiting_counterparty" | "awaiting_internal" | "escalated" | "closed";
export type Description = string;
/**
 * e.g. "15 days from receipt"
 */
export type Basis = string;
/**
 * Computed by code from the basis, never by the model
 */
export type ComputedDate = string | null;
/**
 * Message ID, attachment ID or chunk ID
 */
export type SourceId = string;
export type Quote = string;
export type Deadlines = Deadline[];
export type LinkedMessageIds = string[];
export type LinkedDocumentIds = string[];
export type Summary = string;
export type DecidedBy = string;
export type DecidedAt = string;
export type Decisions = Decision[];
export type AssignedLawyerId = string | null;
/**
 * User IDs allowed to see this matter
 *
 * @minItems 1
 */
export type AccessList = [string, ...string[]];
export type LegalHold = boolean;

export interface MatterRecord {
  schema_version?: SchemaVersion;
  matter_id: MatterId;
  tenant_id: TenantId;
  title: Title;
  type: Category;
  parties?: Parties;
  states?: States;
  risk_level: RiskLevel;
  status: Status;
  deadlines?: Deadlines;
  linked_message_ids?: LinkedMessageIds;
  linked_document_ids?: LinkedDocumentIds;
  decisions?: Decisions;
  assigned_lawyer_id?: AssignedLawyerId;
  access_list: AccessList;
  legal_hold?: LegalHold;
}
export interface Party {
  name: Name;
  email?: Email;
  organisation?: Organisation;
  role: Role;
  cin?: Cin;
}
export interface Deadline {
  description: Description;
  basis: Basis;
  computed_date?: ComputedDate;
  source: SourceQuote;
}
/**
 * An exact span from an email, attachment or document that supports a value.
 */
export interface SourceQuote {
  source_id: SourceId;
  quote: Quote;
}
export interface Decision {
  summary: Summary;
  decided_by: DecidedBy;
  decided_at: DecidedAt;
}
