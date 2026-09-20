//! Validate request text before any recall operation.

use crate::{
	Error, GraphQueryEntityRef, GraphQueryPredicateRef, Result, context_pack::ContextPackRequest,
};
use elf_domain::english_gate;

pub(super) fn validate_context_pack_request(req: &ContextPackRequest) -> Result<()> {
	validate_required_english("task", req.task.as_str())?;
	validate_optional_english("title", req.title.as_deref())?;
	validate_optional_english("description", req.description.as_deref())?;
	validate_optional_english("query", req.query.as_deref())?;
	validate_optional_english("docs_query", req.docs_query.as_deref())?;
	validate_optional_english("knowledge_query", req.knowledge_query.as_deref())?;
	validate_graph_entity_ref("graph_subject", req.graph_subject.as_ref())?;
	validate_graph_predicate_ref("graph_predicate", req.graph_predicate.as_ref())?;

	Ok(())
}

fn validate_required_english(field: &str, value: &str) -> Result<()> {
	let trimmed = value.trim();

	if trimmed.is_empty() {
		return Err(Error::InvalidRequest { message: format!("{field} must be non-empty.") });
	}
	if !english_gate::is_english_natural_language(trimmed) {
		return Err(Error::NonEnglishInput { field: format!("$.{field}") });
	}

	Ok(())
}

fn validate_optional_english(field: &str, value: Option<&str>) -> Result<()> {
	if let Some(value) = value.map(str::trim).filter(|value| !value.is_empty())
		&& !english_gate::is_english_natural_language(value)
	{
		return Err(Error::NonEnglishInput { field: format!("$.{field}") });
	}

	Ok(())
}

fn validate_graph_entity_ref(field: &str, value: Option<&GraphQueryEntityRef>) -> Result<()> {
	if let Some(GraphQueryEntityRef::Surface { surface }) = value {
		validate_identifier_english(format!("$.{field}.surface"), surface.as_str())?;
	}

	Ok(())
}

fn validate_graph_predicate_ref(field: &str, value: Option<&GraphQueryPredicateRef>) -> Result<()> {
	if let Some(GraphQueryPredicateRef::Surface { surface }) = value {
		validate_identifier_english(format!("$.{field}.surface"), surface.as_str())?;
	}

	Ok(())
}

fn validate_identifier_english(field: String, value: &str) -> Result<()> {
	if !english_gate::is_english_identifier(value.trim()) {
		return Err(Error::NonEnglishInput { field });
	}

	Ok(())
}
