use crate::acceptance::docs_extension_v1::{self, DocsContext};
use elf_service::{DocsExcerptsGetRequest, Error, TextPositionSelector, TextQuoteSelector};

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL (or ELF_QDRANT_GRPC_URL) to run."]
async fn docs_excerpts_get_supports_l0_and_returns_locator_and_optional_trajectory() {
	let Some(ctx) = docs_extension_v1::setup_docs_context().await else { return };
	let DocsContext { test_db, service } = ctx;
	let doc = docs_extension_v1::put_test_doc(&service).await;
	let (handle, shutdown) = docs_extension_v1::spawn_doc_worker(&service).await;

	assert!(
		docs_extension_v1::wait_for_doc_outbox_done(
			&service.db.pool,
			doc.doc_id,
			std::time::Duration::from_secs(15)
		)
		.await,
		"Expected doc outbox to reach DONE."
	);

	let excerpt = service
		.docs_excerpts_get(DocsExcerptsGetRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "reader".to_string(),
			read_profile: "private_plus_project".to_string(),
			doc_id: doc.doc_id,
			level: "L0".to_string(),
			max_bytes: None,
			chunk_id: None,
			quote: Some(TextQuoteSelector {
				exact: "Keyword: peregrine.".to_string(),
				prefix: Some("evidence. ".to_string()),
				suffix: Some("\nSecond".to_string()),
			}),
			position: None,
			explain: Some(true),
		})
		.await
		.expect("Failed to hydrate excerpt.");

	assert_eq!(excerpt.locator.selector_kind, "quote");
	assert!(excerpt.locator.match_end_offset > excerpt.locator.match_start_offset);
	assert!(!excerpt.locator.span_id.is_nil());
	assert!(excerpt.excerpt.len() <= 256);
	assert!(excerpt.trajectory.is_some());
	assert_eq!(
		excerpt.trajectory.as_ref().map(|trajectory| trajectory.schema.as_str()),
		Some("doc_retrieval_trajectory/v1")
	);
	assert!(!excerpt.trace_id.is_nil());

	let no_explain = service
		.docs_excerpts_get(DocsExcerptsGetRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "reader".to_string(),
			read_profile: "private_plus_project".to_string(),
			doc_id: doc.doc_id,
			level: "L0".to_string(),
			max_bytes: None,
			chunk_id: None,
			quote: Some(TextQuoteSelector {
				exact: "Keyword: peregrine.".to_string(),
				prefix: Some("evidence. ".to_string()),
				suffix: Some("\nSecond".to_string()),
			}),
			position: None,
			explain: Some(false),
		})
		.await
		.expect("Failed to hydrate excerpt.");

	assert!(no_explain.trajectory.is_none());

	let _ = shutdown.send(());

	handle.abort();

	let _ = handle.await;

	drop(service);

	test_db.cleanup().await.expect("Failed to cleanup test database.");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL (or ELF_QDRANT_GRPC_URL) to run."]
async fn excerpt_byte_cap_preserves_utf8_provenance_and_access() {
	let Some(ctx) = docs_extension_v1::setup_docs_context().await else { return };
	let DocsContext { test_db, service } = ctx;
	let content = "白鹭的原文。Conditions remain in the original.\n".repeat(400);
	let doc = docs_extension_v1::put_test_doc_with(
		&service,
		"owner",
		"project_shared",
		None,
		"Bounded source",
		serde_json::json!({
			"schema": "doc_source_ref/v1",
			"doc_type": "knowledge",
			"ts": "2026-02-25T12:00:00Z",
			"uri": "acceptance://bounded"
		}),
		&content,
	)
	.await;
	let mut request = DocsExcerptsGetRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "reader".into(),
		read_profile: "private_plus_project".into(),
		doc_id: doc.doc_id,
		level: "L1".into(),
		max_bytes: None,
		chunk_id: None,
		quote: None,
		position: Some(TextPositionSelector { start: 7_000, end: 7_001 }),
		explain: None,
	};
	let original = service.docs_excerpts_get(request.clone()).await.expect("Default read.");

	assert!((8_186..=8_192).contains(&original.excerpt.len()));

	for cap in [1, 13, 500, 1_500, 100_000] {
		request.max_bytes = Some(cap);

		let excerpt = service.docs_excerpts_get(request.clone()).await.expect("Bounded read.");

		assert!(excerpt.excerpt.len() <= cap.min(8_192));
		assert_eq!(excerpt.excerpt, content[excerpt.start_offset..excerpt.end_offset]);
		assert_eq!(excerpt.verification.content_hash, doc.content_hash);
		assert_eq!(
			excerpt.verification.excerpt_hash,
			blake3::hash(excerpt.excerpt.as_bytes()).to_hex().to_string()
		);

		if excerpt.verification.verified {
			assert_eq!(
				excerpt.reference,
				Some(format!(
					"elf-source-v1/{}/{}/{}/{}",
					doc.doc_id, doc.content_hash, excerpt.start_offset, excerpt.end_offset
				))
			);
		} else {
			assert!(excerpt.reference.is_none());
			assert!(excerpt.excerpt.is_empty());
		}
	}

	request.max_bytes = Some(0);

	assert!(matches!(
		service.docs_excerpts_get(request.clone()).await,
		Err(Error::InvalidRequest { .. })
	));

	request.max_bytes = Some(500);
	request.tenant_id = "foreign".into();

	assert!(matches!(service.docs_excerpts_get(request).await, Err(Error::NotFound { .. })));

	let stored: String = sqlx::query_scalar("SELECT content FROM doc_documents WHERE doc_id = $1")
		.bind(doc.doc_id)
		.fetch_one(&service.db.pool)
		.await
		.expect("Original source read.");

	assert_eq!(stored, content);

	drop(service);

	test_db.cleanup().await.expect("Cleanup test database.");
}
