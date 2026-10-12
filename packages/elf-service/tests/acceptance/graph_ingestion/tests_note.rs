use time::{OffsetDateTime, format_description::well_known::Rfc3339};

use crate::acceptance::graph_ingestion::tests_helpers;
use elf_service::{
	AddNoteInput, AddNoteRequest, GraphQueryEntityRef, GraphQueryRequest, NoteOp,
	RelationTemporalStatus,
};

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn add_note_duplicate_fact_attaches_multiple_evidence() {
	let Some(test_db) =
		tests_helpers::build_test_db("add_note_duplicate_fact_attaches_multiple_evidence").await
	else {
		return;
	};
	let service = tests_helpers::build_hash_service(&test_db).await;

	tests_helpers::reset_service_db(&service).await;

	let response = service
		.add_note(tests_helpers::duplicate_fact_attaches_multiple_evidence_request())
		.await
		.expect("add_note failed.");

	assert_eq!(response.results.len(), 2);
	assert_eq!(response.results[0].op, NoteOp::Add);
	assert_eq!(response.results[1].op, NoteOp::Add);

	tests_helpers::assert_graph_policy_from_op(
		response.results[0].op,
		response.results[0].policy_decision,
	);
	tests_helpers::assert_graph_policy_from_op(
		response.results[1].op,
		response.results[1].policy_decision,
	);

	let first_note_id = response.results[0].note_id.expect("Expected note_id.");
	let second_note_id = response.results[1].note_id.expect("Expected note_id.");

	assert_ne!(first_note_id, second_note_id);

	let fact_id = tests_helpers::graph_fact_id(&service.db.pool).await;
	let fact_count = tests_helpers::graph_fact_count(&service.db.pool).await;
	let evidence_count = tests_helpers::graph_fact_evidence_count(&service.db.pool, fact_id).await;

	assert_eq!(fact_count, 1);
	assert_eq!(evidence_count, 2);

	let first_evidence_count =
		tests_helpers::graph_fact_evidence_count_for_note(&service.db.pool, fact_id, first_note_id)
			.await;
	let second_evidence_count = tests_helpers::graph_fact_evidence_count_for_note(
		&service.db.pool,
		fact_id,
		second_note_id,
	)
	.await;

	assert_eq!(first_evidence_count, 1);
	assert_eq!(second_evidence_count, 1);

	test_db.cleanup().await.expect("Failed to cleanup test database.");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn add_note_invalid_relation_rejected_has_field_path() {
	let Some(test_db) =
		tests_helpers::build_test_db("add_note_invalid_relation_rejected_has_field_path").await
	else {
		return;
	};
	let service = tests_helpers::build_stub_service(&test_db).await;
	let response = service
		.add_note(AddNoteRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "a".to_string(),
			scope: "agent_private".to_string(),
			notes: vec![AddNoteInput {
				r#type: "fact".to_string(),
				key: Some("mentorship".to_string()),
				text: "Alice mentors Bob.".to_string(),
				structured: Some(
					serde_json::from_value::<elf_service::structured_fields::StructuredFields>(
						serde_json::json!({
							"relations": [{
								"subject": { "canonical": "Alice" },
								"object": { "value": "Bob" }
							}]
						}),
					)
					.expect("Failed to build structured fields."),
				),
				importance: 0.8,
				confidence: 0.9,
				ttl_days: None,
				source_ref: serde_json::json!({}),
				write_policy: None,
			}],
		})
		.await
		.expect("add_note failed.");

	assert_eq!(response.results.len(), 1);
	assert_eq!(response.results[0].op, NoteOp::Rejected);
	assert_eq!(response.results[0].reason_code.as_deref(), Some("REJECT_STRUCTURED_INVALID"));
	assert_eq!(
		response.results[0].field_path,
		Some("structured.relations[0].predicate".to_string()),
	);

	test_db.cleanup().await.expect("Failed to cleanup test database.");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn add_note_persists_graph_relations() {
	let Some(test_db) = tests_helpers::build_test_db("add_note_persists_graph_relations").await
	else {
		return;
	};
	let service = tests_helpers::build_stub_service(&test_db).await;

	tests_helpers::reset_service_db(&service).await;

	let response = service
		.add_note(AddNoteRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "a".to_string(),
			scope: "agent_private".to_string(),
			notes: vec![AddNoteInput {
				r#type: "fact".to_string(),
				key: Some("mentorship".to_string()),
				text: "Alice mentors Bob.".to_string(),
				structured: Some(
					serde_json::from_value::<elf_service::structured_fields::StructuredFields>(
						serde_json::json!({
								"relations": [{
									"subject": { "canonical": "Alice" },
									"predicate": "mentors",
									"object": { "value": "Bob" }
							}]
						}),
					)
					.expect("Failed to build structured fields."),
				),
				importance: 0.8,
				confidence: 0.9,
				ttl_days: None,
				source_ref: serde_json::json!({}),
				write_policy: None,
			}],
		})
		.await
		.expect("add_note failed.");

	assert_eq!(response.results.len(), 1);
	assert_eq!(response.results[0].op, NoteOp::Add);

	tests_helpers::assert_graph_policy_from_op(
		response.results[0].op,
		response.results[0].policy_decision,
	);

	let note_id = response.results[0].note_id.expect("Expected note_id.");
	let fact_id = tests_helpers::graph_fact_id(&service.db.pool).await;
	let fact_count = tests_helpers::graph_fact_count(&service.db.pool).await;
	let evidence_count =
		tests_helpers::graph_fact_evidence_count_for_note(&service.db.pool, fact_id, note_id).await;

	assert_eq!(fact_count, 1);
	assert_eq!(evidence_count, 1);

	test_db.cleanup().await.expect("Failed to cleanup test database.");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn graph_preserves_unknown_time_and_reuses_declared_aliases() {
	let db = tests_helpers::build_test_db("graph_identity_time").await.expect("Database required.");
	let service = tests_helpers::build_stub_service(&db).await;

	for (name, aliases, target) in [
		("Cobalt", vec!["project Cobalt"], "incident Z"),
		("project Cobalt", vec![], "procedure Y"),
	] {
		let text = format!("Cobalt (project Cobalt) uses {target}.");

		service.add_note(AddNoteRequest {tenant_id:"t".into(),project_id:"p".into(),agent_id:"a".into(),scope:"agent_private".into(),notes:vec![AddNoteInput {
            r#type:"fact".into(),key:None,text:text.clone(),importance:0.8,confidence:0.9,ttl_days:None,write_policy:None,source_ref:serde_json::json!({"quote":text}),
            structured:Some(serde_json::from_value(serde_json::json!({"relations":[{"subject":{"canonical":name,"kind":"project","aliases":aliases},"predicate":"uses","object":{"entity":{"canonical":target}}}]})).expect("Evidence integrity fixture must succeed.")),
        }]}).await.expect("Store graph evidence.");
	}

	let result = service
		.graph_query(GraphQueryRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			read_profile: "private_only".into(),
			subject: GraphQueryEntityRef::Surface { surface: "project Cobalt".into() },
			predicate: None,
			scopes: None,
			as_of: Some(
				OffsetDateTime::parse("2026-08-22T00:00:00Z", &Rfc3339)
					.expect("Evidence integrity fixture must succeed."),
			),
			limit: None,
			explain: None,
		})
		.await
		.expect("Read unknown-time candidates.");

	assert_eq!(result.facts.len(), 2);
	assert!(result.facts.iter().all(|f| f.valid_from.is_none() && f.temporal_status == RelationTemporalStatus::Unknown));

	let count: i64 = sqlx::query_scalar(
		"SELECT count(*) FROM graph_entities WHERE canonical IN ('Cobalt','project Cobalt')",
	)
	.fetch_one(&service.db.pool)
	.await
	.expect("Evidence integrity fixture must succeed.");

	assert_eq!(count, 1);

	db.cleanup().await.expect("Clean fixture.");
}
