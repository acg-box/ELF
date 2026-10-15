use std::path::Path;

use crate::{
	REJECT_EVIDENCE_MISMATCH, REJECT_EVIDENCE_QUOTE_COUNT,
	add_event::{
		self,
		types::{AddEventRequest, EventMessage, EvidenceQuote, ExtractorOutput},
		validation,
	},
};

#[test]
fn accepts_long_french_message_content() {
	let req = AddEventRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "a".to_string(),
			scope: None,
			dry_run: None,
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".to_string(),
					content: "Bonjour, je veux m'assurer que ce texte est suffisamment long et riche en lettres pour declencher la detection de langue. Merci beaucoup."
						.to_string(),
					ts: None,
					msg_id: None,
					source_document: None,
					write_policy: None,
				}],
			};

	validation::validate_add_event_request(&req).expect("French text must be accepted.");
}

#[test]
fn malformed_extracted_entity_is_not_silently_discarded() {
	let output = serde_json::json!({"notes":[{"type":"fact","text":"Mara started Larch.",
        "structured":{"relations":[{"subject":{"entity":{"canonical":"Mara"}},
            "predicate":"started","object":{"entity":{"canonical":"Larch"}},"valid_from":"2026-08-01"}]}}]});
	let error = serde_json::from_value::<ExtractorOutput>(output)
		.expect_err("The old model response shape must not silently lose its subject");

	assert!(error.to_string().contains("unknown field `entity`"));
}

#[test]
fn extractor_schema_exposes_the_relation_time_contract() {
	let schema = add_event::extraction_schema();
	let description =
		schema["$defs"]["StructuredRelation"]["properties"]["valid_from"]["description"]
			.as_str()
			.expect("Date contract description");

	assert!(description.contains("YYYY-MM-DD"), "{description}");
}

#[test]
fn complete_quotes_can_cross_span_boundaries_but_must_match_originals() {
	let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../elf.example.toml");
	let mut cfg = elf_config::load(&path).expect("Example config");

	cfg.security.evidence_span_bytes = 6;

	let messages = vec!["中文测试".to_string()];
	let check = |quotes: &[EvidenceQuote]| {
		validation::reject_extracted_note_if_evidence_invalid(
			&cfg,
			None,
			quotes,
			&messages,
			&[false],
		)
	};

	assert_eq!(
		check(&[]).expect("Missing quotes").reason_code.as_deref(),
		Some(REJECT_EVIDENCE_QUOTE_COUNT)
	);
	assert!(
		check(&[EvidenceQuote { position: None, message_index: 0, quote: "中文".into() }])
			.is_none()
	);
	assert!(
		check(&[EvidenceQuote { position: None, message_index: 0, quote: "中文测试".into() }])
			.is_none()
	);
	assert!(
		check(&[
			EvidenceQuote { position: None, message_index: 0, quote: "中文".into() },
			EvidenceQuote { position: None, message_index: 0, quote: "文测".into() },
			EvidenceQuote { position: None, message_index: 0, quote: "测试".into() },
		])
		.is_none()
	);
	assert_eq!(
		check(&[EvidenceQuote { position: None, message_index: 0, quote: "not".into() }])
			.expect("Wrong quote")
			.reason_code
			.as_deref(),
		Some(REJECT_EVIDENCE_MISMATCH)
	);
	assert_eq!(messages[0], "中文测试");
}
