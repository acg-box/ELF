use uuid::Uuid;

use elf_config::Postgres;
use elf_storage::{
	db::Db,
	graph::{self, AliasAuthority},
};
use elf_testkit::TestDatabase;

#[tokio::test]
#[ignore = "Requires external Postgres. Set ELF_PG_DSN to run."]
async fn graph_entity_upsert_is_idempotent_by_normalized_canonical() {
	let Some(base_dsn) = elf_testkit::env_dsn() else {
		eprintln!(
			"Skipping graph_entity_upsert_is_idempotent_by_normalized_canonical; set ELF_PG_DSN to run."
		);

		return;
	};
	let test_db = TestDatabase::new(&base_dsn).await.expect("Failed to create test database.");
	let cfg = Postgres { dsn: test_db.dsn().to_string(), pool_max_conns: 1 };
	let db = Db::connect(&cfg).await.expect("Failed to connect to Postgres.");

	db.ensure_schema(4_096).await.expect("Failed to ensure schema.");

	let mut tx = db.pool.begin().await.expect("Failed to open transaction.");
	let tenant_id = "tenant-a";
	let project_id = "project-a";
	let entity_id =
		graph::upsert_entity(&mut tx, tenant_id, project_id, "  Alice   Doe ", Some("person"))
			.await
			.expect("Failed to upsert canonical entity.");
	let canonical_norm = graph::normalize_entity_name("Alice doe");

	assert_eq!(canonical_norm, "alice doe");

	let entity_again =
		graph::upsert_entity(&mut tx, tenant_id, project_id, "Alice\tDoe", Some("person"))
			.await
			.expect("Failed to upsert canonical alias.");

	assert_eq!(entity_id, entity_again);

	tx.commit().await.expect("Failed to commit transaction.");

	verify_alias_upgrade(&db, entity_id, tenant_id, project_id).await;

	assert!(test_db.cleanup().await.is_ok(), "Failed to cleanup test database.");
}

async fn verify_alias_upgrade(db: &Db, entity_id: Uuid, tenant: &str, project: &str) {
	let mut conn = db.pool.acquire().await.expect("Alias connection");

	graph::upsert_entity_alias(&mut conn, entity_id, "Legacy name", AliasAuthority::Extracted)
		.await
		.expect("Extracted alias");

	assert!(
		graph::resolve_entity_by_surface(&mut conn, tenant, project, "Legacy name")
			.await
			.expect("Lookup")
			.is_none()
	);

	sqlx::query("ALTER TABLE graph_entity_aliases DROP COLUMN authority")
		.execute(&mut *conn)
		.await
		.expect("Reconstruct pre-authority schema");

	drop(conn);

	db.ensure_schema(4_096).await.expect("Upgrade old alias rows");
	db.ensure_schema(4_096).await.expect("Replay remains idempotent");

	let mut conn = db.pool.acquire().await.expect("Upgraded connection");
	let row: (Uuid, String, String) = sqlx::query_as(
		"SELECT entity_id,alias,authority FROM graph_entity_aliases WHERE entity_id=$1",
	)
	.bind(entity_id)
	.fetch_one(&mut *conn)
	.await
	.expect("Preserved row");

	assert_eq!(row, (entity_id, "Legacy name".into(), "unknown".into()));
	assert!(
		graph::resolve_entity_by_surface(&mut conn, tenant, project, "Legacy name")
			.await
			.expect("Unknown authority")
			.is_none()
	);

	graph::upsert_entity_alias(&mut conn, entity_id, "Legacy name", AliasAuthority::Caller)
		.await
		.expect("Explicit caller confirmation");
	graph::upsert_entity_alias(&mut conn, entity_id, "Legacy name", AliasAuthority::Extracted)
		.await
		.expect("Extraction cannot revoke caller authority");

	assert_eq!(
		graph::resolve_entity_by_surface(&mut conn, tenant, project, "Legacy name")
			.await
			.expect("Caller lookup")
			.expect("Confirmed identity")
			.entity_id,
		entity_id
	);
}
