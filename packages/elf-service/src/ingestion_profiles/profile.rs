use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::{Error, Result, add_event};

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(super) struct IngestionProfileV1 {
	#[serde(default = "default_schema_version")]
	pub(super) schema_version: i32,

	pub(super) prompt_schema: Option<Value>,

	pub(super) prompt_system_template: Option<String>,

	pub(super) prompt_user_template: Option<String>,

	pub(super) model: Option<String>,

	pub(super) temperature: Option<f32>,

	pub(super) timeout_ms: Option<u64>,
}
impl IngestionProfileV1 {
	pub(super) fn with_defaults(self) -> Self {
		let defaults = builtin_profile();
		let mut merged = defaults;

		if self.schema_version != 0 {
			merged.schema_version = self.schema_version;
		}

		merged.prompt_schema = self.prompt_schema.or(merged.prompt_schema);
		merged.prompt_system_template =
			self.prompt_system_template.or(merged.prompt_system_template);
		merged.prompt_user_template = self.prompt_user_template.or(merged.prompt_user_template);
		merged.model = self.model.or(merged.model);
		merged.temperature = self.temperature.or(merged.temperature);
		merged.timeout_ms = self.timeout_ms.or(merged.timeout_ms);

		merged
	}
}

pub(super) fn parse_profile(profile: Value) -> Result<IngestionProfileV1> {
	let parsed = serde_json::from_value::<IngestionProfileV1>(profile.clone()).or_else(|_| {
		if profile.is_object() {
			Ok(IngestionProfileV1 {
				schema_version: 1,
				prompt_schema: Some(profile),
				prompt_system_template: None,
				prompt_user_template: None,
				model: None,
				temperature: None,
				timeout_ms: None,
			})
		} else {
			Err(Error::InvalidRequest {
				message: "Ingestion profile JSON has unsupported format.".to_string(),
			})
		}
	})?;

	Ok(parsed)
}

pub(super) fn builtin_profile() -> IngestionProfileV1 {
	IngestionProfileV1 {
		schema_version: 1,
		prompt_schema: Some(add_event::extraction_schema()),
		prompt_system_template: Some(
			"You are a memory extraction engine for an agent memory system. Output must be valid JSON only and must match the provided schema exactly. \
Extract at most MAX_NOTES high-signal, cross-session reusable memory notes from the given messages. \
Prefer concise English summaries, but preserve original names, identifiers, and quoted evidence in their source language. Never translate evidence quotes. \
The structured field is optional. If present, summary must be short, facts must be verbatim substrings of note text or evidence quotes, and concepts must be short phrases. \
For each relation, subject is directly an entity object with canonical, kind, and aliases; never wrap subject in another entity field. The object provides exactly one non-null entity or value. Subject canonical, predicate, and object canonical/value must occur verbatim in note text or an evidence quote. Omit optional relations when this cannot be satisfied. \
Preserve numbers, dates, percentages, currency amounts, tickers, URLs, and code snippets exactly. \
Never store secrets or PII: API keys, tokens, private keys, seed phrases, passwords, bank IDs, personal addresses. \
For every note, provide 1 to 2 evidence quotes copied verbatim from the input messages and include the message_index. \
If you cannot provide verbatim evidence, omit the note. \
If content is ephemeral or not useful long-term, return an empty notes array."
				.to_string(),
		),
		prompt_user_template: Some(
			"Return an instance matching this JSON Schema:\n{SCHEMA}\nConstraints:\n- MAX_NOTES = {MAX_NOTES}\n- MAX_NOTE_CHARS = {MAX_NOTE_CHARS}\nHere are the messages as JSON:\n{MESSAGES_JSON}"
				.to_string(),
		),
		model: None,
		temperature: None,
		timeout_ms: None,
	}
}

fn default_schema_version() -> i32 {
	1
}
