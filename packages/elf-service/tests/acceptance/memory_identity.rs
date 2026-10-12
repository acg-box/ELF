use std::sync::{Arc, atomic::AtomicUsize};

use serde_json::Value;

use crate::acceptance::{self, SpyExtractor, StubRerank};
use elf_config::EmbeddingProviderConfig;
use elf_service::{
	AddNoteInput, AddNoteRequest, BoxFuture, EmbeddingProvider, NoteOp, Providers, Result,
};

struct IdenticalEmbedding;
impl EmbeddingProvider for IdenticalEmbedding {
	fn embed<'a>(
		&'a self,
		_: &'a EmbeddingProviderConfig,
		texts: &'a [String],
	) -> BoxFuture<'a, Result<Vec<Vec<f32>>>> {
		Box::pin(async move { Ok(vec![vec![1.0; 4_096]; texts.len()]) })
	}
}

fn note(key: Option<&str>, text: &str) -> AddNoteInput {
	AddNoteInput {
		r#type: "fact".into(),
		key: key.map(str::to_string),
		text: text.into(),
		structured: Some(
			serde_json::from_value(serde_json::json!({"summary":text,"facts":[text]}))
				.expect("Identity regression fixture must succeed."),
		),
		importance: 0.8,
		confidence: 0.9,
		ttl_days: None,
		source_ref: serde_json::json!({"quote":text}),
		write_policy: None,
	}
}

fn request(note: AddNoteInput) -> AddNoteRequest {
	AddNoteRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "a".into(),
		scope: "agent_private".into(),
		notes: vec![note],
	}
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn memory_identity_preserves_distinct_facts_and_clears_stale_fields() {
	let db = acceptance::test_db().await.expect("Postgres is required.");
	let cfg = acceptance::test_config(
		db.dsn().to_string(),
		acceptance::test_qdrant_url().expect("Qdrant is required."),
		4_096,
		db.collection_name("identity"),
		db.collection_name("identity_docs"),
	);
	let service = acceptance::build_service(
		cfg,
		Providers::new(
			Arc::new(IdenticalEmbedding),
			Arc::new(StubRerank),
			Arc::new(SpyExtractor {
				calls: Arc::new(AtomicUsize::new(0)),
				payload: serde_json::json!({"notes":[]}),
			}),
		),
	)
	.await
	.expect("Identity regression fixture must succeed.");
	let first = service
		.add_note(request(note(Some("retry-0"), "Use RETRY-0-907.")))
		.await
		.expect("Identity regression fixture must succeed.")
		.results
		.remove(0);
	let id = first.note_id.expect("Identity regression fixture must succeed.");
	// Identical vectors must not grant authority to overwrite a different identity.
	let vector = format!("[{}]", vec!["1"; 4_096].join(","));

	sqlx::query("INSERT INTO note_embeddings(note_id,embedding_version,embedding_dim,vec) SELECT note_id,embedding_version,4096,$2::text::vector FROM memory_notes WHERE note_id=$1")
        .bind(id).bind(vector).execute(&service.db.pool).await.expect("Identity regression fixture must succeed.");

	for key in [Some("retry-4"), None] {
		let next = service
			.add_note(request(note(key, "Use RETRY-4-907.")))
			.await
			.expect("Identity regression fixture must succeed.")
			.results
			.remove(0);

		assert_eq!(next.op, NoteOp::Add);
		assert_ne!(next.note_id, Some(id));
	}

	let fields: Vec<String> =
		sqlx::query_scalar("SELECT text FROM memory_note_fields WHERE note_id=$1")
			.bind(id)
			.fetch_all(&service.db.pool)
			.await
			.expect("Identity regression fixture must succeed.");

	assert!(fields.iter().all(|text| text.contains("RETRY-0-907")));

	let mut duplicate = note(None, "Use RETRY-4-907.");

	duplicate.structured = Some(
		serde_json::from_value(serde_json::json!({"facts":["RETRY-4-907"]}))
			.expect("Identity regression fixture must succeed."),
	);

	let result = service
		.add_note(request(duplicate))
		.await
		.expect("Identity regression fixture must succeed.")
		.results
		.remove(0);

	assert_eq!(result.op, NoteOp::None);

	let wrong: i64 =
		sqlx::query_scalar("SELECT count(*) FROM memory_note_fields WHERE text='RETRY-4-907'")
			.fetch_one(&service.db.pool)
			.await
			.expect("Identity regression fixture must succeed.");

	assert_eq!(wrong, 0);

	let mut replacement = note(Some("retry-0"), "Use RETRY-0-908.");

	replacement.structured = None;

	let result = service
		.add_note(request(replacement))
		.await
		.expect("Identity regression fixture must succeed.")
		.results
		.remove(0);

	assert_eq!(result.note_id, Some(id));
	assert_eq!(result.op, NoteOp::Update);

	let count: i64 = sqlx::query_scalar("SELECT count(*) FROM memory_note_fields WHERE note_id=$1")
		.bind(id)
		.fetch_one(&service.db.pool)
		.await
		.expect("Identity regression fixture must succeed.");

	assert_eq!(count, 0);

	let (text, source): (String, Value) =
		sqlx::query_as("SELECT text,source_ref FROM memory_notes WHERE note_id=$1")
			.bind(id)
			.fetch_one(&service.db.pool)
			.await
			.expect("Identity regression fixture must succeed.");

	assert_eq!(source["quote"], text);

	db.cleanup().await.expect("Identity regression fixture must succeed.");
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn identical_text_preserves_source_occurrences_under_concurrent_retries() {
	let db = acceptance::test_db().await.expect("Postgres is required.");
	let cfg = acceptance::test_config(
		db.dsn().to_string(),
		acceptance::test_qdrant_url().expect("Qdrant is required."),
		4_096,
		db.collection_name("occurrences"),
		db.collection_name("occurrence_docs"),
	);
	let service = acceptance::build_service(
		cfg,
		Providers::new(
			Arc::new(IdenticalEmbedding),
			Arc::new(StubRerank),
			Arc::new(SpyExtractor {
				calls: Arc::new(AtomicUsize::new(0)),
				payload: serde_json::json!({"notes":[]}),
			}),
		),
	)
	.await
	.expect("Build service.");
	let mut first = note(None, "No change was approved.");

	first.source_ref = serde_json::json!({"source_id":"project-A/meeting"});

	let mut second = first.clone();

	second.source_ref = serde_json::json!({"source_id":"project-B/meeting"});

	let (left, right) =
		tokio::join!(service.add_note(request(first.clone())), service.add_note(request(first)));
	let left = left.expect("First concurrent write.").results.remove(0);
	let right = right.expect("Concurrent retry.").results.remove(0);

	assert_eq!(left.note_id, right.note_id);
	assert!(matches!(
		(left.op, right.op),
		(NoteOp::Add, NoteOp::None) | (NoteOp::None, NoteOp::Add)
	));

	let other = service
		.add_note(request(second))
		.await
		.expect("Distinct source occurrence.")
		.results
		.remove(0);

	assert_eq!(other.op, NoteOp::Add);
	assert_ne!(other.note_id, left.note_id);

	let count: i64 = sqlx::query_scalar("SELECT count(*) FROM memory_notes")
		.fetch_one(&service.db.pool)
		.await
		.expect("Read occurrences.");

	assert_eq!(count, 2);

	db.cleanup().await.expect("Clean fixture.");
}
