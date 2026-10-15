use serde::Deserialize;

/// Write-path limits and policy controls for note ingestion.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Memory {
	/// Total serialized extraction-input and candidate bytes processed per ingestion request.
	pub ingest_max_bytes: u32,
	/// Display-only character bound for search previews. Stored notes are not truncated.
	#[serde(alias = "max_note_chars")]
	pub preview_max_chars: u32,
	/// Candidate pool size used before final top-k selection.
	pub candidate_k: u32,
	/// Final top-k size for note retrieval.
	pub top_k: u32,
	/// Optional downgrade rules applied after base memory decisions.
	pub policy: MemoryPolicy,
}

/// Collection of memory-policy downgrade rules.
#[derive(Debug, Deserialize)]
pub struct MemoryPolicy {
	/// Ordered policy rules evaluated against note type, scope, and scores.
	pub rules: Vec<MemoryPolicyRule>,
}

/// A single memory-policy rule matched by note metadata and confidence/importance thresholds.
#[derive(Debug, Default, Deserialize)]
pub struct MemoryPolicyRule {
	/// Optional note type selector.
	pub note_type: Option<String>,
	/// Optional scope selector.
	pub scope: Option<String>,
	/// Optional minimum confidence required for the rule to match.
	pub min_confidence: Option<f32>,
	/// Optional minimum importance required for the rule to match.
	pub min_importance: Option<f32>,
}
