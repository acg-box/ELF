use std::collections::HashSet;

use serde::Deserialize;
use serde_json::Value;
use uuid::Uuid;

use crate::{
	docs::{DocsExcerptsGetRequest, DocsGetRequest, TextPositionSelector},
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
		let scopes = search::resolve_read_profile_scopes(&self.cfg, &read_profile)?;
		let note = self.get_note(req.clone()).await?;

		if !scopes.contains(&note.scope) {
			return Err(Error::NotFound { message: "Note not found in the read profile.".into() });
		}

		let entries = note.source_ref.get("evidence").and_then(Value::as_array);
		let pointers: Vec<&Value> = if let Some(entries) = entries {
			entries.iter().map(|entry| &entry["source"]["document"]).collect()
		} else {
			vec![&note.source_ref]
		};
		let mut seen = HashSet::new();
		let mut sources = Vec::new();
		let mut complete = !pointers.is_empty();
		let mut reads = 0;

		for value in pointers {
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
			);

			if !seen.insert(key) {
				continue;
			}
			if reads == MAX_SOURCES {
				complete = false;

				continue;
			}

			reads += 1;

			let fetched = self.resolve_note_source(&req, &read_profile, pointer).await;

			match fetched {
				Ok(source) => sources.push(source),
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

		let excerpt = self
			.docs_excerpts_get(DocsExcerptsGetRequest {
				tenant_id: req.tenant_id.clone(),
				project_id: req.project_id.clone(),
				agent_id: req.agent_id.clone(),
				read_profile: read_profile.into(),
				doc_id,
				level: "L2".into(),
				chunk_id: None,
				quote: None,
				position: Some(pointer.locator.position),
				explain: Some(false),
			})
			.await?;

		if !excerpt.verification.verified
			|| excerpt.verification.content_hash != metadata.content_hash
		{
			return Err(Error::InvalidRequest {
				message: "Source excerpt verification failed.".into(),
			});
		}

		Ok(NoteSourceEvidence { metadata, excerpt })
	}
}
