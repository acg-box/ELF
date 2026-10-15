pub(super) mod budget;

mod windows;

use std::collections::HashSet;

use serde::Serialize;
use time::OffsetDateTime;
use uuid::Uuid;

use crate::{
	evidence::{ElfService, Error, NoteFetchRequest, NoteSourceEvidence, Result, reference},
	search,
};

/// Selected notes to materialize under current source-read permissions.
#[derive(Clone, Debug)]
pub struct EvidencePackRequest {
	/// Tenant that owns the read.
	pub tenant_id: String,
	/// Project that owns the read.
	pub project_id: String,
	/// Agent requesting the read.
	pub agent_id: String,
	/// Read profile applied to every note and source.
	pub read_profile: String,
	/// One to twelve note IDs in retrieval order. Duplicates are ignored.
	pub note_ids: Vec<Uuid>,
	/// Total original-text byte budget; defaults to 32768 and cannot exceed it.
	pub max_source_bytes: Option<usize>,
	/// Total serialized response budget, including notes, originals, and metadata.
	pub max_bytes: Option<usize>,
}

/// Derived candidates linked to separate, immutable source context.
#[derive(Clone, Debug, Serialize)]
pub struct EvidencePackResponse {
	/// Read contract identifier.
	pub schema: &'static str,
	/// Derived notes; these are not independently verified facts.
	pub notes: Vec<EvidencePackNote>,
	/// Deduplicated original windows with native citation locators.
	pub sources: Vec<EvidencePackSource>,
	/// Whether every requested note and supported source pointer fit and resolved.
	pub complete: bool,
	/// Number of original-text bytes included.
	pub source_bytes: usize,
	/// Requested notes not returned, including those that did not fit the response budget.
	pub omitted_note_ids: Vec<Uuid>,
}

/// A derived note with links to its original context; no inferred subject merge.
#[derive(Clone, Debug, Serialize)]
pub struct EvidencePackNote {
	/// Native memory identifier.
	pub note_id: Uuid,
	/// Stored memory kind, such as a fact, constraint, or plan; not a truth verdict.
	pub note_type: String,
	/// Project that owns the memory, not an inferred subject identity.
	pub project_id: String,
	/// Stored visibility scope. Source reads still enforce their own permissions.
	pub scope: String,
	/// Derived memory text.
	pub text: String,
	/// Verbatim-bound stored clauses that can preserve qualifiers omitted by the short text.
	/// These remain derived evidence; inspect the linked originals before using them.
	#[serde(skip_serializing_if = "Vec::is_empty")]
	pub facts: Vec<String>,
	/// Stored evidence quotes present in this note's returned, readable source windows.
	/// These fragments can preserve qualifiers; they do not establish a complete rule.
	#[serde(skip_serializing_if = "Vec::is_empty")]
	pub evidence_quotes: Vec<String>,
	/// Source-window references, in pointer order.
	pub source_references: Vec<String>,
	/// Whether this note's source context resolved within the pack budget.
	pub complete: bool,
}

/// Original text is kept with its identity and record-time metadata.
#[derive(Clone, Debug, Serialize)]
pub struct EvidencePackSource {
	/// Stable locator accepted by the claim checker; grants no read access.
	pub reference: String,
	/// Original document identity.
	pub doc_id: Uuid,
	/// Original document content hash.
	pub content_hash: String,
	/// Inclusive byte offset in the original.
	pub start: usize,
	/// Exclusive byte offset in the original.
	pub end: usize,
	/// Exact source window. Subject and effective time must be established from its content.
	pub text: String,
	/// Source title, when supplied by its owner.
	pub title: Option<String>,
	/// Stored source origin, including its owner/path/revision when supplied.
	/// This locator is provenance, not evidence that a rule applies to another subject.
	pub origin: Option<String>,
	/// Timestamp declared by the source record; not an inferred fact-validity time.
	pub source_timestamp: Option<String>,
	#[serde(with = "crate::time_serde")]
	/// Time ELF captured the source; never used as a fact's effective time.
	pub captured_at: OffsetDateTime,
}
impl EvidencePackSource {
	pub(super) fn from_evidence(source: NoteSourceEvidence) -> Self {
		let metadata = source.metadata;
		let excerpt = source.excerpt;

		Self {
			reference: reference::source_reference(
				metadata.doc_id,
				&metadata.content_hash,
				excerpt.start_offset,
				excerpt.end_offset,
			),
			doc_id: metadata.doc_id,
			content_hash: metadata.content_hash,
			start: excerpt.start_offset,
			end: excerpt.end_offset,
			text: excerpt.excerpt,
			title: metadata.title,
			origin: metadata.source_ref.get("origin").and_then(|v| v.as_str()).map(str::to_string),
			source_timestamp: metadata
				.source_ref
				.get("ts")
				.and_then(|v| v.as_str())
				.map(str::to_string),
			captured_at: metadata.created_at,
		}
	}
}

impl ElfService {
	/// Materialize selected memories without a new model, index, or storage authority.
	pub async fn evidence_pack(&self, req: EvidencePackRequest) -> Result<EvidencePackResponse> {
		let budget = req.max_source_bytes.unwrap_or(32_768);
		let response_budget = budget::response_limit(req.max_bytes)?;

		if req.note_ids.is_empty() || req.note_ids.len() > 12 || !(1..=32_768).contains(&budget) {
			return Err(Error::InvalidRequest {
				message: "Supply 1 to 12 note IDs and a source byte budget between 1 and 32768."
					.into(),
			});
		}

		search::resolve_read_profile_scopes(&self.cfg, &req.read_profile)?;

		let distinct_notes = req.note_ids.iter().collect::<HashSet<_>>().len();
		let window_bytes = (budget / distinct_notes).max(1);
		let mut result = EvidencePackResponse {
			schema: "elf.evidence_pack/v1",
			notes: Vec::new(),
			sources: Vec::new(),
			complete: true,
			source_bytes: 0,
			omitted_note_ids: Vec::new(),
		};
		let mut seen = HashSet::new();

		for note_id in req.note_ids {
			if !seen.insert(note_id) {
				continue;
			}

			let expanded = self
				.note_evidence_bounded(
					NoteFetchRequest {
						tenant_id: req.tenant_id.clone(),
						project_id: req.project_id.clone(),
						agent_id: req.agent_id.clone(),
						note_id,
					},
					req.read_profile.clone(),
					Some(window_bytes),
				)
				.await;
			let expanded = match expanded {
				Ok(value) => value,
				Err(
					Error::NotFound { .. }
					| Error::InvalidRequest { .. }
					| Error::ScopeDenied { .. },
				) => {
					result.complete = false;

					result.omitted_note_ids.push(note_id);

					continue;
				},
				Err(error) => return Err(error),
			};
			let mut note = EvidencePackNote {
				note_id,
				note_type: expanded.note.r#type,
				project_id: expanded.note.project_id,
				scope: expanded.note.scope,
				text: expanded.note.text,
				facts: expanded.note.structured.and_then(|fields| fields.facts).unwrap_or_default(),
				evidence_quotes: expanded.note.source_ref["evidence"]
					.as_array()
					.into_iter()
					.flatten()
					.filter_map(|item| item["quote"].as_str().map(str::to_string))
					.collect(),
				source_references: Vec::new(),
				complete: expanded.complete,
			};

			for source in expanded.sources {
				let metadata = source.metadata;
				let excerpt = source.excerpt;
				let reference = reference::source_reference(
					metadata.doc_id,
					&metadata.content_hash,
					excerpt.start_offset,
					excerpt.end_offset,
				);

				if !result.sources.iter().any(|prior| prior.reference == reference) {
					if excerpt.excerpt.len() > budget - result.source_bytes {
						note.complete = false;

						continue;
					}

					result.source_bytes += excerpt.excerpt.len();

					result.sources.push(EvidencePackSource::from_evidence(NoteSourceEvidence {
						metadata,
						excerpt,
					}));
				}

				note.source_references.push(reference);
			}

			result.complete &= note.complete;

			result.notes.push(note);
		}

		windows::merge_overlaps(&mut result);

		result.limit_bytes(response_budget)?;

		Ok(result)
	}
}
