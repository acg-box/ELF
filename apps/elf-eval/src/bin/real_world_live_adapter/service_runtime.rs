use crate::{
	Arc, BaselineRuntime, ChunkingConfig, Db, ElfService, JoinSet, QdrantStore, Result,
	WorkerState, eyre, worker,
};

pub(super) async fn build_service(runtime: &BaselineRuntime) -> Result<ElfService> {
	let cfg = crate::runtime_config(runtime)?;
	let db = Db::connect(&cfg.storage.postgres).await?;

	db.ensure_schema(cfg.storage.qdrant.vector_dim).await?;

	let qdrant = QdrantStore::new(&cfg.storage.qdrant)?;

	qdrant.ensure_collection().await?;

	let providers = crate::real_world_providers(&cfg);

	Ok(ElfService::with_providers(cfg, db, qdrant, providers))
}

pub(super) async fn run_worker(runtime: &BaselineRuntime) -> Result<()> {
	let state = Arc::new(build_worker_state(runtime).await?);
	let drain = async {
		loop {
			let (remaining, failed) = sqlx::query_as::<_, (i64, i64)>(
				"SELECT COUNT(*) FILTER (WHERE status <> 'DONE'),
				 COUNT(*) FILTER (WHERE status = 'FAILED')
				 FROM (
				 SELECT status FROM indexing_outbox
				 UNION ALL SELECT status FROM doc_indexing_outbox
				 UNION ALL SELECT status FROM search_trace_outbox
				 UNION ALL SELECT status FROM consolidation_run_jobs
				 ) AS queues",
			)
			.fetch_one(&state.db.pool)
			.await?;

			if failed > 0 {
				return Err(eyre::eyre!("Benchmark worker has {failed} failed jobs."));
			}
			if remaining == 0 {
				return Ok(());
			}

			// A worker pass handles at most one item per queue. A fixed pass
			// count can report retrieval readiness with an unfinished corpus.
			let state = Arc::clone(&state);
			let mut set = JoinSet::new();

			set.spawn(async move {
				worker::process_once(&state)
					.await
					.map_err(|err| eyre::eyre!("Worker process_once failed: {err}"))
			});

			while let Some(joined) = set.join_next().await {
				joined??;
			}

			tokio::time::sleep(std::time::Duration::from_millis(25)).await;
		}
	};

	tokio::time::timeout(std::time::Duration::from_secs(180), drain)
		.await
		.map_err(|_| eyre::eyre!("Benchmark worker did not drain within 180 seconds."))?
}

async fn build_worker_state(runtime: &BaselineRuntime) -> Result<WorkerState> {
	let cfg = crate::runtime_config(runtime)?;
	let db = Db::connect(&cfg.storage.postgres).await?;

	db.ensure_schema(cfg.storage.qdrant.vector_dim).await?;

	let qdrant = QdrantStore::new(&cfg.storage.qdrant)?;

	qdrant.ensure_collection().await?;

	let docs_qdrant =
		QdrantStore::new_with_collection(&cfg.storage.qdrant, &cfg.storage.qdrant.docs_collection)?;

	docs_qdrant.ensure_collection().await?;

	let tokenizer = elf_chunking::load_tokenizer(&cfg.chunking.tokenizer_repo)
		.map_err(|err| eyre::eyre!("Failed to load tokenizer for live adapter worker: {err}"))?;
	let chunking = ChunkingConfig {
		max_tokens: cfg.chunking.max_tokens,
		overlap_tokens: cfg.chunking.overlap_tokens,
	};

	Ok(WorkerState {
		db,
		qdrant,
		docs_qdrant,
		embedding: cfg.providers.embedding,
		chunking,
		tokenizer,
	})
}
