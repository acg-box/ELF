use std::sync::atomic::Ordering;

use crate::acceptance::text_boundary::setup;
use elf_service::{
	AddEventRequest, AddEventResponse, AddNoteInput, AddNoteRequest, DocsPutRequest, ElfService,
	EventMessage, EventSourceDocument, NoteFetchRequest, NoteOp,
	docs::TextPositionSelector,
	evidence::{EvidencePackRequest, EvidenceRecallRequest},
};

const OLD_REJECTED: &str = "ELF’s shared MCP/HTTP evidence contract is version 5: the authorized host writes selected exact user messages, assistant records, and receipts, then ingests those same bytes with the returned document hash/span. Work Journal alone does not create searchable memory. Fresh-session calibration requires reading a nonempty memory pack with linked originals, citing a relevant original in the final answer, and passing the native binding check; bindings prove accessible original bytes, not semantic truth or memory benefit.";

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn complete_memories_keep_long_conditions_and_every_candidate() {
	assert_eq!(OLD_REJECTED.chars().count(), 520);

	let qualified = format!(
		"{}仅在2026年10月15日之后且财务批准时，项目甲可以使用新额度。",
		"项目甲保留原文并记录其来源。".repeat(40)
	);
	let texts = [
		OLD_REJECTED,
		qualified.as_str(),
		"Project B has an independent budget owner.",
		"Project C keeps its previous approval condition.",
	];
	let content = texts.join("\n");
	let payload = serde_json::json!({"notes":texts.iter().map(|text| serde_json::json!({
		"type":"fact","text":text,"importance":0.8,"confidence":0.9,
		"evidence":[{"message_index":0,"quote":text}]
	})).collect::<Vec<_>>()});
	let Some(fixture) = setup::setup_service_with_payload("complete_memory", payload).await else {
		return;
	};
	let service = &fixture.service;
	let doc = service
		.docs_put(DocsPutRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: "agent_private".into(),
			doc_type: None,
			title: None,
			write_policy: None,
			source_ref: serde_json::json!({"schema":"doc_source_ref/v1","doc_type":"knowledge","ts":"2026-10-15T00:00:00Z"}),
			content: content.clone(),
		})
		.await
		.expect("Capture unchanged original");
	let event = service
		.add_event(AddEventRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: Some("agent_private".into()),
			dry_run: None,
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".into(),
				content: content.clone(),
				ts: None,
				msg_id: None,
				write_policy: None,
				source_document: Some(EventSourceDocument {
					doc_id: doc.doc_id,
					content_hash: doc.content_hash.clone(),
					position: TextPositionSelector { start: 0, end: content.len() },
				}),
			}],
		})
		.await
		.expect("Ingest all candidates");

	assert!(event.processing_complete);
	assert_eq!(event.results.len(), 4);
	assert_eq!(event.extracted["notes"].as_array().expect("Candidates").len(), 4);

	for (result, text) in event.results.iter().zip(texts) {
		assert_eq!(result.op, NoteOp::Add);

		let evidence = service
			.note_evidence(
				NoteFetchRequest {
					tenant_id: "t".into(),
					project_id: "p".into(),
					agent_id: "a".into(),
					note_id: result.note_id.expect("Note"),
				},
				"private_only".into(),
			)
			.await
			.expect("Read exact note and original");

		assert_eq!(evidence.note.text, text);
		assert!(evidence.sources.iter().any(|source| source.excerpt.excerpt.contains(text)));
		assert!(
			evidence.sources.iter().all(|source| source.metadata.content_hash == doc.content_hash)
		);
	}

	verify_read_budget(service, &event, &texts).await;

	let stored: String = sqlx::query_scalar("SELECT content FROM doc_documents WHERE doc_id=$1")
		.bind(doc.doc_id)
		.fetch_one(&service.db.pool)
		.await
		.expect("Read immutable original");

	assert_eq!(stored, content);

	fixture.test_db.cleanup().await.expect("Clean fixture");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn aggregate_ingest_budget_defers_whole_candidates_and_prevents_large_model_input() {
	let Some(mut fixture) = setup::setup_service("ingest_budget").await else { return };
	let note = AddNoteInput {
		r#type: "fact".into(),
		key: None,
		text: OLD_REJECTED.into(),
		structured: None,
		importance: 0.8,
		confidence: 0.9,
		ttl_days: None,
		source_ref: serde_json::json!({}),
		write_policy: None,
	};

	fixture.service.cfg.memory.ingest_max_bytes =
		serde_json::to_vec(&note).expect("Candidate bytes").len() as u32;

	let result = fixture
		.service
		.add_note(AddNoteRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: "agent_private".into(),
			notes: vec![note.clone(), note],
		})
		.await
		.expect("Explicit partial batch");

	assert!(!result.processing_complete);
	assert_eq!(result.results.len(), 2);
	assert_eq!(result.results[0].op, NoteOp::Add);
	assert_eq!(result.results[1].op, NoteOp::None);
	assert_eq!(result.results[1].reason_code.as_deref(), Some("DEFERRED_INGEST_BUDGET"));
	assert!(result.results[1].note_id.is_none());

	let counts: (i64, i64) = sqlx::query_as(
		"SELECT (SELECT count(*) FROM memory_notes), (SELECT count(*) FROM indexing_outbox)",
	)
	.fetch_one(&fixture.service.db.pool)
	.await
	.expect("Only admitted data is queued");

	assert_eq!(counts, (1, 1));

	let response = fixture
		.service
		.add_event(AddEventRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: Some("agent_private".into()),
			dry_run: None,
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".into(),
				content: OLD_REJECTED.into(),
				ts: None,
				msg_id: None,
				source_document: None,
				write_policy: None,
			}],
		})
		.await;

	assert!(
		response
			.expect_err("Input exceeds total byte budget")
			.to_string()
			.contains("ingest_max_bytes")
	);
	assert_eq!(fixture.extractor_calls.load(Ordering::SeqCst), 0);

	fixture.test_db.cleanup().await.expect("Clean fixture");
}

async fn verify_read_budget(service: &ElfService, event: &AddEventResponse, texts: &[&str]) {
	let pack = service
		.evidence_pack(EvidencePackRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			read_profile: "private_only".into(),
			note_ids: event.results.iter().filter_map(|r| r.note_id).collect(),
			max_source_bytes: None,
			max_bytes: Some(1_024),
		})
		.await
		.expect("Small response budget");

	assert!(serde_json::to_vec(&pack).expect("Response bytes").len() <= 1_024);
	assert!(!pack.complete && !pack.omitted_note_ids.is_empty());
	assert!(pack.notes.iter().all(|note| texts.contains(&note.text.as_str())));

	let recall = service
		.evidence_recall(EvidenceRecallRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			read_profile: "private_only".into(),
			subjects: vec!["ELF".into(), "项目甲".into()],
			as_of: None,
			max_bytes: Some(1_024),
		})
		.await
		.expect("Bound complete recall response");

	assert!(serde_json::to_vec(&recall).expect("Recall bytes").len() <= 1_024);
	assert!(recall.truncated);
	assert!(recall.pack.notes.iter().all(|note| texts.contains(&note.text.as_str())));
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn extracted_budget_overflow_returns_the_complete_candidate_without_queueing_it() {
	let oversized = OLD_REJECTED.repeat(70);
	let payload = serde_json::json!({"notes":[
		{"type":"fact","text":oversized,"importance":0.8,"confidence":0.9,"evidence":[{"message_index":0,"quote":OLD_REJECTED}]},
		{"type":"fact","text":OLD_REJECTED,"importance":0.8,"confidence":0.9,"evidence":[{"message_index":0,"quote":OLD_REJECTED}]}
	]});
	let Some(fixture) = setup::setup_service_with_payload("extracted_budget", payload).await else {
		return;
	};
	let result = fixture
		.service
		.add_event(AddEventRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: Some("agent_private".into()),
			dry_run: None,
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".into(),
				content: OLD_REJECTED.into(),
				ts: None,
				msg_id: None,
				source_document: None,
				write_policy: None,
			}],
		})
		.await
		.expect("Keep all extraction results");

	assert!(!result.processing_complete);
	assert_eq!(result.results.len(), 2);
	assert_eq!(result.extracted["notes"][0]["text"], oversized);
	assert_eq!(result.results[0].reason_code.as_deref(), Some("DEFERRED_INGEST_BUDGET"));
	assert!(result.results[0].note_id.is_none());
	assert_eq!(result.results[1].op, NoteOp::Add);

	let counts: (i64, i64, i64) = sqlx::query_as("SELECT (SELECT count(*) FROM memory_notes), (SELECT count(*) FROM indexing_outbox), (SELECT count(*) FROM memory_ingest_decisions WHERE reason_code='DEFERRED_INGEST_BUDGET')").fetch_one(&fixture.service.db.pool).await.expect("Only complete admitted memory is queued");

	assert_eq!(counts, (1, 1, 1));

	fixture.test_db.cleanup().await.expect("Clean fixture");
}
