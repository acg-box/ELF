use serde_json::Value;

use crate::acceptance::graph_ingestion::tests_helpers;
use elf_service::{
	AddEventRequest, DocsPutRequest, EventMessage, EventSourceDocument, NoteOp,
	TextPositionSelector, evidence::EvidenceRecallRequest,
};
use elf_storage::graph;

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn add_event_persists_graph_relations() {
	let Some(test_db) = tests_helpers::build_test_db("add_event_persists_graph_relations").await
	else {
		return;
	};
	let extractor_payload = serde_json::json!({
		"notes": [{
			"type": "fact",
			"key": "mentorship",
			"text": "Alice mentors Bob.",
			"structured": {
				"relations": [{
					"subject": { "canonical": "Alice" },
					"predicate": "mentors",
					"object": { "value": "Bob" }
				}]
			},
			"importance": 0.8,
			"confidence": 0.9,
			"ttl_days": null,
			"scope_suggestion": "agent_private",
			"evidence": [{ "message_index": 0, "quote": "Alice mentors Bob." }],
			"reason": "test"
		}]
	});
	let service =
		tests_helpers::build_service_with_extractor_payload(&test_db, extractor_payload).await;

	tests_helpers::reset_service_db(&service).await;

	let response = service
		.add_event(AddEventRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "a".to_string(),
			scope: Some("agent_private".to_string()),
			dry_run: Some(false),
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".to_string(),
				content: "Alice mentors Bob.".to_string(),
				ts: None,
				msg_id: None,
				source_document: None,
				write_policy: None,
			}],
		})
		.await
		.expect("add_event failed.");

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
async fn extracted_keys_cannot_overwrite_distinct_subjects() {
	let test_db = tests_helpers::build_test_db("extracted_key_authority")
		.await
		.expect("Database is required.");
	let mut identities = Vec::new();

	for text in ["Project Alpha uses RETRY-A.", "Project Beta uses RETRY-B."] {
		let payload = serde_json::json!({"notes":[{
			"type":"fact", "key":"retry_policy.version", "text":text,
			"importance":0.8,"confidence":0.9,
			"structured":{"facts":[text]},
			"evidence":[{"message_index":0,"quote":text}]
		}]});
		let service = tests_helpers::build_service_with_extractor_payload(&test_db, payload).await;
		let request = AddEventRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: Some("agent_private".into()),
			dry_run: Some(false),
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".into(),
				content: text.into(),
				ts: None,
				msg_id: Some(text.into()),
				source_document: None,
				write_policy: None,
			}],
		};
		let result = service.add_event(request.clone()).await.expect("Store extracted fact.");

		assert_eq!(result.results[0].op, NoteOp::Add);

		let id = result.results[0].note_id.expect("Persisted identity.");

		identities.push(id);

		let (stored, key, hint): (String, Option<String>, Option<String>) = sqlx::query_as(
			"SELECT text,key,source_ref->>'extracted_key' FROM memory_notes WHERE note_id=$1",
		)
		.bind(id)
		.fetch_one(&service.db.pool)
		.await
		.expect("Read memory identity.");

		assert_eq!(stored, text);
		assert_eq!(key, None);
		assert_eq!(hint.as_deref(), Some("retry_policy.version"));

		let duplicate = service.add_event(request).await.expect("Repeat extraction.");

		assert_eq!(duplicate.results[0].op, NoteOp::None);
		assert_eq!(duplicate.results[0].note_id, Some(id));
	}

	assert_ne!(identities[0], identities[1]);

	test_db.cleanup().await.expect("Cleanup database.");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn event_source_occurrences_link_exact_original_documents() {
	let db = tests_helpers::build_test_db("source_occurrences").await.expect("Database required.");
	let quote = "No change was approved.";
	let payload = serde_json::json!({"notes":[{"type":"decision","text":quote,"importance":0.8,"confidence":0.9,"evidence":[{"message_index":0,"quote":quote}]}]});
	let service = tests_helpers::build_service_with_extractor_payload(&db, payload).await;
	let mut ids = Vec::new();

	for project in ["Alpha", "Beta"] {
		let content = format!("项目 {project}: {quote}");
		let doc = service.docs_put(DocsPutRequest {
            tenant_id:"t".into(),project_id:"p".into(),agent_id:"a".into(),scope:"agent_private".into(),doc_type:None,title:None,write_policy:None,
            source_ref:serde_json::json!({"schema":"doc_source_ref/v1","doc_type":"knowledge","origin":project,"ts":"2026-08-08T00:00:00Z"}),content:content.clone(),
        }).await.expect("Archive original.");
		let request = AddEventRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: Some("agent_private".into()),
			dry_run: Some(false),
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".into(),
				content: content.clone(),
				ts: Some("2026-08-08".into()),
				msg_id: Some(project.into()),
				write_policy: None,
				source_document: Some(EventSourceDocument {
					doc_id: doc.doc_id,
					content_hash: doc.content_hash.clone(),
					position: TextPositionSelector { start: 0, end: content.len() },
				}),
			}],
		};
		let result = service.add_event(request.clone()).await.expect("Bind source occurrence.");
		let id = result.results[0].note_id.expect("Persisted note.");

		assert_eq!(result.results[0].op, NoteOp::Add);

		ids.push(id);

		let retry = service.add_event(request.clone()).await.expect("Retry same occurrence.");

		assert_eq!(retry.results[0].op, NoteOp::None);
		assert_eq!(retry.results[0].note_id, Some(id));

		let source: Value =
			sqlx::query_scalar("SELECT source_ref FROM memory_notes WHERE note_id=$1")
				.bind(id)
				.fetch_one(&service.db.pool)
				.await
				.expect("Read provenance.");

		assert_eq!(
			source["evidence"][0]["source"]["document"]["ref"]["doc_id"],
			doc.doc_id.to_string()
		);

		let (bytes, hash): (String, String) =
			sqlx::query_as("SELECT content,content_hash FROM doc_documents WHERE doc_id=$1")
				.bind(doc.doc_id)
				.fetch_one(&service.db.pool)
				.await
				.expect("Read source.");

		assert_eq!((bytes, hash), (content, doc.content_hash));

		let mut wrong = request.clone();

		wrong.messages[0]
			.source_document
			.as_mut()
			.expect("Evidence integrity fixture must succeed.")
			.content_hash = "wrong".into();

		assert!(service.add_event(wrong).await.is_err());

		let mut wrong = request.clone();

		wrong.messages[0]
			.source_document
			.as_mut()
			.expect("Evidence integrity fixture must succeed.")
			.position
			.end -= 1;

		assert!(service.add_event(wrong).await.is_err());

		let mut wrong = request.clone();

		wrong.agent_id = "another-agent".into();

		assert!(service.add_event(wrong).await.is_err());

		let mut wrong = request;

		wrong.scope = Some("project_shared".into());

		assert!(service.add_event(wrong).await.is_err());
	}

	assert_ne!(ids[0], ids[1]);

	db.cleanup().await.expect("Clean fixture.");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn extracted_shared_alias_does_not_merge_distinct_canonical_identities() {
	let db =
		tests_helpers::build_test_db("extracted_alias_authority").await.expect("Database required");
	let payload = serde_json::json!({"notes":[
		{"type":"fact","text":"North Atlas uses account ACCT-N.","importance":0.8,"confidence":0.9,"evidence":[{"message_index":0,"quote":"North Atlas uses account ACCT-N."}],"structured":{"entities":[{"canonical":"ACCT-N","aliases":["Atlas"]}]}},
		{"type":"fact","text":"South Atlas uses account ACCT-S.","importance":0.8,"confidence":0.9,"evidence":[{"message_index":0,"quote":"South Atlas uses account ACCT-S."}],"structured":{"entities":[{"canonical":"ACCT-S","aliases":["Atlas"]}]}}
	]});
	let service = tests_helpers::build_service_with_extractor_payload(&db, payload).await;
	let result = service
		.add_event(AddEventRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: Some("agent_private".into()),
			dry_run: Some(false),
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".into(),
				content: "North Atlas uses account ACCT-N. South Atlas uses account ACCT-S.".into(),
				ts: None,
				msg_id: Some("accounts".into()),
				source_document: None,
				write_policy: None,
			}],
		})
		.await
		.expect("Retain distinct entities");

	assert!(result.results.iter().all(|r| r.op == NoteOp::Add));

	let count: i64 = sqlx::query_scalar(
		"SELECT count(*) FROM graph_entities WHERE canonical IN ('ACCT-N','ACCT-S')",
	)
	.fetch_one(&service.db.pool)
	.await
	.expect("Two canonical identities");

	assert_eq!(count, 2);

	let mut conn = service.db.pool.acquire().await.expect("Connection");

	assert!(
		graph::resolve_entity_by_surface(&mut conn, "t", "p", "Atlas")
			.await
			.expect("Extracted aliases cannot resolve identity")
			.is_none()
	);

	let recalled = service
		.evidence_recall(EvidenceRecallRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			read_profile: "private_only".into(),
			subjects: vec!["Atlas".into()],
			as_of: None,
		})
		.await
		.expect("Ambiguous names return separate evidence candidates");

	assert_eq!(recalled.candidates.len(), 2);
	assert_eq!(recalled.pack.notes.len(), 2);
	assert_ne!(recalled.candidates[0].note_id, recalled.candidates[1].note_id);

	drop(conn);

	db.cleanup().await.expect("Clean fixture");
}
