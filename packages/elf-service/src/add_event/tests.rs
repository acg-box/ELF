use crate::add_event::{
	types::{AddEventRequest, EventMessage, ExtractorOutput},
	validation,
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
	let schema = crate::add_event::extraction_schema();
	let description =
		schema["$defs"]["StructuredRelation"]["properties"]["valid_from"]["description"]
			.as_str()
			.expect("Date contract description");

	assert!(description.contains("YYYY-MM-DD"), "{description}");
}
