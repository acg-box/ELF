use crate::docs::validation::{
	DEFAULT_L0_MAX_BYTES, DEFAULT_L1_MAX_BYTES, DEFAULT_L2_MAX_BYTES, DEFAULT_MAX_CHUNKS_PER_DOC,
	DocChunkingProfile, DocType, Error, Result, TextQuoteSelector, text_validation,
};

pub(in crate::docs) fn resolve_doc_chunking_profile(doc_type: DocType) -> DocChunkingProfile {
	match doc_type {
		DocType::Chat | DocType::Search => DocChunkingProfile {
			max_tokens: 1_024,
			overlap_tokens: 128,
			max_chunks: DEFAULT_MAX_CHUNKS_PER_DOC,
		},
		DocType::Knowledge | DocType::Dev => DocChunkingProfile {
			max_tokens: 2_048,
			overlap_tokens: 256,
			max_chunks: DEFAULT_MAX_CHUNKS_PER_DOC,
		},
	}
}

pub(in crate::docs) fn validate_docs_excerpts_get(
	tenant_id: &str,
	project_id: &str,
	agent_id: &str,
	read_profile: &str,
	quote: Option<&TextQuoteSelector>,
) -> Result<()> {
	if tenant_id.is_empty()
		|| project_id.is_empty()
		|| agent_id.is_empty()
		|| read_profile.is_empty()
	{
		return Err(Error::InvalidRequest {
			message: "tenant_id, project_id, agent_id, and read_profile are required.".to_string(),
		});
	}

	if let Some(quote) = quote {
		validate_quote_selector_text(quote)?;
	}

	Ok(())
}

pub(in crate::docs) fn validate_quote_selector_text(quote: &TextQuoteSelector) -> Result<()> {
	if !text_validation::is_valid_text(quote.exact.as_str()) {
		return Err(Error::InvalidText { field: "$.quote.exact".to_string() });
	}

	if let Some(prefix) = quote.prefix.as_ref()
		&& !text_validation::is_valid_text(prefix.as_str())
	{
		return Err(Error::InvalidText { field: "$.quote.prefix".to_string() });
	}
	if let Some(suffix) = quote.suffix.as_ref()
		&& !text_validation::is_valid_text(suffix.as_str())
	{
		return Err(Error::InvalidText { field: "$.quote.suffix".to_string() });
	}

	Ok(())
}

pub(in crate::docs) fn excerpt_level_max(level: &str) -> Result<usize> {
	match level {
		"L0" => Ok(DEFAULT_L0_MAX_BYTES),
		"L1" => Ok(DEFAULT_L1_MAX_BYTES),
		"L2" => Ok(DEFAULT_L2_MAX_BYTES),
		_ => Err(Error::InvalidRequest { message: "level must be L0, L1, or L2.".to_string() }),
	}
}
