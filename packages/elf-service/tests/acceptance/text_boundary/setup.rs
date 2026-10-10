use std::sync::{Arc, atomic::AtomicUsize};

use serde_json::Value;

use crate::acceptance::{self, SpyExtractor, StubEmbedding, StubRerank};
use elf_service::{ElfService, Providers};
use elf_testkit::TestDatabase;

pub(in crate::acceptance::text_boundary) struct BoundaryFixture {
	pub(in crate::acceptance::text_boundary) service: ElfService,
	pub(in crate::acceptance::text_boundary) test_db: TestDatabase,
}

pub(in crate::acceptance::text_boundary) async fn setup_service(
	test_name: &str,
) -> Option<BoundaryFixture> {
	setup_service_with_payload(test_name, serde_json::json!({"notes":[]})).await
}

pub(in crate::acceptance::text_boundary) async fn setup_service_with_payload(
	test_name: &str,
	payload: Value,
) -> Option<BoundaryFixture> {
	let Some(test_db) = acceptance::test_db().await else {
		eprintln!("Skipping {test_name}; set ELF_PG_DSN to run this test.");

		return None;
	};
	let Some(qdrant_url) = acceptance::test_qdrant_url() else {
		eprintln!("Skipping {test_name}; set ELF_QDRANT_URL to run this test.");

		return None;
	};
	let collection = test_db.collection_name("elf_acceptance");
	let docs_collection = test_db.collection_name("elf_acceptance_docs");
	let extractor = SpyExtractor { calls: Arc::new(AtomicUsize::new(0)), payload };
	let providers = Providers::new(
		Arc::new(StubEmbedding { vector_dim: 4_096 }),
		Arc::new(StubRerank),
		Arc::new(extractor),
	);
	let cfg = acceptance::test_config(
		test_db.dsn().to_string(),
		qdrant_url,
		4_096,
		collection,
		docs_collection,
	);
	let service =
		acceptance::build_service(cfg, providers).await.expect("Failed to build service.");

	acceptance::reset_db(&service.db.pool).await.expect("Failed to reset test database.");

	Some(BoundaryFixture { service, test_db })
}
