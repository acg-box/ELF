use crate::{
	Error, Result,
	structured_fields::{
		types::StructuredRelation,
		validation::{entity, quotes, text},
	},
};

pub(super) fn validate_structured_relation(
	relation: &StructuredRelation,
	note_text: &str,
	evidence_quotes: &[String],
	base: &str,
) -> Result<()> {
	if relation.predicate.is_none() {
		return Err(Error::InvalidRequest { message: format!("{base}.predicate is required.") });
	}

	let subject = relation
		.subject
		.as_ref()
		.ok_or_else(|| Error::InvalidRequest { message: format!("{base}.subject is required.") })?;

	entity::validate_structured_entity(subject, &format!("{base}.subject"), true)?;

	let predicate = relation.predicate.as_ref().ok_or_else(|| Error::InvalidRequest {
		message: format!("{base}.predicate is required."),
	})?;

	text::validate_text_field(predicate, &format!("{base}.predicate"))?;

	let object = relation
		.object
		.as_ref()
		.ok_or_else(|| Error::InvalidRequest { message: format!("{base}.object is required.") })?;

	match (&object.entity, object.value.as_ref()) {
		(Some(entity), None) => {
			entity::validate_structured_entity(entity, &format!("{base}.object.entity"), true)?;

			let canonical = entity.canonical.as_deref().ok_or_else(|| Error::InvalidRequest {
				message: format!("{base}.object.entity.canonical is required."),
			})?;

			if !quotes::fact_is_evidence_bound(canonical, note_text, evidence_quotes) {
				return Err(Error::InvalidRequest {
					message: format!(
						"{base}.object.entity.canonical is not supported by note text or evidence quotes."
					),
				});
			}
		},
		(None, Some(value)) => {
			text::validate_text_field(value, &format!("{base}.object.value"))?;

			if !quotes::fact_is_evidence_bound(value, note_text, evidence_quotes) {
				return Err(Error::InvalidRequest {
					message: format!(
						"{base}.object.value is not supported by note text or evidence quotes."
					),
				});
			}
		},
		(_, _) => {
			return Err(Error::InvalidRequest {
				message: format!("{base}.object must provide exactly one of entity or value."),
			});
		},
	}

	if !quotes::fact_is_evidence_bound(
		subject.canonical.as_deref().unwrap_or_default(),
		note_text,
		evidence_quotes,
	) {
		return Err(Error::InvalidRequest {
			message: format!(
				"{base}.subject.canonical is not supported by note text or evidence quotes."
			),
		});
	}

	if let Some(quote) = relation.evidence_quote.as_ref() {
		text::validate_text_field(quote, &format!("{base}.evidence_quote"))?;

		let subject = subject.canonical.as_deref().unwrap_or_default();
		let object = object
			.entity
			.as_ref()
			.and_then(|entity| entity.canonical.as_deref())
			.or(object.value.as_deref())
			.unwrap_or_default();

		if !evidence_quotes.iter().any(|source| source.contains(quote))
			|| !quote.contains(subject)
			|| !quote.contains(object)
		{
			return Err(Error::InvalidRequest {
				message: format!(
					"{base}.evidence_quote must be an original quote containing both edge endpoints."
				),
			});
		}
	} else if !quotes::fact_is_evidence_bound(predicate, note_text, evidence_quotes) {
		return Err(Error::InvalidRequest {
			message: format!("{base}.predicate is not supported by note text or evidence quotes."),
		});
	}
	if let (Some(valid_from), Some(valid_to)) = (relation.valid_from, relation.valid_to)
		&& valid_to <= valid_from
	{
		return Err(Error::InvalidRequest {
			message: format!("{base}.valid_to must be greater than valid_from."),
		});
	}

	Ok(())
}
