use serde_json::Value;
use sqlx::PgExecutor;
use time::OffsetDateTime;
use uuid::Uuid;

use crate::{Error, Result, models::DocDocument};

/// Normalizes absent document source metadata to an empty JSON object.
pub fn normalize_source_ref(source_ref: Option<Value>) -> Value {
	source_ref.unwrap_or(Value::Object(Default::default()))
}

/// Inserts one document record into storage.
pub async fn insert_doc_document<'e, E>(executor: E, doc: &DocDocument) -> Result<()>
where
	E: PgExecutor<'e>,
{
	let written = sqlx::query(
		"\
INSERT INTO doc_documents (
	doc_id,
	tenant_id,
	project_id,
	agent_id,
	scope,
	doc_type,
	status,
	title,
	source_ref,
	content,
	content_bytes,
	content_hash,
	created_at,
	updated_at
)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
ON CONFLICT (doc_id) DO UPDATE
SET
    status = EXCLUDED.status,
    source_ref = EXCLUDED.source_ref,
    updated_at = EXCLUDED.updated_at
WHERE doc_documents.content = EXCLUDED.content
  AND doc_documents.content_hash = EXCLUDED.content_hash
  AND doc_documents.content_bytes = EXCLUDED.content_bytes
  AND doc_documents.tenant_id = EXCLUDED.tenant_id
  AND doc_documents.project_id = EXCLUDED.project_id
  AND doc_documents.agent_id = EXCLUDED.agent_id
  AND doc_documents.scope = EXCLUDED.scope
  AND doc_documents.doc_type = EXCLUDED.doc_type",
	)
	.bind(doc.doc_id)
	.bind(doc.tenant_id.as_str())
	.bind(doc.project_id.as_str())
	.bind(doc.agent_id.as_str())
	.bind(doc.scope.as_str())
	.bind(doc.doc_type.as_str())
	.bind(doc.status.as_str())
	.bind(doc.title.as_deref())
	.bind(&doc.source_ref)
	.bind(doc.content.as_str())
	.bind(doc.content_bytes)
	.bind(doc.content_hash.as_str())
	.bind(doc.created_at)
	.bind(doc.updated_at)
	.execute(executor)
	.await?;

	if written.rows_affected() != 1 {
		return Err(Error::Conflict(
			"Source document identity cannot overwrite immutable content or ownership.".to_string(),
		));
	}

	Ok(())
}

/// Fetches one document record by tenant and document identifier.
pub async fn get_doc_document<'e, E>(
	executor: E,
	tenant_id: &str,
	doc_id: Uuid,
) -> Result<Option<DocDocument>>
where
	E: PgExecutor<'e>,
{
	let row = sqlx::query_as::<_, DocDocument>(
		"\
	SELECT
		doc_id,
		tenant_id,
		project_id,
		agent_id,
		scope,
		doc_type,
		status,
		title,
		COALESCE(source_ref, '{}'::jsonb) AS source_ref,
		content,
		content_bytes,
		content_hash,
		created_at,
		updated_at
FROM doc_documents
WHERE tenant_id = $1 AND doc_id = $2
LIMIT 1",
	)
	.bind(tenant_id)
	.bind(doc_id)
	.fetch_optional(executor)
	.await?;

	Ok(row)
}

/// Marks one document record as deleted.
pub async fn mark_doc_deleted<'e, E>(
	executor: E,
	tenant_id: &str,
	doc_id: Uuid,
	source_ref: &Value,
	now: OffsetDateTime,
) -> Result<()>
where
	E: PgExecutor<'e>,
{
	sqlx::query(
		"\
UPDATE doc_documents
SET status = 'deleted', source_ref = $1, updated_at = $2
WHERE tenant_id = $3 AND doc_id = $4",
	)
	.bind(source_ref)
	.bind(now)
	.bind(tenant_id)
	.bind(doc_id)
	.execute(executor)
	.await?;

	Ok(())
}
