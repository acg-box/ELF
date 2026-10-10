pub(super) use elf_domain::text_validation::find_invalid_path;

use crate::structured_fields::StructuredFields;
use elf_domain::text_validation;

pub(super) fn find_invalid_path_in_structured(
	structured: Option<&StructuredFields>,
	base: &str,
) -> Option<String> {
	let structured = structured?;

	if let Some(summary) = structured.summary.as_ref()
		&& !text_validation::is_valid_text(summary)
	{
		return Some(format!("{base}.summary"));
	}
	if let Some(items) = structured.facts.as_ref() {
		for (idx, item) in items.iter().enumerate() {
			if !text_validation::is_valid_text(item) {
				return Some(format!("{base}.facts[{idx}]"));
			}
		}
	}
	if let Some(items) = structured.concepts.as_ref() {
		for (idx, item) in items.iter().enumerate() {
			if !text_validation::is_valid_text(item) {
				return Some(format!("{base}.concepts[{idx}]"));
			}
		}
	}
	if let Some(items) = structured.entities.as_ref() {
		for (idx, entity) in items.iter().enumerate() {
			let base = format!("{base}.entities[{idx}]");

			if let Some(canonical) = entity.canonical.as_ref()
				&& !text_validation::is_valid_text(canonical)
			{
				return Some(format!("{base}.canonical"));
			}
			if let Some(kind) = entity.kind.as_ref()
				&& !text_validation::is_valid_text(kind)
			{
				return Some(format!("{base}.kind"));
			}
			if let Some(aliases) = entity.aliases.as_ref() {
				for (alias_idx, alias) in aliases.iter().enumerate() {
					if !text_validation::is_valid_text(alias) {
						return Some(format!("{base}.aliases[{alias_idx}]"));
					}
				}
			}
		}
	}
	if let Some(items) = structured.relations.as_ref() {
		for (idx, relation) in items.iter().enumerate() {
			let base = format!("{base}.relations[{idx}]");

			if let Some(subject) = relation.subject.as_ref() {
				let subject_base = format!("{base}.subject");

				if let Some(canonical) = subject.canonical.as_ref()
					&& !text_validation::is_valid_text(canonical)
				{
					return Some(format!("{subject_base}.canonical"));
				}
				if let Some(kind) = subject.kind.as_ref()
					&& !text_validation::is_valid_text(kind)
				{
					return Some(format!("{subject_base}.kind"));
				}
				if let Some(aliases) = subject.aliases.as_ref() {
					for (alias_idx, alias) in aliases.iter().enumerate() {
						if !text_validation::is_valid_text(alias) {
							return Some(format!("{subject_base}.aliases[{alias_idx}]"));
						}
					}
				}
			}
			if let Some(predicate) = relation.predicate.as_ref()
				&& !text_validation::is_valid_text(predicate)
			{
				return Some(format!("{base}.predicate"));
			}
			if let Some(object) = relation.object.as_ref() {
				if let Some(entity) = object.entity.as_ref() {
					let object_base = format!("{base}.object.entity");

					if let Some(canonical) = entity.canonical.as_ref()
						&& !text_validation::is_valid_text(canonical)
					{
						return Some(format!("{object_base}.canonical"));
					}
					if let Some(kind) = entity.kind.as_ref()
						&& !text_validation::is_valid_text(kind)
					{
						return Some(format!("{object_base}.kind"));
					}
					if let Some(aliases) = entity.aliases.as_ref() {
						for (alias_idx, alias) in aliases.iter().enumerate() {
							if !text_validation::is_valid_text(alias) {
								return Some(format!("{object_base}.aliases[{alias_idx}]"));
							}
						}
					}
				}
				if let Some(value) = object.value.as_ref()
					&& !text_validation::is_valid_text(value)
				{
					return Some(format!("{base}.object.value"));
				}
			}
		}
	}

	None
}

#[cfg(test)] mod tests;
