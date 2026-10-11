//! LLM extraction-provider client helpers.

use std::time::Duration;

use reqwest::Client;
use serde_json::Value;

use crate::{Error, Result};
use elf_config::LlmProviderConfig;

/// Calls the configured extractor provider and returns parsed JSON content.
pub async fn extract(cfg: &LlmProviderConfig, messages: &[Value]) -> Result<Value> {
	let client = Client::builder().timeout(Duration::from_millis(cfg.timeout_ms)).build()?;
	let url = format!("{}{}", cfg.api_base, cfg.path);

	for _ in 0..3 {
		let body = serde_json::json!({
			"model": cfg.model,
			"temperature": cfg.temperature,
			"messages": messages,
		});
		let res = client
			.post(&url)
			.headers(crate::auth_headers(&cfg.api_key, &cfg.default_headers)?)
			.json(&body)
			.send()
			.await?;
		let json: Value = res.error_for_status()?.json().await?;

		if let Ok(parsed) = parse_extractor_json(json) {
			return Ok(parsed);
		}
	}

	Err(Error::InvalidResponse { message: "Extractor response is not valid JSON.".to_string() })
}

fn parse_extractor_json(json: Value) -> Result<Value> {
	if json.pointer("/choices/0/finish_reason").and_then(Value::as_str) == Some("error") {
		return Err(Error::InvalidResponse {
			message: "Extractor completion failed upstream.".to_string(),
		});
	}

	if let Some(content) = json
		.get("choices")
		.and_then(|v| v.as_array())
		.and_then(|arr| arr.first())
		.and_then(|choice| choice.get("message"))
		.and_then(|msg| msg.get("content"))
		.and_then(|c| c.as_str())
	{
		let parsed: Value = serde_json::from_str(content).map_err(|_| Error::InvalidResponse {
			message: "Extractor content is not valid JSON.".to_string(),
		})?;

		return Ok(parsed);
	}

	// A provider envelope with no content is not a direct extraction object.
	// Returning it would bypass the bounded parse retry and misclassify an
	// upstream error as an invalid memory request.
	if json.get("choices").is_some() {
		return Err(Error::InvalidResponse {
			message: "Extractor response is missing completion content.".to_string(),
		});
	}
	if json.is_object() {
		return Ok(json);
	}

	Err(Error::InvalidResponse {
		message: "Extractor response is missing JSON content.".to_string(),
	})
}

#[cfg(test)]
mod tests {
	use crate::extractor;

	#[test]
	fn rejects_failed_completion_envelope_instead_of_returning_it_as_memory() {
		let json = serde_json::json!({"choices":[{"finish_reason":"error","error":{"code":502},"message":{"content":null}}]});

		assert!(extractor::parse_extractor_json(json).is_err());
		assert!(extractor::parse_extractor_json(serde_json::json!({"choices":[]})).is_err());
	}

	#[test]
	fn accepts_direct_extraction_objects() {
		let json = serde_json::json!({"notes":[]});

		assert_eq!(extractor::parse_extractor_json(json.clone()).expect("Direct JSON"), json);
	}

	#[test]
	fn parses_choice_content_json() {
		let json = serde_json::json!({
			"choices": [
				{ "message": { "content": "{\"notes\": []}" } }
			]
		});
		let parsed = extractor::parse_extractor_json(json).expect("parse failed");

		assert!(parsed.get("notes").is_some());
	}
}
