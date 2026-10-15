//! Bounded evidence discovery. Surface matches are candidates, never identity assertions.

use std::collections::HashSet;

use serde::Serialize;
use serde_json::Value;
use sqlx::FromRow;
use time::{OffsetDateTime, format_description::well_known::Rfc3339};
use uuid::Uuid;

use crate::{
	access::{self, ORG_PROJECT_ID},
	evidence::{
		ElfService, Error, EvidencePackRequest, EvidencePackResponse, EvidencePackSource, Result,
		pack::budget,
	},
	search,
};

/// Literal subjects supplied by the caller, independently of expected answers.
#[derive(Clone, Debug)]
pub struct EvidenceRecallRequest {
	/// Tenant boundary.
	pub tenant_id: String,
	/// Project boundary.
	pub project_id: String,
	/// Requesting agent.
	pub agent_id: String,
	/// Current source-read policy.
	pub read_profile: String,
	/// One to four literal names or identifiers. Matches do not merge identities.
	pub subjects: Vec<String>,
	/// Requested fact time, not a document creation cutoff.
	pub as_of: Option<OffsetDateTime>,
	/// Total serialized response budget, including candidates and source context.
	pub max_bytes: Option<usize>,
}

/// Source-diverse candidates from lexical and graph incidence retrieval.
#[derive(Debug, Serialize)]
pub struct EvidenceRecallResponse {
	/// Read contract identifier.
	pub schema: &'static str,
	#[serde(with = "crate::time_serde::option")]
	/// Requested fact time; late reports can still describe earlier facts.
	pub as_of: Option<OffsetDateTime>,
	/// Whether the bounded candidate list or selected-note budget was exceeded.
	pub truncated: bool,
	/// Selected candidates in source-diverse order.
	pub candidates: Vec<EvidenceRecallCandidate>,
	/// Sources resolved under current permissions. Completeness is not answer coverage.
	pub pack: EvidencePackResponse,
}
impl EvidenceRecallResponse {
	fn limit_bytes(&mut self, maximum: usize) -> Result<()> {
		while budget::serialized_size(self)? > maximum {
			self.truncated = true;

			if !self.pack.remove_last_entry() {
				return Err(Error::InvalidRequest {
					message: "Recall metadata does not fit max_bytes.".into(),
				});
			}

			let visible: HashSet<_> = self.pack.notes.iter().map(|n| n.note_id).collect();

			self.candidates.retain(|c| visible.contains(&c.note_id));
		}

		self.truncated |= !self.pack.complete;

		Ok(())
	}
}

/// A match explains navigation, not truth or entity equivalence.
#[derive(Debug, Serialize)]
pub struct EvidenceRecallCandidate {
	/// Readable note identity.
	pub note_id: Uuid,
	/// Literal subject appears in this derived note.
	pub lexical_match: bool,
	/// Distinct matching graph entity identities connected through readable facts.
	pub entity_ids: Vec<Uuid>,
}

#[derive(FromRow)]
struct Row {
	note_id: Uuid,
	source_ref: Value,
	lexical_match: bool,
	entity_ids: Vec<Uuid>,
}

impl ElfService {
	/// Supplement vector candidates through names and graph incidence without new model calls.
	pub async fn evidence_recall(
		&self,
		req: EvidenceRecallRequest,
	) -> Result<EvidenceRecallResponse> {
		let response_budget = budget::response_limit(req.max_bytes)?;

		if !(1..=4).contains(&req.subjects.len())
			|| req.subjects.iter().any(|s| s.trim().chars().count() < 2 || s.len() > 128)
		{
			return Err(Error::InvalidRequest {
				message: "Supply 1 to 4 literal subjects of 2 to 128 bytes.".into(),
			});
		}

		let subjects: Vec<String> = req.subjects.iter().map(|s| s.trim().to_lowercase()).collect();
		let scopes = search::resolve_read_profile_scopes(&self.cfg, &req.read_profile)?;
		let grants = access::load_shared_read_grants_with_org_shared(
			&self.db.pool,
			&req.tenant_id,
			&req.project_id,
			&req.agent_id,
			scopes.iter().any(|s| s == "org_shared"),
		)
		.await?;
		let grant_keys = access::shared_scope_key_strings(&grants);
		let (direct_sources, direct_complete) =
			self.recall_original_sources(&req, &scopes, &grant_keys, &subjects).await?;
		let rows = sqlx::query_as::<_, Row>(include_str!("recall.sql"))
			.bind(&req.tenant_id)
			.bind(&req.project_id)
			.bind(&req.agent_id)
			.bind(&scopes)
			.bind(&grant_keys)
			.bind(&subjects)
			.bind(ORG_PROJECT_ID)
			.fetch_all(&self.db.pool)
			.await?;
		let mut truncated = rows.len() > 128;
		let rows: Vec<_> = rows.into_iter().take(128).collect();
		let selected = select_source_diverse(&rows, 12);

		truncated |= selected.len() < rows.len();

		let candidates: Vec<_> = selected
			.iter()
			.map(|&i| EvidenceRecallCandidate {
				note_id: rows[i].note_id,
				lexical_match: rows[i].lexical_match,
				entity_ids: rows[i].entity_ids.clone(),
			})
			.collect();
		let mut pack = if candidates.is_empty() {
			EvidencePackResponse {
				schema: "elf.evidence_pack/v1",
				notes: vec![],
				sources: vec![],
				complete: true,
				source_bytes: 0,
				omitted_note_ids: vec![],
			}
		} else {
			self.evidence_pack(EvidencePackRequest {
				tenant_id: req.tenant_id,
				project_id: req.project_id,
				agent_id: req.agent_id,
				read_profile: req.read_profile,
				note_ids: candidates.iter().map(|c| c.note_id).collect(),
				max_source_bytes: None,
				max_bytes: req.max_bytes,
			})
			.await?
		};
		let mut sources = Vec::new();
		let mut seen = HashSet::new();
		let mut bytes = 0;

		pack.complete &= direct_complete;

		for source in direct_sources.into_iter().chain(pack.sources) {
			if !seen.insert(source.reference.clone()) {
				continue;
			}
			if bytes + source.text.len() > 32_768 {
				pack.complete = false;

				continue;
			}

			bytes += source.text.len();

			sources.push(source);
		}

		pack.source_bytes = bytes;
		pack.sources = sources;

		let included: HashSet<_> = pack.sources.iter().map(|s| s.reference.as_str()).collect();

		for note in &mut pack.notes {
			note.complete &= note.source_references.iter().all(|r| included.contains(r.as_str()));

			note.source_references.retain(|r| included.contains(r.as_str()));
		}

		// Stable chronological presentation does not infer validity from record timestamps.
		pack.sources.sort_by(|a, b| {
			record_time(a).cmp(&record_time(b)).then(a.reference.cmp(&b.reference))
		});

		let visible: HashSet<_> = pack.notes.iter().map(|n| n.note_id).collect();
		let candidates = candidates.into_iter().filter(|c| visible.contains(&c.note_id)).collect();
		let mut response = EvidenceRecallResponse {
			schema: "elf.evidence_recall/v1",
			as_of: req.as_of,
			truncated,
			candidates,
			pack,
		};

		response.limit_bytes(response_budget)?;

		Ok(response)
	}
}

fn record_time(source: &EvidencePackSource) -> Option<OffsetDateTime> {
	source.source_timestamp.as_deref().and_then(|raw| OffsetDateTime::parse(raw, &Rfc3339).ok())
}

fn source_ids(row: &Row) -> HashSet<String> {
	row.source_ref
		.get("evidence")
		.and_then(Value::as_array)
		.into_iter()
		.flatten()
		.filter_map(|entry| entry.pointer("/source/document/ref/doc_id").and_then(Value::as_str))
		.chain(row.source_ref.pointer("/ref/doc_id").and_then(Value::as_str))
		.map(str::to_string)
		.collect()
}

fn select_source_diverse(rows: &[Row], limit: usize) -> Vec<usize> {
	let mut selected = Vec::new();
	let mut covered = HashSet::new();

	for (i, row) in rows.iter().enumerate() {
		let ids = source_ids(row);

		if !ids.is_empty() && !ids.is_subset(&covered) {
			covered.extend(ids);
			selected.push(i);

			if selected.len() == limit {
				return selected;
			}
		}
	}
	for i in 0..rows.len() {
		if !selected.contains(&i) {
			selected.push(i);
		}
		if selected.len() == limit {
			break;
		}
	}

	selected
}

#[cfg(test)]
mod tests {
	use uuid::Uuid;

	use crate::evidence::recall::{self, Row};

	#[test]
	fn source_diversity_keeps_later_records_instead_of_duplicate_notes() {
		let rows: Vec<_> = (0..20).map(|i| Row {
            note_id: Uuid::new_v4(), lexical_match: true, entity_ids: vec![],
            source_ref: serde_json::json!({"evidence":[{"source":{"document":{"ref":{"doc_id":if i < 17 {"first"} else {"later"}}}}}]}),
        }).collect();

		assert_eq!(recall::select_source_diverse(&rows, 2), vec![0, 17]);
	}
}
