use serde_json::Value;

use crate::acceptance::text_boundary::setup;
use elf_service::{
	AddEventRequest, AdminIngestionProfileDefaultGetRequest,
	AdminIngestionProfileDefaultSetRequest, EventMessage,
};

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
				source_document: None,
				write_policy: None,
			}],
		})
		.await
		.expect("Extract and persist Chinese evidence");

	assert_eq!(result.ingestion_profile.expect("Versioned profile").version, 7);
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

	let origin = &source["evidence"][0]["source"];

	assert_eq!(origin["message_id"], "原文-1");
	assert_eq!(origin["role"], "user");
	assert_eq!(origin["timestamp"], "2026-10-01T00:00:00Z");
	assert_eq!(origin["content_hash"], blake3::hash(text.as_bytes()).to_hex().to_string());
	assert_eq!(origin["extraction_content_hash"], origin["content_hash"]);
	assert_eq!(origin["write_policy_audit"], serde_json::Value::Null);

	fixture.test_db.cleanup().await.expect("Cleanup database");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn new_builtin_profile_preserves_existing_versions_and_pins() {
	let fixture =
		setup::setup_service("versioned_profile_upgrade").await.expect("Fixture required.");
	let legacy = serde_json::json!({"schema_version":1,"prompt_system_template":"Pinned legacy instructions"});

	sqlx::query("INSERT INTO memory_ingestion_profiles (tenant_id,project_id,pipeline,profile_id,version,profile) VALUES ('t','p','add_event','default',6,$1)")
        .bind(&legacy).execute(&fixture.service.db.pool).await.expect("Seed legacy profile.");

	fixture
		.service
		.admin_ingestion_profile_default_set(AdminIngestionProfileDefaultSetRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			profile_id: "default".into(),
			version: Some(6),
		})
		.await
		.expect("Pin legacy default.");

	let selected = fixture
		.service
		.admin_ingestion_profile_default_get(AdminIngestionProfileDefaultGetRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
		})
		.await
		.expect("Seed the new builtin without moving the pin.");

	assert_eq!(selected.version, Some(6));

	let profiles: Vec<(i32, Value)> = sqlx::query_as("SELECT version,profile FROM memory_ingestion_profiles WHERE tenant_id='t' AND project_id='p' ORDER BY version")
        .fetch_all(&fixture.service.db.pool).await.expect("Read immutable versions.");

	assert_eq!(profiles.len(), 2);
	assert_eq!(profiles[0], (6, legacy));
	assert_eq!(profiles[1].0, 7);
	assert_ne!(profiles[1].1, profiles[0].1);

	let activated = fixture
		.service
		.admin_ingestion_profile_default_set(AdminIngestionProfileDefaultSetRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			profile_id: "default".into(),
			version: Some(7),
		})
		.await
		.expect("Explicitly activate the new guidance.");

	assert_eq!(activated.version, Some(7));

	fixture.test_db.cleanup().await.expect("Clean profile fixture.");
}
