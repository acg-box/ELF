use uuid::Uuid;

use crate::acceptance::text_boundary::setup;
use elf_service::{
	AddEventRequest, DocsExcerptsGetRequest, DocsPutRequest, ElfService, EventMessage,
	EventSourceDocument, NoteFetchRequest,
	docs::TextPositionSelector,
	evidence::{
		ClaimCitation, ClaimEvidence, ClaimState, EvidenceCheckRequest, EvidencePackRequest,
		EvidenceRecallRequest,
	},
};

fn claim_request(doc_id: Uuid, content_hash: &str, content: &str) -> EvidenceCheckRequest {
	let cite = ClaimCitation::Source {
		doc_id,
		content_hash: content_hash.to_string(),
		quote: "林澈担任预算负责人。".into(),
	};

	EvidenceCheckRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "a".into(),
		read_profile: "private_plus_project".into(),
		claims: vec![
			ClaimEvidence {
				depends_on: vec![],
				text: "白鹭预算负责人是林澈。".into(),
				state: ClaimState::Supported,
				citations: vec![cite.clone()],
			},
			ClaimEvidence {
				depends_on: vec![],
				text: "No source establishes this claim.".into(),
				state: ClaimState::Absent,
				citations: vec![],
			},
			ClaimEvidence {
				depends_on: vec![],
				text: "Unknown appointment.".into(),
				state: ClaimState::Unknown,
				citations: vec![],
			},
			ClaimEvidence {
				depends_on: vec![],
				text: "A real quote does not prove this unrelated claim.".into(),
				state: ClaimState::Supported,
				citations: vec![cite],
			},
			ClaimEvidence {
				depends_on: vec![],
				text: "Forged quote.".into(),
				state: ClaimState::Supported,
				citations: vec![ClaimCitation::Source {
					doc_id,
					content_hash: content_hash.to_string(),
					quote: "陈雨担任预算负责人。".into(),
				}],
			},
			ClaimEvidence {
				depends_on: vec![],
				text: "Stale hash.".into(),
				state: ClaimState::Supported,
				citations: vec![ClaimCitation::Source {
					doc_id,
					content_hash: "wrong".into(),
					quote: content.into(),
				}],
			},
		],
	}
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn evidence_expansion_and_claim_binding_preserve_sources_and_current_access() {
	let content =
		"2026-08-22。白鹭项目：林澈担任预算负责人。仅在财务批准且金额不超过十万元时生效。";
	let payload = serde_json::json!({"notes":[{"type":"fact","text":"林澈担任预算负责人。","importance":0.8,"confidence":0.9,"structured":{"facts":[content]},"evidence":[{"message_index":0,"quote":content}]}]});
	let Some(fixture) = setup::setup_service_with_payload("evidence_read", payload).await else {
		return;
	};
	let service = &fixture.service;
	let doc = service.docs_put(DocsPutRequest { tenant_id:"t".into(), project_id:"p".into(), agent_id:"a".into(), scope:"agent_private".into(), doc_type:None, title:Some("白鹭项目".into()), write_policy:None, source_ref:serde_json::json!({"schema":"doc_source_ref/v1","doc_type":"knowledge","ts":"2026-08-22T00:00:00Z"}), content:content.into() }).await.expect("Archive original");

	verify_source_only_recall(service, content).await;

	let event = service
		.add_event(AddEventRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: Some("agent_private".into()),
			dry_run: Some(false),
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".into(),
				content: content.into(),
				ts: Some("2026-08-22T00:00:00Z".into()),
				msg_id: Some("egret-record".into()),
				source_document: Some(EventSourceDocument {
					doc_id: doc.doc_id,
					content_hash: doc.content_hash.clone(),
					position: TextPositionSelector { start: 0, end: content.len() },
				}),
				write_policy: None,
			}],
		})
		.await
		.expect("Extract note");
	let note_id = event.results[0].note_id.expect("Persisted note");
	let read = NoteFetchRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "a".into(),
		note_id,
	};
	let expanded = service
		.note_evidence(read.clone(), "private_plus_project".into())
		.await
		.expect("Expand evidence");

	assert!(expanded.complete);
	assert_eq!(expanded.sources.len(), 1);
	assert_eq!(expanded.sources[0].excerpt.excerpt, content);
	assert_eq!(expanded.sources[0].metadata.content_hash, doc.content_hash);

	let reference =
		verify_evidence_pack(service, note_id, doc.doc_id, &doc.content_hash, content).await;

	verify_supplemental_recall(service, content).await;

	let request = claim_request(doc.doc_id, &doc.content_hash, content);
	let checked = service.evidence_check(request.clone()).await.expect("Check bindings");

	assert_eq!(
		checked.claims.iter().map(|c| c.binding_verified).collect::<Vec<_>>(),
		vec![true, false, true, true, false, false]
	);
	assert_eq!(checked.semantic_support, "not_evaluated");
	assert!(
		service
			.note_evidence(
				NoteFetchRequest { agent_id: "other".into(), ..read.clone() },
				"private_plus_project".into()
			)
			.await
			.is_err()
	);

	let other = service
		.evidence_check(EvidenceCheckRequest { agent_id: "other".into(), ..request.clone() })
		.await
		.expect("Unreadable bindings fail without source disclosure");

	assert!(!other.claims[0].binding_verified);

	sqlx::query("UPDATE doc_documents SET status='deleted' WHERE doc_id=$1")
		.bind(doc.doc_id)
		.execute(&service.db.pool)
		.await
		.expect("Revoke source availability");

	let revoked = service
		.note_evidence(read, "private_plus_project".into())
		.await
		.expect("Derived note remains readable");

	assert!(!revoked.complete && revoked.sources.is_empty());
	assert!(
		!service.evidence_check(request).await.expect("Recheck current access").claims[0]
			.binding_verified
	);

	let mut native_request = claim_request(doc.doc_id, &doc.content_hash, content);

	native_request.claims.truncate(1);

	native_request.claims[0].citations = vec![ClaimCitation::Reference { reference }];

	assert!(
		!service
			.evidence_check(native_request)
			.await
			.expect("Reject revoked native reference")
			.claims[0]
			.binding_verified
	);

	verify_original_unchanged(service, doc.doc_id, content, &doc.content_hash).await;

	fixture.test_db.cleanup().await.expect("Clean fixture");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn evidence_expansion_anchors_each_quote_in_a_long_source_span() {
	let first = "白鹭预算负责人是林澈。";
	let last = "The project lead is Chen.";
	let content = format!("{first}\n{}{last}", "padding ".repeat(10_000));
	let payload = serde_json::json!({"notes":[{"type":"fact","text":"Egret budget owner 林澈; project lead Chen.","importance":0.8,"confidence":0.9,"evidence":[{"message_index":0,"quote":first},{"message_index":0,"quote":last}]}]});
	let fixture = setup::setup_service_with_payload("long_evidence_window", payload)
		.await
		.expect("Test prerequisites");
	let service = &fixture.service;
	let doc = service.docs_put(DocsPutRequest { tenant_id:"t".into(), project_id:"p".into(), agent_id:"a".into(), scope:"agent_private".into(), doc_type:None, title:Some("Long source".into()), write_policy:None, source_ref:serde_json::json!({"schema":"doc_source_ref/v1","doc_type":"knowledge","ts":"2026-08-22T00:00:00Z"}), content:content.clone() }).await.expect("Archive long original");
	let event = service
		.add_event(AddEventRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			scope: Some("agent_private".into()),
			dry_run: Some(false),
			ingestion_profile: None,
			messages: vec![EventMessage {
				role: "user".into(),
				content: content.clone(),
				ts: None,
				msg_id: Some("long-original".into()),
				source_document: Some(EventSourceDocument {
					doc_id: doc.doc_id,
					content_hash: doc.content_hash.clone(),
					position: TextPositionSelector { start: 0, end: content.len() },
				}),
				write_policy: None,
			}],
		})
		.await
		.expect("Extract two distant quotes");
	let read = NoteFetchRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "a".into(),
		note_id: event.results[0].note_id.expect("Stored note"),
	};
	let expanded = service
		.note_evidence(read.clone(), "private_plus_project".into())
		.await
		.expect("Resolve quote-centered windows");

	assert!(expanded.complete);
	assert_eq!(expanded.sources.len(), 2);
	assert!(expanded.sources[0].excerpt.excerpt.contains(first));
	assert!(expanded.sources[1].excerpt.excerpt.contains(last));
	assert!(expanded.sources.iter().all(|source| source.excerpt.excerpt.len() <= 32 * 1_024));
	assert!(expanded.sources.iter().all(|source| source.excerpt.locator.selector_kind == "quote"));

	let bounded = service
		.evidence_pack(EvidencePackRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			read_profile: "private_plus_project".into(),
			note_ids: vec![read.note_id, read.note_id],
			max_source_bytes: Some(1_024),
		})
		.await
		.expect("Hydrate a small pack from a long original");

	assert!(bounded.complete);
	assert_eq!(bounded.sources.len(), 2);
	assert!(bounded.sources[0].text.contains(first));
	assert!(bounded.sources[1].text.contains(last));
	assert!(bounded.source_bytes <= 1_024);

	sqlx::query("UPDATE memory_notes SET source_ref=jsonb_set(source_ref,'{evidence,0,source,document,locator,position,start}','1024'::jsonb) WHERE note_id=$1")
        .bind(read.note_id).execute(&service.db.pool).await.expect("Simulate an invalid pointer range");

	let outside = service
		.note_evidence(read, "private_plus_project".into())
		.await
		.expect("Reject a quote outside the declared original range");

	assert!(!outside.complete);
	assert_eq!(outside.sources.len(), 1);
	assert!(outside.sources[0].excerpt.excerpt.contains(last));

	let original: (String, String) =
		sqlx::query_as("SELECT content,content_hash FROM doc_documents WHERE doc_id=$1")
			.bind(doc.doc_id)
			.fetch_one(&service.db.pool)
			.await
			.expect("Read immutable original");

	assert_eq!(original, (content, doc.content_hash));

	fixture.test_db.cleanup().await.expect("Clean fixture");
}

async fn verify_evidence_pack(
	service: &ElfService,
	note_id: Uuid,
	doc_id: Uuid,
	content_hash: &str,
	content: &str,
) -> String {
	let pack_request = EvidencePackRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "a".into(),
		read_profile: "private_plus_project".into(),
		note_ids: vec![note_id, note_id],
		max_source_bytes: None,
	};
	let pack = service.evidence_pack(pack_request.clone()).await.expect("Pack evidence");

	assert!(pack.complete);
	assert_eq!(pack.notes.len(), 1);
	assert_eq!(pack.notes[0].note_type, "fact");
	assert_eq!(pack.notes[0].project_id, "p");
	assert_eq!(pack.notes[0].scope, "agent_private");
	assert_eq!(pack.notes[0].facts, vec![content]);
	assert_eq!(pack.notes[0].evidence_quotes, vec![content]);
	assert_eq!(pack.sources.len(), 1);
	assert_eq!(pack.sources[0].text, content);
	assert_eq!(pack.sources[0].source_timestamp.as_deref(), Some("2026-08-22T00:00:00Z"));
	assert_eq!(pack.sources[0].origin.as_deref(), Some("knowledge:2026-08-22T00:00:00Z"));
	assert_eq!(pack.notes[0].source_references, vec![pack.sources[0].reference.clone()]);
	assert_eq!(pack.source_bytes, content.len());

	let excerpt = service
		.docs_excerpts_get(DocsExcerptsGetRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			read_profile: "private_plus_project".into(),
			doc_id,
			level: "L1".into(),
			max_bytes: None,
			position: Some(TextPositionSelector { start: 0, end: content.len() }),
			quote: None,
			chunk_id: None,
			explain: None,
		})
		.await
		.expect("Read exact source position");

	assert_eq!(excerpt.reference.as_deref(), Some(pack.sources[0].reference.as_str()));

	let partial = service
		.evidence_pack(EvidencePackRequest {
			max_source_bytes: Some(content.len() - 1),
			..pack_request.clone()
		})
		.await
		.expect("Budgeted evidence");

	assert!(!partial.complete);
	assert!(!partial.notes[0].complete);
	assert!(partial.sources.is_empty());
	assert!(partial.notes[0].evidence_quotes.is_empty());

	let denied = service
		.evidence_pack(EvidencePackRequest { agent_id: "other".into(), ..pack_request })
		.await
		.expect("Do not disclose unreadable notes or sources");

	assert!(denied.notes.is_empty() && denied.sources.is_empty());
	assert!(!denied.complete);

	let mut references = claim_request(doc_id, content_hash, content);

	references.claims.truncate(1);

	references.claims[0].citations =
		vec![ClaimCitation::Reference { reference: pack.sources[0].reference.clone() }];

	let native = service.evidence_check(references.clone()).await.expect("Resolve reference");

	assert!(native.claims[0].binding_verified);
	assert_eq!(native.semantic_support, "not_evaluated");

	let Some(ClaimCitation::Source { quote, content_hash: resolved_hash, .. }) =
		&native.claims[0].resolved_citations[0]
	else {
		panic!("Expected original source citation");
	};

	assert_eq!(quote, content);
	assert_eq!(resolved_hash, content_hash);

	let denied = service
		.evidence_check(EvidenceCheckRequest { agent_id: "other".into(), ..references.clone() })
		.await
		.expect("Reference does not grant access");

	assert!(!denied.claims[0].binding_verified);
	assert!(denied.claims[0].resolved_citations[0].is_none());

	for reference in [
		pack.sources[0].reference.replace(content_hash, &"0".repeat(64)),
		format!("elf-source-v1/{}/{}/12/13", doc_id, content_hash),
		format!("elf-source-v1/{}/{}/0/{}", doc_id, content_hash, content.len() + 1),
	] {
		references.claims[0].citations = vec![ClaimCitation::Reference { reference }];

		assert!(
			!service
				.evidence_check(references.clone())
				.await
				.expect("Reject invalid reference")
				.claims[0]
				.binding_verified
		);
	}

	pack.sources[0].reference.clone()
}

async fn verify_supplemental_recall(service: &ElfService, content: &str) {
	let recall_req = EvidenceRecallRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "a".into(),
		read_profile: "private_plus_project".into(),
		subjects: vec!["林澈".into()],
		as_of: Some(time::macros::datetime!(2_026-08-01 00:00 UTC)),
	};
	let recall = service
		.evidence_recall(recall_req.clone())
		.await
		.expect("Discover source without a graph edge");

	assert_eq!(recall.pack.sources[0].text, content);
	assert_eq!(recall.as_of, recall_req.as_of);
	assert!(recall.candidates[0].lexical_match);

	for hidden_request in [
		EvidenceRecallRequest { agent_id: "other".into(), ..recall_req.clone() },
		EvidenceRecallRequest { tenant_id: "other".into(), ..recall_req },
	] {
		let hidden =
			service.evidence_recall(hidden_request).await.expect("No inaccessible matches");

		assert!(hidden.candidates.is_empty());
		assert!(hidden.pack.sources.is_empty());
	}
}

async fn verify_source_only_recall(service: &ElfService, content: &str) {
	let recalled = service
		.evidence_recall(EvidenceRecallRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			read_profile: "private_only".into(),
			subjects: vec!["白鹭".into()],
			as_of: None,
		})
		.await
		.expect("Read original without any derived note");

	assert!(recalled.candidates.is_empty());
	assert_eq!(recalled.pack.sources.len(), 1);
	assert_eq!(recalled.pack.sources[0].text, content);
}

async fn verify_original_unchanged(service: &ElfService, doc_id: Uuid, content: &str, hash: &str) {
	let original: (String, String) =
		sqlx::query_as("SELECT content,content_hash FROM doc_documents WHERE doc_id=$1")
			.bind(doc_id)
			.fetch_one(&service.db.pool)
			.await
			.expect("Original readback");

	assert_eq!(original, (content.into(), hash.into()));
}
