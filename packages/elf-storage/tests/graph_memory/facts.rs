use time::{Duration, OffsetDateTime};
use uuid::Uuid;

use crate::graph_memory::helpers;
use elf_config::Postgres;
use elf_storage::{db::Db, graph, models::GraphFact};
use elf_testkit::TestDatabase;

#[tokio::test]
#[ignore = "Requires external Postgres. Set ELF_PG_DSN to run."]
async fn graph_fact_with_empty_evidence_is_rejected() {
	let Some(base_dsn) = elf_testkit::env_dsn() else {
		eprintln!("Skipping graph_fact_with_empty_evidence_is_rejected; set ELF_PG_DSN to run.");

		return;
	};
	let test_db = TestDatabase::new(&base_dsn).await.expect("Failed to create test database.");
	let cfg = Postgres { dsn: test_db.dsn().to_string(), pool_max_conns: 1 };
	let db = Db::connect(&cfg).await.expect("Failed to connect to Postgres.");

	db.ensure_schema(4_096).await.expect("Failed to ensure schema.");

	let mut tx = db.pool.begin().await.expect("Failed to open transaction.");
	let subject = graph::upsert_entity(&mut tx, "tenant-a", "project-a", "Entity A", None)
		.await
		.expect("Failed to upsert subject.");
	let predicate =
		graph::resolve_or_register_predicate(&mut tx, "tenant-a", "project-a", "related_to")
			.await
			.expect("Failed to resolve predicate.");
	let err = graph::insert_fact_with_evidence(
		&mut tx,
		"tenant-a",
		"project-a",
		"agent-a",
		"scope-a",
		subject,
		"related_to",
		predicate.predicate_id,
		None,
		Some("value"),
		OffsetDateTime::now_utc(),
		None,
		&[],
	)
	.await
	.expect_err("Expected empty evidence to be rejected.");

	assert!(matches!(err, elf_storage::Error::InvalidArgument(_)));

	tx.rollback().await.expect("Failed to rollback transaction.");
	test_db.cleanup().await.expect("Failed to cleanup test database.");
}

#[tokio::test]
#[ignore = "Requires external Postgres. Set ELF_PG_DSN to run."]
async fn graph_fact_duplicates_with_active_window_fail_unique_constraint() {
	let Some(base_dsn) = elf_testkit::env_dsn() else {
		eprintln!(
			"Skipping graph_fact_duplicates_with_active_window_fail_unique_constraint; set ELF_PG_DSN to run."
		);

		return;
	};
	let test_db = TestDatabase::new(&base_dsn).await.expect("Failed to create test database.");
	let cfg = Postgres { dsn: test_db.dsn().to_string(), pool_max_conns: 1 };
	let db = Db::connect(&cfg).await.expect("Failed to connect to Postgres.");

	db.ensure_schema(4_096).await.expect("Failed to ensure schema.");

	let mut tx = db.pool.begin().await.expect("Failed to open transaction.");
	let note_id = helpers::insert_memory_note(&mut tx, "tenant-a", "project-a").await;
	let subject = graph::upsert_entity(&mut tx, "tenant-a", "project-a", "Entity Subject", None)
		.await
		.expect("Failed to upsert subject.");
	let object = graph::upsert_entity(&mut tx, "tenant-a", "project-a", "Entity Object", None)
		.await
		.expect("Failed to upsert object.");
	let predicate =
		graph::resolve_or_register_predicate(&mut tx, "tenant-a", "project-a", "related_to")
			.await
			.expect("Failed to resolve predicate.");
	let now = OffsetDateTime::now_utc();

	graph::insert_fact_with_evidence(
		&mut tx,
		"tenant-a",
		"project-a",
		"agent-a",
		"scope-a",
		subject,
		"related_to",
		predicate.predicate_id,
		Some(object),
		None,
		now,
		None,
		&[note_id],
	)
	.await
	.expect("Failed to insert graph fact.");

	let err = graph::insert_fact_with_evidence(
		&mut tx,
		"tenant-a",
		"project-a",
		"agent-a",
		"scope-a",
		subject,
		"related_to",
		predicate.predicate_id,
		Some(object),
		None,
		now,
		None,
		&[note_id],
	)
	.await;

	assert!(err.is_err());

	tx.rollback().await.expect("Failed to rollback transaction.");
	test_db.cleanup().await.expect("Failed to cleanup test database.");
}

#[tokio::test]
#[ignore = "Requires external Postgres. Set ELF_PG_DSN to run."]
async fn graph_fact_rejects_invalid_valid_window() {
	let Some(base_dsn) = elf_testkit::env_dsn() else {
		eprintln!("Skipping graph_fact_rejects_invalid_valid_window; set ELF_PG_DSN to run.");

		return;
	};
	let test_db = TestDatabase::new(&base_dsn).await.expect("Failed to create test database.");
	let cfg = Postgres { dsn: test_db.dsn().to_string(), pool_max_conns: 1 };
	let db = Db::connect(&cfg).await.expect("Failed to connect to Postgres.");

	db.ensure_schema(4_096).await.expect("Failed to ensure schema.");

	let mut tx = db.pool.begin().await.expect("Failed to open transaction.");
	let note_id = helpers::insert_memory_note(&mut tx, "tenant-a", "project-a").await;
	let subject = graph::upsert_entity(&mut tx, "tenant-a", "project-a", "Entity Subject", None)
		.await
		.expect("Failed to upsert subject.");
	let predicate =
		graph::resolve_or_register_predicate(&mut tx, "tenant-a", "project-a", "expires")
			.await
			.expect("Failed to resolve predicate.");
	let now = OffsetDateTime::now_utc();
	let err = graph::insert_fact_with_evidence(
		&mut tx,
		"tenant-a",
		"project-a",
		"agent-a",
		"scope-a",
		subject,
		"expires",
		predicate.predicate_id,
		None,
		Some("value"),
		now,
		Some(now),
		&[note_id],
	)
	.await;

	assert!(err.is_err());

	tx.rollback().await.expect("Failed to rollback transaction.");
	test_db.cleanup().await.expect("Failed to cleanup test database.");
}

#[tokio::test]
#[ignore = "Requires external Postgres. Set ELF_PG_DSN to run."]
async fn graph_fetch_active_facts_returns_active_window_only() {
	let Some(base_dsn) = elf_testkit::env_dsn() else {
		eprintln!(
			"Skipping graph_fetch_active_facts_returns_active_window_only; set ELF_PG_DSN to run."
		);

		return;
	};
	let test_db = TestDatabase::new(&base_dsn).await.expect("Failed to create test database.");
	let cfg = Postgres { dsn: test_db.dsn().to_string(), pool_max_conns: 1 };
	let db = Db::connect(&cfg).await.expect("Failed to connect to Postgres.");

	db.ensure_schema(4_096).await.expect("Failed to ensure schema.");

	let mut tx = db.pool.begin().await.expect("Failed to open transaction.");
	let note_id = helpers::insert_memory_note(&mut tx, "tenant-a", "project-a").await;
	let subject = graph::upsert_entity(&mut tx, "tenant-a", "project-a", "Entity Subject", None)
		.await
		.expect("Failed to upsert subject.");
	let active_predicate =
		graph::resolve_or_register_predicate(&mut tx, "tenant-a", "project-a", "active_fact")
			.await
			.expect("Failed to resolve predicate.");
	let expired_predicate =
		graph::resolve_or_register_predicate(&mut tx, "tenant-a", "project-a", "expired_fact")
			.await
			.expect("Failed to resolve predicate.");
	let future_predicate =
		graph::resolve_or_register_predicate(&mut tx, "tenant-a", "project-a", "future_fact")
			.await
			.expect("Failed to resolve predicate.");
	let now = OffsetDateTime::now_utc();
	let active = graph::insert_fact_with_evidence(
		&mut tx,
		"tenant-a",
		"project-a",
		"agent-a",
		"scope-a",
		subject,
		"active_fact",
		active_predicate.predicate_id,
		None,
		Some("alpha"),
		now - Duration::hours(1),
		None,
		&[note_id],
	)
	.await
	.expect("Failed to insert active graph fact.");

	graph::insert_fact_with_evidence(
		&mut tx,
		"tenant-a",
		"project-a",
		"agent-a",
		"scope-a",
		subject,
		"expired_fact",
		expired_predicate.predicate_id,
		None,
		Some("beta"),
		now - Duration::hours(2),
		Some(now - Duration::minutes(1)),
		&[note_id],
	)
	.await
	.expect("Failed to insert expired graph fact.");
	graph::insert_fact_with_evidence(
		&mut tx,
		"tenant-a",
		"project-a",
		"agent-a",
		"scope-a",
		subject,
		"future_fact",
		future_predicate.predicate_id,
		None,
		Some("gamma"),
		now + Duration::hours(1),
		None,
		&[note_id],
	)
	.await
	.expect("Failed to insert future graph fact.");

	let facts: Vec<GraphFact> = graph::fetch_active_facts_for_subject(
		&mut tx,
		"tenant-a",
		"project-a",
		"scope-a",
		subject,
		now,
	)
	.await
	.expect("Failed to fetch active graph facts.");

	assert_eq!(facts.len(), 1);
	assert_eq!(facts[0].fact_id, active);
	assert_eq!(facts[0].predicate, "active_fact");

	tx.rollback().await.expect("Failed to rollback transaction.");
	test_db.cleanup().await.expect("Failed to cleanup test database.");
}

#[tokio::test]
#[ignore = "Requires external Postgres."]
async fn graph_schema_upgrade_preserves_rows_and_separates_owner_and_unknown_time() {
	let base = elf_testkit::env_dsn().expect("Postgres is required.");
	let test_db = TestDatabase::new(&base).await.expect("Create fixture.");
	let db = Db::connect(&Postgres { dsn: test_db.dsn().into(), pool_max_conns: 1 })
		.await
		.expect("Evidence integrity fixture must succeed.");

	db.ensure_schema(4_096).await.expect("Evidence integrity fixture must succeed.");

	let mut tx = db.pool.begin().await.expect("Evidence integrity fixture must succeed.");
	let note = helpers::insert_memory_note(&mut tx, "t", "p").await;
	let other_note = helpers::insert_memory_note(&mut tx, "t", "p").await;

	sqlx::query("UPDATE memory_notes SET agent_id='agent-b' WHERE note_id=$1")
		.bind(other_note)
		.execute(&mut *tx)
		.await
		.expect("Evidence integrity fixture must succeed.");

	let subject = graph::upsert_entity(&mut tx, "t", "p", "subject", None)
		.await
		.expect("Evidence integrity fixture must succeed.");
	let predicate = graph::resolve_or_register_predicate(&mut tx, "t", "p", "uses")
		.await
		.expect("Evidence integrity fixture must succeed.");
	let start = OffsetDateTime::from_unix_timestamp(100).expect("Valid timestamp.");
	let old = graph::upsert_fact_with_evidence(
		&mut tx,
		"t",
		"p",
		"agent-a",
		"scope-a",
		subject,
		"uses",
		predicate.predicate_id,
		None,
		Some("value"),
		Some(start),
		None,
		&[note],
	)
	.await
	.expect("Evidence integrity fixture must succeed.");

	tx.commit().await.expect("Evidence integrity fixture must succeed.");

	assert_legacy_graph_upgrade(&db, old, start).await;

	let mut tx = db.pool.begin().await.expect("Evidence integrity fixture must succeed.");
	let mut ids = Vec::new();

	for (agent, evidence, time) in [
		("agent-a", note, None),
		("agent-a", note, None),
		("agent-b", other_note, None),
		("agent-a", note, Some(start + Duration::seconds(1))),
		("agent-b", other_note, Some(start)),
	] {
		ids.push(
			graph::upsert_fact_with_evidence(
				&mut tx,
				"t",
				"p",
				agent,
				"scope-a",
				subject,
				"uses",
				predicate.predicate_id,
				None,
				Some("value"),
				time,
				None,
				&[evidence],
			)
			.await
			.expect("Evidence integrity fixture must succeed."),
		);
	}

	assert_eq!(ids[0], ids[1]);
	assert_ne!(ids[0], ids[2]);
	assert_ne!(ids[0], ids[3]);
	assert_ne!(old, ids[3]);

	let superseded = graph::supersede_conflicting_active_facts(
		&mut tx,
		"t",
		"p",
		"agent-a",
		"scope-a",
		subject,
		predicate.predicate_id,
		ids[3],
		note,
		start + Duration::seconds(1),
	)
	.await
	.expect("Supersede only this owner's earlier known assertion.");

	assert_eq!(superseded, vec![old]);

	let remaining: i64 =
		sqlx::query_scalar("SELECT count(*) FROM graph_facts WHERE valid_to IS NULL")
			.fetch_one(&mut *tx)
			.await
			.expect("Read remaining assertions.");

	assert_eq!(remaining, 4);

	tx.commit().await.expect("Evidence integrity fixture must succeed.");

	let count: i64 = sqlx::query_scalar("SELECT count(*) FROM graph_facts")
		.fetch_one(&db.pool)
		.await
		.expect("Evidence integrity fixture must succeed.");

	assert_eq!(count, 5);

	test_db.cleanup().await.expect("Evidence integrity fixture must succeed.");
}

async fn assert_legacy_graph_upgrade(db: &Db, old: Uuid, start: OffsetDateTime) {
	// Recreate only the old graph-table contract in this isolated database.
	sqlx::raw_sql("ALTER TABLE graph_facts ALTER COLUMN valid_from SET NOT NULL;
        DROP INDEX uq_graph_facts_active_entity_value;
        DROP INDEX uq_graph_facts_active_entity_object;
        CREATE UNIQUE INDEX uq_graph_facts_active_entity_value ON graph_facts(tenant_id,project_id,scope,subject_entity_id,predicate_id,object_value) WHERE valid_to IS NULL AND object_value IS NOT NULL;
        CREATE UNIQUE INDEX uq_graph_facts_active_entity_object ON graph_facts(tenant_id,project_id,scope,subject_entity_id,predicate_id,object_entity_id) WHERE valid_to IS NULL AND object_entity_id IS NOT NULL;")
        .execute(&db.pool).await.expect("Evidence integrity fixture must succeed.");

	db.ensure_schema(4_096).await.expect("Upgrade the old schema without deleting facts.");
	db.ensure_schema(4_096).await.expect("Repeat the repository-owned bootstrap safely.");

	let preserved: Option<OffsetDateTime> =
		sqlx::query_scalar("SELECT valid_from FROM graph_facts WHERE fact_id=$1")
			.bind(old)
			.fetch_one(&db.pool)
			.await
			.expect("Evidence integrity fixture must succeed.");

	assert_eq!(preserved, Some(start));
}
