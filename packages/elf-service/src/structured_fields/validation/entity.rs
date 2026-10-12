use std::iter;

use crate::{
	Error, Result,
	structured_fields::{
		types::{StructuredEntity, StructuredFields},
		validation::{
			bounds::{self, MAX_ALIASES},
			text,
		},
	},
};
use elf_storage::graph;

pub(super) fn validate_structured_entity(
	entity: &StructuredEntity,
	base: &str,
	require_canonical: bool,
) -> Result<()> {
	if require_canonical {
		text::validate_required_text_field(
			entity.canonical.as_ref(),
			&format!("{base}.canonical"),
		)?;
	}

	if let Some(kind) = entity.kind.as_ref() {
		text::validate_text_field(kind, &format!("{base}.kind"))?;
	}
	if let Some(aliases) = entity.aliases.as_ref() {
		bounds::validate_list_field_count(aliases.len(), MAX_ALIASES, &format!("{base}.aliases"))?;

		for (alias_idx, alias) in aliases.iter().enumerate() {
			text::validate_text_field(alias, &format!("{base}.aliases[{alias_idx}]"))?;
		}
	}

	Ok(())
}

// Alias identity follows the same case and whitespace normalization as lookup.
// Original quotes and facts keep their separate verbatim validation.
pub(super) fn validate_extracted_aliases(
	structured: &StructuredFields,
	note_text: &str,
	evidence_quotes: &[String],
) -> Result<()> {
	let evidence: Vec<String> = iter::once(note_text)
		.chain(evidence_quotes.iter().map(String::as_str))
		.map(graph::normalize_entity_name)
		.collect();
	let entities = structured.entities.iter().flatten().chain(
		structured.relations.iter().flatten().flat_map(|relation| {
			relation
				.subject
				.iter()
				.chain(relation.object.iter().filter_map(|object| object.entity.as_ref()))
		}),
	);

	for entity in entities {
		if entity.entity_id.is_some() {
			return Err(Error::InvalidRequest {
				message: "Automatic extraction cannot assign caller-owned entity identities."
					.into(),
			});
		}

		for alias in entity.aliases.iter().flatten() {
			let surface = graph::normalize_entity_name(alias);

			if !evidence.iter().any(|text| text.contains(&surface)) {
				return Err(Error::InvalidRequest {
					message: "structured.entities aliases require note or source evidence.".into(),
				});
			}
		}
	}

	Ok(())
}
