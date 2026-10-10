//! Validate request text before any recall operation.

use crate::{
	Error, GraphQueryEntityRef, GraphQueryPredicateRef, Result, context_pack::ContextPackRequest,
};
use elf_domain::text_validation;

pub(super) fn validate_context_pack_request(req: &ContextPackRequest) -> Result<()> {
	validate_required_text("task", req.task.as_str())?;
	validate_optional_text("title", req.title.as_deref())?;
	validate_optional_text("description", req.description.as_deref())?;
	validate_optional_text("query", req.query.as_deref())?;
	validate_optional_text("docs_query", req.docs_query.as_deref())?;
	validate_optional_text("knowledge_query", req.knowledge_query.as_deref())?;
	validate_graph_entity_ref("graph_subject", req.graph_subject.as_ref())?;
	validate_graph_predicate_ref("graph_predicate", req.graph_predicate.as_ref())?;

	Ok(())
}

fn validate_required_text(field: &str, value: &str) -> Result<()> {
	let trimmed = value.trim();

	if trimmed.is_empty() {
		return Err(Error::InvalidRequest { message: format!("{field} must be non-empty.") });
	}
	if !text_validation::is_valid_text(trimmed) {
		return Err(Error::InvalidText { field: format!("$.{field}") });
	}

	Ok(())
}

fn validate_optional_text(field: &str, value: Option<&str>) -> Result<()> {
	if let Some(value) = value.map(str::trim).filter(|value| !value.is_empty())
		&& !text_validation::is_valid_text(value)
	{
		return Err(Error::InvalidText { field: format!("$.{field}") });
	}

	Ok(())
}

fn validate_graph_entity_ref(field: &str, value: Option<&GraphQueryEntityRef>) -> Result<()> {
	if let Some(GraphQueryEntityRef::Surface { surface }) = value {
		validate_identifier_text(format!("$.{field}.surface"), surface.as_str())?;
	}

	Ok(())
}

fn validate_graph_predicate_ref(field: &str, value: Option<&GraphQueryPredicateRef>) -> Result<()> {
	if let Some(GraphQueryPredicateRef::Surface { surface }) = value {
		validate_identifier_text(format!("$.{field}.surface"), surface.as_str())?;
	}

	Ok(())
}

fn validate_identifier_text(field: String, value: &str) -> Result<()> {
	if !text_validation::is_valid_identifier(value.trim()) {
		return Err(Error::InvalidText { field });
	}

	Ok(())
}
