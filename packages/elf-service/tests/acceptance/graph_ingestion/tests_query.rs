use crate::acceptance::graph_ingestion::tests_helpers::{
	self, TEST_PROJECT, TEST_SCOPE, TEST_TENANT,
};
use elf_service::{
	DeleteRequest, ElfService, GraphQueryEntityRef, GraphQueryPredicateRef, GraphQueryRequest,
	NoteOp, evidence::EvidenceRecallRequest,
};
use elf_storage::graph::{self, AliasAuthority};

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn graph_query_suppresses_deleted_evidence_notes() {
	let Some(test_db) =
		tests_helpers::build_test_db("graph_query_suppresses_deleted_evidence_notes").await
	else {
		return;
	};
	let service = tests_helpers::build_stub_service(&test_db).await;

	tests_helpers::reset_service_db(&service).await;

	let note_id = tests_helpers::add_fact_note(
		&service,
		"mentorship",
		"Alice mentors Bob.",
		"mentors",
		"Bob",
	)
	.await;
	let before_delete = service
		.graph_query(GraphQueryRequest {
			tenant_id: TEST_TENANT.to_string(),
			project_id: TEST_PROJECT.to_string(),
			agent_id: "a".to_string(),
			read_profile: "private_only".to_string(),
			subject: GraphQueryEntityRef::Surface { surface: "Alice".to_string() },
			predicate: Some(GraphQueryPredicateRef::Surface { surface: "mentors".to_string() }),
			scopes: Some(vec![TEST_SCOPE.to_string()]),
			as_of: None,
			limit: Some(10),
			explain: Some(true),
		})
		.await
		.expect("graph query before delete should succeed");

	assert_eq!(before_delete.facts.len(), 1);
	assert_eq!(before_delete.facts[0].evidence_note_ids, vec![note_id]);

	verify_historical_and_incoming_recall(&service).await;

	let delete = service
		.delete(DeleteRequest {
			tenant_id: TEST_TENANT.to_string(),
			project_id: TEST_PROJECT.to_string(),
			agent_id: "a".to_string(),
			note_id,
		})
		.await
		.expect("note delete should succeed");

	assert_eq!(delete.op, NoteOp::Delete);

	let after_delete = service
		.graph_query(GraphQueryRequest {
			tenant_id: TEST_TENANT.to_string(),
			project_id: TEST_PROJECT.to_string(),
			agent_id: "a".to_string(),
			read_profile: "private_only".to_string(),
			subject: GraphQueryEntityRef::Surface { surface: "Alice".to_string() },
			predicate: Some(GraphQueryPredicateRef::Surface { surface: "mentors".to_string() }),
			scopes: Some(vec![TEST_SCOPE.to_string()]),
			as_of: Some(time::macros::datetime!(2_020-08-01 00:00 UTC)),
			limit: Some(10),
			explain: Some(true),
		})
		.await
		.expect("graph query after delete should succeed");

	assert!(
		after_delete.facts.is_empty(),
		"graph facts without active readable evidence notes must be suppressed"
	);

	test_db.cleanup().await.expect("Failed to cleanup test database.");
}

async fn verify_historical_and_incoming_recall(service: &ElfService) {
	sqlx::query(
		"UPDATE graph_facts SET valid_from='2020-01-01T00:00:00Z', valid_to='2021-01-01T00:00:00Z'",
	)
	.execute(&service.db.pool)
	.await
	.expect("Set historical validity");

	let historical = service
		.graph_query(GraphQueryRequest {
			tenant_id: TEST_TENANT.into(),
			project_id: TEST_PROJECT.into(),
			agent_id: "a".into(),
			read_profile: "private_only".into(),
			subject: GraphQueryEntityRef::Surface { surface: "Alice".into() },
			predicate: None,
			scopes: None,
			as_of: Some(time::macros::datetime!(2_020-08-01 00:00 UTC)),
			limit: None,
			explain: None,
		})
		.await
		.expect("Read historical state");

	assert_eq!(historical.facts.len(), 1);
	assert_eq!(
		historical.facts[0].temporal_status,
		elf_service::graph::RelationTemporalStatus::Current
	);

	let recalled = service
		.evidence_recall(EvidenceRecallRequest {
			tenant_id: TEST_TENANT.into(),
			project_id: TEST_PROJECT.into(),
			agent_id: "a".into(),
			read_profile: "private_only".into(),
			subjects: vec!["Alice".into()],
			as_of: None,
		})
		.await
		.expect("Discover historical graph evidence");

	assert_eq!(recalled.candidates.len(), 1);
	assert_eq!(recalled.candidates[0].entity_ids.len(), 1);

	let mut conn = service.db.pool.acquire().await.expect("Graph fixture connection");
	let bob = graph::upsert_entity(&mut conn, TEST_TENANT, TEST_PROJECT, "Bob", None)
		.await
		.expect("Object entity");

	graph::upsert_entity_alias(&mut conn, bob, "Robert", AliasAuthority::Caller)
		.await
		.expect("Object alias");
	sqlx::query("UPDATE graph_facts SET object_entity_id=$1, object_value=NULL")
		.bind(bob)
		.execute(&mut *conn)
		.await
		.expect("Link object");

	let alice = graph::resolve_entity_by_canonical(&mut conn, TEST_TENANT, TEST_PROJECT, "Alice")
		.await
		.expect("Resolve Alice")
		.expect("Existing subject");

	graph::upsert_entity_alias(&mut conn, alice.entity_id, "Robert", AliasAuthority::Caller)
		.await
		.expect("Ambiguous alias");

	drop(conn);

	let incoming = service
		.evidence_recall(EvidenceRecallRequest {
			tenant_id: TEST_TENANT.into(),
			project_id: TEST_PROJECT.into(),
			agent_id: "a".into(),
			read_profile: "private_only".into(),
			subjects: vec!["Robert".into()],
			as_of: None,
		})
		.await
		.expect("Incoming historical alias evidence");

	assert!(incoming.candidates[0].entity_ids.contains(&bob));
	assert!(incoming.candidates[0].entity_ids.contains(&alice.entity_id));
	assert_eq!(incoming.candidates[0].entity_ids.len(), 2);
	assert!(!incoming.candidates[0].lexical_match);
}
