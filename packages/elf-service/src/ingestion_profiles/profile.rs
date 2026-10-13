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
Make each note understandable and retrievable without the surrounding conversation. Preserve the explicit subject, project or system, and identifiers that distinguish it from similar facts. Resolve pronouns only from the supplied messages; do not invent missing context. Keep a recovery action together with its incident, affected system, and outcome when the input connects them. \
An optional key is only a descriptive hint, not authority to replace an existing memory. Include its subject and use null when the identity is uncertain. \
Prefer concise English summaries, but preserve original names, identifiers, and quoted evidence in their source language. Never translate evidence quotes. \
The structured field is optional. If present, summary must be short, facts must be verbatim substrings of note text or evidence quotes, and concepts must be short phrases. \
For each relation, subject is directly an entity object with canonical, kind, and aliases; never wrap subject in another entity field. The object provides exactly one non-null entity or value. Subject and object must occur verbatim in a source evidence quote. Include evidence_quote for every relation: copy a source passage containing both endpoints. Predicates may be concise normalized relationship labels; they are candidate interpretations, not certified facts. Omit relations without direct source support. \
Prefer an explicit source identifier as canonical when names are shared across projects or people. Keep each note subject and scope explicit, including account or division identifiers when present. Never treat a missing appointment as an unassigned role; preserve explicit negatives, unresolved contradictions, and future proposals. Combine related facts when necessary to fit MAX_NOTES without dropping these distinctions. Keep a named entity canonical consistent across notes. Use explicit source-backed alternate names as aliases, not separate entities. Use entity objects for linkable identifiers such as systems, incidents, and procedures; scalar values are for literals. Extract each explicitly stated step of a relation chain, but do not invent missing edges or infer equivalence merely from co-occurrence. \
Set relation valid_from/valid_to only when the source establishes effective dates. Distinguish approval dates, event dates, and observation dates; leave unknown validity null rather than using the message or ingestion timestamp. \
Preserve numbers, dates, percentages, currency amounts, tickers, URLs, and code snippets exactly. \
Never store secrets or PII: API keys, tokens, private keys, seed phrases, passwords, bank IDs, personal addresses. \
For every note, select supporting evidence_spans supplied with each message: output message_index and span_id. The server fills the exact original quote; do not copy or rewrite its text. Select the fewest spans that support the claim, including its subject and effective time where stated. Legacy quote objects are accepted only when copied exactly, including whitespace. If a note cannot fit, narrow the claim rather than dropping its subject or qualifications. \
If no supplied evidence span supports a claim, omit the note. \
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
