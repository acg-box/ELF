use serde_json::Value;

use crate::acceptance::text_boundary::setup;
use elf_service::{AddEventRequest, EventMessage};

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn chinese_evidence_and_date_only_relations_survive_native_extraction() {
	let text = "项目甲的负责人是王明，生效日期为2026-10-01。";
	let payload = serde_json::json!({"notes":[{
		"type":"fact","text":text,"importance":0.8,"confidence":0.9,
		"evidence":[{"message_index":0,"quote":text}],
		"structured":{"relations":[{"subject":{"canonical":"项目甲"},"predicate":"负责人",
			"object":{"entity":{"canonical":"王明"}},"valid_from":"2026-10-01"}]}
	}]});
	let Some(fixture) = setup::setup_service_with_payload("multilingual_extraction", payload).await
	else {
		return;
	};
	let result = fixture
		.service
		.add_event(AddEventRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "a".to_string(),
			scope: Some("agent_private".to_string()),
			dry_run: Some(false),
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".to_string(),
				content: text.to_string(),
				ts: Some("2026-10-01T00:00:00Z".to_string()),
				msg_id: Some("原文-1".to_string()),
				write_policy: None,
			}],
		})
		.await
		.expect("Extract and persist Chinese evidence");

	assert_eq!(result.ingestion_profile.expect("Versioned profile").version, 2);
	assert_eq!(
		result.extracted["notes"][0]["structured"]["relations"][0]["valid_from"],
		"2026-10-01T00:00:00Z"
	);
	assert_eq!(result.extracted["notes"][0]["evidence"][0]["quote"], text);

	let id = result.results[0].note_id.expect("Native note must be stored");
	let (stored, source): (String, Value) =
		sqlx::query_as("SELECT text, source_ref FROM memory_notes WHERE note_id=$1")
			.bind(id)
			.fetch_one(&fixture.service.db.pool)
			.await
			.expect("Read stored note");

	assert_eq!(stored, text);
	assert!(source.to_string().contains(text));

	fixture.test_db.cleanup().await.expect("Cleanup database");
}
