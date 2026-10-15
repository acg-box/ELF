use serde::{Deserialize, Serialize};
use serde_json::Value;
use time::OffsetDateTime;

use crate::{Error, Result};
use elf_config::{Config, LlmProviderConfig};

/// Selector for an ingestion profile and optional version.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct IngestionProfileSelector {
	/// Profile identifier.
	pub id: String,
	/// Optional explicit version.
	pub version: Option<i32>,
}

/// Resolved ingestion-profile reference.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct IngestionProfileRef {
	/// Profile identifier.
	pub id: String,
	/// Resolved version.
	pub version: i32,
}

/// Request payload for creating an ingestion profile version.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct AdminIngestionProfileCreateRequest {
	/// Tenant that owns the profile.
	pub tenant_id: String,
	/// Project that owns the profile.
	pub project_id: String,
	/// Profile identifier.
	pub profile_id: String,
	/// Optional explicit version number.
	pub version: Option<i32>,
	/// JSON profile payload.
	pub profile: Value,
	/// Actor creating the profile version.
	pub created_by: String,
}

/// Request payload for listing ingestion profiles.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct AdminIngestionProfileListRequest {
	/// Tenant that owns the profiles.
	pub tenant_id: String,
	/// Project that owns the profiles.
	pub project_id: String,
}

/// Request payload for fetching one ingestion profile.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct AdminIngestionProfileGetRequest {
	/// Tenant that owns the profile.
	pub tenant_id: String,
	/// Project that owns the profile.
	pub project_id: String,
	/// Profile identifier.
	pub profile_id: String,
	/// Optional explicit version.
	pub version: Option<i32>,
}

/// Request payload for listing all versions of one ingestion profile.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct AdminIngestionProfileVersionsListRequest {
	/// Tenant that owns the profile.
	pub tenant_id: String,
	/// Project that owns the profile.
	pub project_id: String,
	/// Profile identifier.
	pub profile_id: String,
}

/// Request payload for reading the default ingestion profile pointer.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct AdminIngestionProfileDefaultGetRequest {
	/// Tenant that owns the default pointer.
	pub tenant_id: String,
	/// Project that owns the default pointer.
	pub project_id: String,
}

/// Request payload for updating the default ingestion profile pointer.
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct AdminIngestionProfileDefaultSetRequest {
	/// Tenant that owns the default pointer.
	pub tenant_id: String,
	/// Project that owns the default pointer.
	pub project_id: String,
	/// Profile identifier to make default.
	pub profile_id: String,
	/// Optional explicit version to make default.
	pub version: Option<i32>,
}

/// Response payload for one ingestion profile version.
#[derive(Clone, Debug, Serialize)]
pub struct AdminIngestionProfileResponse {
	/// Profile identifier.
	pub profile_id: String,
	/// Profile version.
	pub version: i32,
	/// JSON profile payload.
	pub profile: Value,
	#[serde(with = "crate::time_serde")]
	/// Creation timestamp.
	pub created_at: OffsetDateTime,
	/// Actor that created the version.
	pub created_by: String,
}

/// Summary row for an ingestion profile version.
#[derive(Clone, Debug, Serialize)]
pub struct AdminIngestionProfileSummary {
	/// Profile identifier.
	pub profile_id: String,
	/// Profile version.
	pub version: i32,
	#[serde(with = "crate::time_serde")]
	/// Creation timestamp.
	pub created_at: OffsetDateTime,
	/// Actor that created the version.
	pub created_by: String,
}

/// Response payload for listing ingestion profiles.
#[derive(Clone, Debug, Serialize)]
pub struct AdminIngestionProfilesListResponse {
	/// Returned profile summaries.
	pub profiles: Vec<AdminIngestionProfileSummary>,
}

/// Response payload for listing versions of one ingestion profile.
#[derive(Clone, Debug, Serialize)]
pub struct AdminIngestionProfileVersionsListResponse {
	/// Returned profile-version summaries.
	pub profiles: Vec<AdminIngestionProfileSummary>,
}

/// Response payload for reading the default ingestion profile pointer.
#[derive(Clone, Debug, Serialize)]
pub struct AdminIngestionProfileDefaultResponse {
	/// Default profile identifier.
	pub profile_id: String,
	/// Default profile version, when pinned.
	pub version: Option<i32>,
	#[serde(with = "crate::time_serde")]
	/// Last update timestamp for the default pointer.
	pub updated_at: OffsetDateTime,
}

#[derive(Clone, Debug)]
pub(crate) struct ResolvedIngestionProfile {
	pub profile_ref: IngestionProfileRef,
	pub prompt_schema: Value,
	pub prompt_system: String,
	pub prompt_user_template: String,
	pub model: Option<String>,
	pub temperature: Option<f32>,
	pub timeout_ms: Option<u64>,
}
impl ResolvedIngestionProfile {
	pub(crate) fn build_extractor_messages(
		&self,
		messages_json: &str,
		cfg: &Config,
	) -> Result<Vec<Value>> {
		let mut schema = self.prompt_schema.clone();

		// Preview and old count settings must not become semantic admission rules.
		if let Some(notes) = schema.pointer_mut("/properties/notes").and_then(Value::as_object_mut)
		{
			notes.remove("maxItems");
		}
		if let Some(text) = schema
			.pointer_mut("/$defs/ExtractedNote/properties/text")
			.and_then(Value::as_object_mut)
		{
			text.remove("maxLength");
		}
		if let Some(evidence) = schema
			.pointer_mut("/$defs/ExtractedNote/properties/evidence")
			.and_then(Value::as_object_mut)
		{
			evidence.insert("minItems".into(), cfg.security.evidence_min_quotes.max(1).into());
			evidence.remove("maxItems");
		}

		let limits = format!(
			"Runtime processing budget: {} serialized UTF-8 bytes shared by extraction input and complete candidate objects. Return complete independent claims with all supporting source ranges. There is no per-note character or quote maximum. The service explicitly reports candidates it cannot process within the overall budget. Do not truncate or merge unrelated claims to fit. Do not change originals or guess byte offsets.",
			cfg.memory.ingest_max_bytes,
		);
		let schema = serde_json::to_string(&schema).map_err(|_| Error::InvalidRequest {
			message: "Failed to serialize ingestion profile schema.".to_string(),
		})?;
		let user_prompt = self
			.prompt_user_template
			.replace("{SCHEMA}", &schema)
			.replace("{MAX_NOTES}", "the request processing budget")
			.replace("{MAX_NOTE_CHARS}", "no per-note character maximum")
			.replace("{MESSAGES_JSON}", messages_json);

		Ok(vec![
			serde_json::json!({ "role": "system", "content": format!("{}\n\n{}", self.prompt_system, limits) }),
			serde_json::json!({ "role": "user", "content": user_prompt }),
		])
	}

	pub(crate) fn resolved_llm_config(&self, base: &LlmProviderConfig) -> LlmProviderConfig {
		LlmProviderConfig {
			provider_id: base.provider_id.clone(),
			api_base: base.api_base.clone(),
			api_key: base.api_key.clone(),
			path: base.path.clone(),
			model: self.model.clone().unwrap_or_else(|| base.model.clone()),
			temperature: self.temperature.unwrap_or(base.temperature),
			timeout_ms: self.timeout_ms.unwrap_or(base.timeout_ms),
			default_headers: base.default_headers.clone(),
		}
	}
}

#[cfg(test)]
mod tests {
	use serde_json::Value;

	use crate::{
		add_event,
		ingestion_profiles::types::{IngestionProfileRef, ResolvedIngestionProfile},
	};

	#[test]
	fn runtime_limits_reach_custom_prompts_without_mutating_profile() {
		let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../elf.example.toml");
		let mut cfg = elf_config::load(&path).expect("Example config");

		cfg.memory.preview_max_chars = 123;
		cfg.memory.ingest_max_bytes = 12_345;

		let profile = ResolvedIngestionProfile {
			profile_ref: IngestionProfileRef { id: "custom".into(), version: 1 },
			prompt_schema: add_event::extraction_schema(),
			prompt_system: "Custom instructions".into(),
			prompt_user_template: "{SCHEMA}\n{MESSAGES_JSON}".into(),
			model: None,
			temperature: None,
			timeout_ms: None,
		};
		let before = profile.prompt_schema.clone();
		let messages = profile.build_extractor_messages("[]", &cfg).expect("Runtime prompt");
		let system = messages[0]["content"].as_str().expect("System prompt");

		assert!(system.contains("12345 serialized UTF-8 bytes"));
		assert!(!system.contains("123 Unicode characters"));

		let user = messages[1]["content"].as_str().expect("User prompt");
		let schema: Value =
			serde_json::from_str(user.split('\n').next().expect("Schema")).expect("Valid schema");

		assert!(schema["$defs"]["ExtractedNote"]["properties"]["text"].get("maxLength").is_none());
		assert!(
			schema["$defs"]["ExtractedNote"]["properties"]["evidence"].get("maxItems").is_none()
		);
		assert!(schema["properties"]["notes"].get("maxItems").is_none());
		assert_eq!(profile.prompt_schema, before);
	}
}
