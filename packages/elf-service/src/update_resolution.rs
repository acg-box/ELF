use sqlx::PgExecutor;
use time::OffsetDateTime;
use uuid::Uuid;

use crate::Result;

// Only an explicit key authorizes replacement. Similarity is retrieval evidence,
// not note identity. Unkeyed notes deduplicate only byte-identical bodies.
const RESOLVE_UPDATE_QUERY: &str = "\
SELECT note_id FROM memory_notes
WHERE tenant_id = $1 AND project_id = $2 AND agent_id = $3
    AND scope = $4 AND type = $5 AND status = 'active'
    AND (expires_at IS NULL OR expires_at > $7)
    AND (($6::text IS NOT NULL AND key = $6)
        OR ($6::text IS NULL AND key IS NULL AND text = $8))
ORDER BY created_at, note_id
LIMIT 1";

#[derive(Clone, Copy, Debug)]
pub(crate) enum UpdateDecision {
	Add { note_id: Uuid, metadata: UpdateDecisionMetadata },
	Update { note_id: Uuid, metadata: UpdateDecisionMetadata },
	None { note_id: Uuid, metadata: UpdateDecisionMetadata },
}
impl UpdateDecision {
	pub(crate) fn note_id(&self) -> Uuid {
		match self {
			Self::Add { note_id, .. }
			| Self::Update { note_id, .. }
			| Self::None { note_id, .. } => *note_id,
		}
	}

	pub(crate) fn metadata(&self) -> UpdateDecisionMetadata {
		match self {
			Self::Add { metadata, .. }
			| Self::Update { metadata, .. }
			| Self::None { metadata, .. } => *metadata,
		}
	}
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct UpdateDecisionMetadata {
	pub similarity_best: Option<f32>,
	pub key_match: bool,
	pub matched_dup: bool,
}

pub(crate) struct ResolveUpdateArgs<'a> {
	pub(crate) tenant_id: &'a str,
	pub(crate) project_id: &'a str,
	pub(crate) agent_id: &'a str,
	pub(crate) scope: &'a str,
	pub(crate) note_type: &'a str,
	pub(crate) key: Option<&'a str>,
	pub(crate) text: &'a str,
	pub(crate) now: OffsetDateTime,
}

pub(crate) async fn resolve_update<'e, E>(
	executor: E,
	args: ResolveUpdateArgs<'_>,
) -> Result<UpdateDecision>
where
	E: PgExecutor<'e>,
{
	let ResolveUpdateArgs { tenant_id, project_id, agent_id, scope, note_type, key, text, now } =
		args;
	let key = key.map(str::trim).filter(|value| !value.is_empty());
	let existing: Option<Uuid> = sqlx::query_scalar(RESOLVE_UPDATE_QUERY)
		.bind(tenant_id)
		.bind(project_id)
		.bind(agent_id)
		.bind(scope)
		.bind(note_type)
		.bind(key)
		.bind(now)
		.bind(text)
		.fetch_optional(executor)
		.await?;
	let metadata = UpdateDecisionMetadata {
		similarity_best: None,
		key_match: existing.is_some() && key.is_some(),
		matched_dup: existing.is_some() && key.is_none(),
	};
	Ok(match existing {
		Some(note_id) if key.is_some() => UpdateDecision::Update { note_id, metadata },
		Some(note_id) => UpdateDecision::None { note_id, metadata },
		None => UpdateDecision::Add { note_id: Uuid::new_v4(), metadata },
	})
}
