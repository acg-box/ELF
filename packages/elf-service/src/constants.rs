/// Rejection code emitted when event evidence quotes do not match the source messages.
pub const REJECT_EVIDENCE_MISMATCH: &str = "REJECT_EVIDENCE_MISMATCH";
/// Rejection code emitted when a write policy and extracted output disagree.
pub const REJECT_WRITE_POLICY_MISMATCH: &str = "REJECT_WRITE_POLICY_MISMATCH";
/// Rejection code emitted when the evidence quote count is outside runtime limits.
pub const REJECT_EVIDENCE_QUOTE_COUNT: &str = "REJECT_EVIDENCE_QUOTE_COUNT";
/// Rejection code emitted when an evidence quote exceeds its UTF-8 byte limit.
pub const REJECT_EVIDENCE_QUOTE_TOO_LONG: &str = "REJECT_EVIDENCE_QUOTE_TOO_LONG";
