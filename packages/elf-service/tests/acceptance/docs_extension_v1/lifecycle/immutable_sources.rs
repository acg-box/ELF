use crate::acceptance::docs_extension_v1::{self, DocsContext};
use elf_storage::docs;

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn multilingual_source_versions_preserve_bytes_and_citation_offsets() {
	let Some(DocsContext { test_db, service }) = docs_extension_v1::setup_docs_context().await
	else {
		return;
	};
	let original = "项目甲的负责人是王明。\n原样保留：e\u{301}、👩‍💻、می\u{200c}روم。";
	let source = serde_json::json!({"schema":"doc_source_ref/v1", "doc_type":"knowledge", "ts":"2026-10-10T00:00:00Z", "ref":"https://example.com/项目甲"});
	let first = docs_extension_v1::put_test_doc_with(
		&service,
		"owner",
		"project_shared",
		Some("knowledge"),
		"原文",
		source.clone(),
		original,
	)
	.await;
	let repeat = docs_extension_v1::put_test_doc_with(
		&service,
		"owner",
		"project_shared",
		Some("knowledge"),
		"原文",
		source.clone(),
		original,
	)
	.await;
	let changed = docs_extension_v1::put_test_doc_with(
		&service,
		"owner",
		"project_shared",
		Some("knowledge"),
		"新版本",
		source,
		"项目甲的负责人是李华。",
	)
	.await;

	assert_eq!(first.doc_id, repeat.doc_id);
	assert_ne!(first.doc_id, changed.doc_id);

	let stored = docs::get_doc_document(&service.db.pool, "t", first.doc_id)
		.await
		.expect("Read original")
		.expect("Original exists");

	assert_eq!(stored.content.as_bytes(), original.as_bytes());
	assert_eq!(stored.content_hash, blake3::hash(original.as_bytes()).to_hex().to_string());

	let mut chunks =
		docs::list_doc_chunks(&service.db.pool, first.doc_id).await.expect("Read chunks");

	assert!(!chunks.is_empty());

	for chunk in &chunks {
		assert_eq!(
			chunk.chunk_text,
			original[chunk.start_offset as usize..chunk.end_offset as usize]
		);
		assert_eq!(
			chunk.chunk_hash,
			blake3::hash(chunk.chunk_text.as_bytes()).to_hex().to_string()
		);
	}

	let mut forged = stored;

	forged.content = "A replacement must not change this citation.".to_string();

	assert!(matches!(
		docs::insert_doc_document(&service.db.pool, &forged).await,
		Err(elf_storage::Error::Conflict(_))
	));

	let mut forged_chunk = chunks.remove(0);
	let original_chunk = forged_chunk.chunk_text.clone();

	forged_chunk.chunk_text = "Different bytes".to_string();

	assert!(matches!(
		docs::insert_doc_chunk(&service.db.pool, &forged_chunk).await,
		Err(elf_storage::Error::Conflict(_))
	));

	let unchanged = docs::get_doc_document(&service.db.pool, "t", first.doc_id)
		.await
		.expect("Read original again")
		.expect("Original still exists");

	assert_eq!(unchanged.content, original);
	assert_eq!(
		docs::list_doc_chunks(&service.db.pool, first.doc_id).await.expect("Read unchanged chunks")
			[0]
		.chunk_text,
		original_chunk
	);

	drop(service);

	test_db.cleanup().await.expect("Cleanup database");
}
