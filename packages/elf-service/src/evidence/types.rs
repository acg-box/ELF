use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::{
	NoteFetchResponse,
	docs::{DocsExcerptResponse, DocsGetResponse},
};

/// A derived note and bounded original context resolved under current read permissions.
#[derive(Clone, Debug, Serialize)]
pub struct NoteEvidenceResponse {
	/// Derived memory; its confidence is not proof of source truth.
	pub note: NoteFetchResponse,
	/// Verified original excerpts and metadata, deduplicated by document and span.
	pub sources: Vec<NoteSourceEvidence>,
	/// Whether all distinct supported pointers were resolved within the read budget.
	pub complete: bool,
}

/// Original source context. Byte integrity and semantic support are distinct.
#[derive(Clone, Debug, Serialize)]
pub struct NoteSourceEvidence {
	/// Current, authorized source metadata.
	pub metadata: DocsGetResponse,
	/// Bounded excerpt with exact byte offsets and verification hashes.
	pub excerpt: DocsExcerptResponse,
}

/// The agent's semantic conclusion, not a server-certified fact.
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ClaimState {
	/// A positive claim supported by the cited evidence according to the agent.
	Supported,
	/// The source explicitly states absence, distinct from missing information.
	Absent,
	/// Evidence is insufficient to establish the requested fact.
	Unknown,
	/// Sources disagree and the conflict remains unresolved.
	Conflict,
}

/// One answer claim and its source bindings.
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ClaimEvidence {
	/// The atomic statement to assess, including its subject and time when relevant.
	pub text: String,
	/// Semantic state asserted by the agent.
	pub state: ClaimState,
	/// Exact quotes supporting this statement rather than the answer as a whole.
	pub citations: Vec<ClaimCitation>,
}

/// A quote from a derived note or an immutable original document.
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum ClaimCitation {
	/// Native locator copied from an evidence pack; current read access is always rechecked.
	Reference {
		/// Versioned document/hash/byte-span locator, not an access token.
		reference: String,
	},
	/// Quote from a currently readable note. This is derived evidence.
	Note {
		/// Note identifier.
		note_id: Uuid,
		/// Verbatim quote from the note body.
		quote: String,
	},
	/// Quote from a currently readable original with a hash guard.
	Source {
		/// Original document identifier.
		doc_id: Uuid,
		/// Whole-document BLAKE3 hash returned by source retrieval.
		content_hash: String,
		/// Verbatim quote from the original.
		quote: String,
	},
}

/// Mechanical binding result for a claim. It does not certify entailment.
#[derive(Clone, Debug, Serialize)]
pub struct ClaimBinding {
	/// Claim position in the request.
	pub claim_index: usize,
	/// One result per requested citation, in request order.
	pub citation_verified: Vec<bool>,
	/// Whether required evidence is present and every supplied quote resolves.
	pub binding_verified: bool,
	/// Resolved exact citations in input order; null for an unreadable or invalid binding.
	pub resolved_citations: Vec<Option<ClaimCitation>>,
}

/// Checked source bindings, with an explicit semantic boundary.
#[derive(Clone, Debug, Serialize)]
pub struct EvidenceCheckResponse {
	/// Claim checks in request order.
	pub claims: Vec<ClaimBinding>,
	/// Always `not_evaluated`: the caller must assess subject, time, and entailment.
	pub semantic_support: &'static str,
}

/// Authorized read context and claims to bind to evidence.
#[derive(Clone, Debug)]
pub struct EvidenceCheckRequest {
	/// Tenant that owns the read.
	pub tenant_id: String,
	/// Project that owns the read.
	pub project_id: String,
	/// Agent requesting the read.
	pub agent_id: String,
	/// Profile applied to original-source reads.
	pub read_profile: String,
	/// Claims supplied by the agent.
	pub claims: Vec<ClaimEvidence>,
}
