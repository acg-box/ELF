use std::collections::HashSet;

use serde::Deserialize;
use serde_json::Value;
use uuid::Uuid;

use crate::{
	docs::{
		DEFAULT_L2_MAX_BYTES, DocsExcerptsGetRequest, DocsGetRequest, TextPositionSelector,
		TextQuoteSelector,
	},
	evidence::{
		ElfService, Error, MAX_SOURCES, NoteEvidenceResponse, NoteFetchRequest, NoteSourceEvidence,
		Result,
	},
	search,
};

#[derive(Deserialize)]
struct Pointer {
	resolver: String,
	#[serde(rename = "ref")]
	reference: Reference,
	state: State,
	locator: Locator,
}
#[derive(Deserialize)]
struct Reference {
	doc_id: Uuid,
}
#[derive(Deserialize)]
struct State {
	content_hash: String,
}
#[derive(Deserialize)]
struct Locator {
	position: TextPositionSelector,
}

impl ElfService {
	/// Expand supported note pointers through Source Library, with no model calls.
	pub async fn note_evidence(
		&self,
		req: NoteFetchRequest,
		read_profile: String,
	) -> Result<NoteEvidenceResponse> {
		self.note_evidence_bounded(req, read_profile, None).await
	}

	pub(super) async fn note_evidence_bounded(
		&self,
		req: NoteFetchRequest,
		read_profile: String,
		source_budget: Option<usize>,
	) -> Result<NoteEvidenceResponse> {
		let scopes = search::resolve_read_profile_scopes(&self.cfg, &read_profile)?;
		let note = self.get_note(req.clone()).await?;

		if !scopes.contains(&note.scope) {
			return Err(Error::NotFound { message: "Note not found in the read profile.".into() });
		}

		let entries = note.source_ref.get("evidence").and_then(Value::as_array);
		let pointers: Vec<(&Value, Option<&str>)> = if let Some(entries) = entries {
			entries
				.iter()
				.map(|entry| (&entry["source"]["document"], entry["quote"].as_str()))
				.collect()
		} else {
			vec![(&note.source_ref, None)]
		};
		let window_bytes = source_budget
			.map(|budget| (budget / pointers.len().clamp(1, MAX_SOURCES)).max(1))
			.unwrap_or(DEFAULT_L2_MAX_BYTES);
		let mut seen = HashSet::new();
		let mut sources: Vec<NoteSourceEvidence> = Vec::new();
		let mut complete = !pointers.is_empty();
		let mut reads = 0;

		for (value, quote) in pointers {
			let Ok(pointer) = serde_json::from_value::<Pointer>(value.clone()) else {
				complete = false;

				continue;
			};

			if pointer.resolver != "elf_doc_ext/v1" {
				complete = false;

				continue;
			}

			let key = (
				pointer.reference.doc_id,
				pointer.locator.position.start,
				pointer.locator.position.end,
				pointer.state.content_hash.clone(),
				quote.map(str::to_string),
			);

			if !seen.insert(key) {
				continue;
			}
			if reads == MAX_SOURCES {
				complete = false;

				continue;
			}

			reads += 1;

			let fetched =
				self.resolve_note_source(&req, &read_profile, pointer, quote, window_bytes).await;

			match fetched {
				Ok(source) => {
					if !sources.iter().any(|prior| {
						prior.metadata.doc_id == source.metadata.doc_id
							&& prior.metadata.content_hash == source.metadata.content_hash
							&& prior.excerpt.start_offset == source.excerpt.start_offset
							&& prior.excerpt.end_offset == source.excerpt.end_offset
					}) {
						sources.push(source);
					}
				},
				Err(
					Error::NotFound { .. }
					| Error::InvalidRequest { .. }
					| Error::ScopeDenied { .. },
				) => complete = false,
				Err(error) => return Err(error),
			}
		}

		Ok(NoteEvidenceResponse { note, sources, complete })
	}

	async fn resolve_note_source(
		&self,
		req: &NoteFetchRequest,
		read_profile: &str,
		pointer: Pointer,
		evidence_quote: Option<&str>,
		window_bytes: usize,
	) -> Result<NoteSourceEvidence> {
		let doc_id = pointer.reference.doc_id;
		let metadata = self
			.docs_get(DocsGetRequest {
				tenant_id: req.tenant_id.clone(),
				project_id: req.project_id.clone(),
				agent_id: req.agent_id.clone(),
				read_profile: read_profile.into(),
				doc_id,
			})
			.await?;

		if metadata.content_hash != pointer.state.content_hash {
			return Err(Error::InvalidRequest { message: "Source pointer hash mismatch.".into() });
		}

		let span = &pointer.locator.position;
		let use_quote = span.end.saturating_sub(span.start) > window_bytes;

		if use_quote && evidence_quote.is_none_or(|quote| quote.trim().is_empty()) {
			return Err(Error::InvalidRequest {
				message: "A large source span requires a nonempty evidence quote.".into(),
			});
		}

		let quote_selector = if use_quote {
			evidence_quote.map(|quote| TextQuoteSelector {
				exact: quote.into(),
				prefix: None,
				suffix: None,
			})
		} else {
			None
		};
		let excerpt = self
			.docs_excerpts_get_bounded(
				DocsExcerptsGetRequest {
					tenant_id: req.tenant_id.clone(),
					project_id: req.project_id.clone(),
					agent_id: req.agent_id.clone(),
					read_profile: read_profile.into(),
					doc_id,
					level: "L2".into(),
					max_bytes: None,
					chunk_id: None,
					quote: quote_selector,
					position: if use_quote { None } else { Some(span.clone()) },
					explain: Some(false),
				},
				window_bytes,
			)
			.await?;

		if !excerpt.verification.verified
			|| excerpt.verification.content_hash != metadata.content_hash
			|| evidence_quote.is_some_and(|quote| !excerpt.excerpt.contains(quote))
			|| excerpt.locator.match_start_offset < span.start
			|| excerpt.locator.match_end_offset > span.end
		{
			return Err(Error::InvalidRequest {
				message: "Source excerpt verification failed.".into(),
			});
		}

		Ok(NoteSourceEvidence { metadata, excerpt })
	}
}
