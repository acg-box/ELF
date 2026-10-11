use std::sync::{Arc, atomic::AtomicUsize};

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
		Box::pin(async move { Ok(vec![vec![1.0; 4096]; texts.len()]) })
	}
}

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn memory_identity_preserves_distinct_facts_and_clears_stale_fields() {
	let db = acceptance::test_db().await.expect("Postgres is required.");
	let cfg = acceptance::test_config(
		db.dsn().to_string(),
		acceptance::test_qdrant_url().expect("Qdrant is required."),
		4096,
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
	.unwrap();
	let note = |key: Option<&str>, text: &str| AddNoteInput {
		r#type: "fact".into(),
		key: key.map(str::to_string),
		text: text.into(),
		structured: Some(
			serde_json::from_value(serde_json::json!({"summary":text,"facts":[text]})).unwrap(),
		),
		importance: 0.8,
		confidence: 0.9,
		ttl_days: None,
		source_ref: serde_json::json!({"quote":text}),
		write_policy: None,
	};
	let request = |note| AddNoteRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "a".into(),
		scope: "agent_private".into(),
		notes: vec![note],
	};
	let first = service
		.add_note(request(note(Some("retry-0"), "Use RETRY-0-907.")))
		.await
		.unwrap()
		.results
		.remove(0);
	let id = first.note_id.unwrap();
	// Identical vectors must not grant authority to overwrite a different identity.
	let vector = format!("[{}]", vec!["1"; 4096].join(","));
	sqlx::query("INSERT INTO note_embeddings(note_id,embedding_version,embedding_dim,vec) SELECT note_id,embedding_version,4096,$2::text::vector FROM memory_notes WHERE note_id=$1")
        .bind(id).bind(vector).execute(&service.db.pool).await.unwrap();
	for key in [Some("retry-4"), None] {
		let next = service
			.add_note(request(note(key, "Use RETRY-4-907.")))
			.await
			.unwrap()
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
			.unwrap();
	assert!(fields.iter().all(|text| text.contains("RETRY-0-907")));
	let mut duplicate = note(None, "Use RETRY-4-907.");
	duplicate.structured =
		Some(serde_json::from_value(serde_json::json!({"facts":["Wrong incoming fact"]})).unwrap());
	let result = service.add_note(request(duplicate)).await.unwrap().results.remove(0);
	assert_eq!(result.op, NoteOp::None);
	let wrong: i64 = sqlx::query_scalar(
		"SELECT count(*) FROM memory_note_fields WHERE text='Wrong incoming fact'",
	)
	.fetch_one(&service.db.pool)
	.await
	.unwrap();
	assert_eq!(wrong, 0);
	let mut replacement = note(Some("retry-0"), "Use RETRY-0-908.");
	replacement.structured = None;
	let result = service.add_note(request(replacement)).await.unwrap().results.remove(0);
	assert_eq!(result.note_id, Some(id));
	assert_eq!(result.op, NoteOp::Update);
	let count: i64 = sqlx::query_scalar("SELECT count(*) FROM memory_note_fields WHERE note_id=$1")
		.bind(id)
		.fetch_one(&service.db.pool)
		.await
		.unwrap();
	assert_eq!(count, 0);
	let (text, source): (String, serde_json::Value) =
		sqlx::query_as("SELECT text,source_ref FROM memory_notes WHERE note_id=$1")
			.bind(id)
			.fetch_one(&service.db.pool)
			.await
			.unwrap();
	assert_eq!(source["quote"], text);
	db.cleanup().await.unwrap();
}
