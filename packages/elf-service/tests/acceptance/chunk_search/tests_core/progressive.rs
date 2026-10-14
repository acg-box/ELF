use uuid::Uuid;

use crate::acceptance::{StubRerank, chunk_search::tests_helpers};
use elf_service::{
	SearchDetailsRequest, SearchRequest, SearchSessionGetRequest, SearchTimelineRequest,
};

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn cached_candidate_counts_survive_expansion_and_keep_session_ownership() {
	let context = tests_helpers::setup_context(
		"cached_candidates",
		tests_helpers::build_providers(StubRerank),
	)
	.await
	.expect("Test prerequisites");

	for text in ["Cedar uses the old queue.", "Cedar retired the old queue."] {
		let note = Uuid::new_v4();
		let chunk = Uuid::new_v4();

		tests_helpers::insert_note(
			&context.service.db.pool,
			note,
			text,
			&context.embedding_version,
		)
		.await;
		tests_helpers::insert_chunk(
			&context.service.db.pool,
			chunk,
			note,
			0,
			0,
			text.len() as i32,
			text,
			&context.embedding_version,
		)
		.await;
		tests_helpers::upsert_point(&context.service, chunk, note, 0, 0, text.len() as i32, text)
			.await;
	}

	let index = context
		.service
		.search(SearchRequest {
			tenant_id: "t".into(),
			project_id: "p".into(),
			agent_id: "a".into(),
			token_id: None,
			read_profile: "private_only".into(),
			payload_level: Default::default(),
			query: "Cedar queue".into(),
			top_k: Some(1),
			candidate_k: Some(10),
			filter: None,
			record_hits: Some(false),
			ranking: None,
		})
		.await
		.expect("First candidate");

	assert_eq!(index.items.len(), 1);
	assert_eq!(index.total, 2);
	assert!(index.has_more);

	let request = SearchSessionGetRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "a".into(),
		search_session_id: index.search_session_id,
		payload_level: Default::default(),
		top_k: Some(8),
		touch: Some(false),
	};
	let expanded =
		context.service.search_session_get(request.clone()).await.expect("Cached expansion");

	assert_eq!(expanded.total, 2);
	assert_eq!(expanded.items.len(), 2);
	assert!(!expanded.has_more);
	assert!(
		context
			.service
			.search_session_get(SearchSessionGetRequest { agent_id: "other".into(), ..request })
			.await
			.is_err()
	);

	context.test_db.cleanup().await.expect("Clean database");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant. Set ELF_PG_DSN and ELF_QDRANT_URL to run."]
async fn progressive_search_returns_index_timeline_and_details() {
	let providers = tests_helpers::build_providers(StubRerank);
	let Some(context) = tests_helpers::setup_context(
		"progressive_search_returns_index_timeline_and_details",
		providers,
	)
	.await
	else {
		return;
	};
	let note_id = Uuid::new_v4();
	let chunk_id = Uuid::new_v4();
	let note_text = "Progressive retrieval works best with staged expansion.";

	tests_helpers::insert_note(
		&context.service.db.pool,
		note_id,
		note_text,
		&context.embedding_version,
	)
	.await;
	tests_helpers::insert_chunk(
		&context.service.db.pool,
		chunk_id,
		note_id,
		0,
		0,
		note_text.len() as i32,
		note_text,
		&context.embedding_version,
	)
	.await;
	tests_helpers::upsert_point(
		&context.service,
		chunk_id,
		note_id,
		0,
		0,
		note_text.len() as i32,
		note_text,
	)
	.await;

	let index = context
		.service
		.search(SearchRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "a".to_string(),
			token_id: None,
			read_profile: "private_only".to_string(),
			payload_level: Default::default(),
			query: "Progressive".to_string(),
			top_k: Some(5),
			candidate_k: Some(10),
			filter: None,
			record_hits: Some(false),
			ranking: None,
		})
		.await
		.expect("Search index failed.");

	assert!(!index.items.is_empty());

	let timeline = context
		.service
		.search_timeline(SearchTimelineRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "a".to_string(),
			search_session_id: index.search_session_id,
			payload_level: Default::default(),
			group_by: None,
		})
		.await
		.expect("Search timeline failed.");

	assert!(!timeline.groups.is_empty());

	let details = context
		.service
		.search_details(SearchDetailsRequest {
			tenant_id: "t".to_string(),
			project_id: "p".to_string(),
			agent_id: "a".to_string(),
			search_session_id: index.search_session_id,
			payload_level: Default::default(),
			note_ids: vec![note_id],
			record_hits: Some(false),
		})
		.await
		.expect("Search details failed.");
	let returned = details
		.results
		.first()
		.and_then(|result| result.note.as_ref())
		.expect("Expected note details.");

	assert_eq!(returned.note_id, note_id);
	assert_eq!(returned.text, note_text);

	context.test_db.cleanup().await.expect("Failed to cleanup test database.");
}
