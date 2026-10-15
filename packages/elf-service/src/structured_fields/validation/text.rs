use crate::{Error, Result};
use elf_domain::text_validation;

pub(super) fn validate_text_field(value: &str, label: &str) -> Result<()> {
	let trimmed = value.trim();

	if trimmed.is_empty() {
		return Err(Error::InvalidRequest { message: format!("{label} must not be empty.") });
	}
	if !text_validation::is_valid_text(trimmed) {
		return Err(Error::InvalidText { field: label.to_string() });
	}

	Ok(())
}

pub(super) fn validate_required_text_field(value: Option<&String>, label: &str) -> Result<()> {
	let Some(value) = value else {
		return Err(Error::InvalidRequest { message: format!("{label} is required.") });
	};

	validate_text_field(value, label)
}
