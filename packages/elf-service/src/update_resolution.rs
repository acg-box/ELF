use serde_json::Value;
use sqlx::PgConnection;
use time::OffsetDateTime;
use uuid::Uuid;

use crate::Result;

// Only an explicit caller key authorizes replacement. Unkeyed equality must
// include the source occurrence; identical prose is not an occurrence identity.
const RESOLVE_UPDATE_QUERY: &str = "\
SELECT note_id, source_ref FROM memory_notes
WHERE tenant_id = $1 AND project_id = $2 AND agent_id = $3
    AND scope = $4 AND type = $5 AND status = 'active'
    AND (expires_at IS NULL OR expires_at > $7)
    AND (($6::text IS NOT NULL AND key = $6)
        OR ($6::text IS NULL AND key IS NULL AND text = $8))
ORDER BY created_at, note_id";

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
	pub(crate) source_ref: &'a Value,
	pub(crate) now: OffsetDateTime,
}

/// The caller holds a transaction through resolution and persistence. Serializing
/// each candidate identity also prevents two concurrent first writes from racing.
pub(crate) async fn resolve_update(
	executor: &mut PgConnection,
	args: ResolveUpdateArgs<'_>,
) -> Result<UpdateDecision> {
	let ResolveUpdateArgs {
		tenant_id,
		project_id,
		agent_id,
		scope,
		note_type,
		key,
		text,
		source_ref,
		now,
	} = args;
	let key = key.map(str::trim).filter(|value| !value.is_empty());
	let lock_identity = serde_json::json!([
		tenant_id,
		project_id,
		agent_id,
		scope,
		note_type,
		key,
		if key.is_none() { Some(text) } else { None }
	]);
	let hash = blake3::hash(lock_identity.to_string().as_bytes());
	let lock = i64::from_be_bytes(hash.as_bytes()[..8].try_into().expect("Eight hash bytes"));

	sqlx::query("SELECT pg_advisory_xact_lock($1)").bind(lock).execute(&mut *executor).await?;

	let candidates: Vec<(Uuid, Value)> = sqlx::query_as(RESOLVE_UPDATE_QUERY)
		.bind(tenant_id)
		.bind(project_id)
		.bind(agent_id)
		.bind(scope)
		.bind(note_type)
		.bind(key)
		.bind(now)
		.bind(text)
		.fetch_all(executor)
		.await?;
	let identity = source_identity(source_ref);
	let existing = candidates
		.into_iter()
		.find(|(_, source)| key.is_some() || source_identity(source) == identity)
		.map(|(id, _)| id);
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

/// Compare stable source identities, not batch positions or model explanations.
/// Unknown caller provenance remains part of identity instead of being discarded.
fn source_identity(source_ref: &Value) -> Value {
	let Some(evidence) = source_ref.get("evidence").and_then(Value::as_array) else {
		return source_ref.clone();
	};

	if evidence.is_empty() {
		return source_ref.clone();
	}

	let mut sources: Vec<Value> = evidence
		.iter()
		.map(|item| {
			let source = &item["source"];

			if source["schema"] != "elf.event_source/v1" {
				return item.clone();
			}

			serde_json::json!({
				"message_id": source["message_id"],
				"role": source["role"],
				"timestamp": source["timestamp"],
				"content_hash": source["content_hash"],
				"document": source["document"],
			})
		})
		.collect();

	sources.sort_by_key(Value::to_string);
	sources.dedup();

	Value::Array(sources)
}

#[cfg(test)]
mod tests {
	use crate::update_resolution;

	#[test]
	fn occurrence_identity_ignores_batch_position_and_quote_selection() {
		let mut first = serde_json::json!({"evidence":[{"message_index":0,"quote":"first quote","source":{
			"schema":"elf.event_source/v1","message_id":"a","content_hash":"original","role":"user","timestamp":"2026-08-08"
		}}],"reason":"model explanation"});
		let identity = update_resolution::source_identity(&first);

		first["evidence"][0]["message_index"] = serde_json::json!(4);
		first["evidence"][0]["quote"] = serde_json::json!("another quote");
		first["reason"] = serde_json::json!("another explanation");

		assert_eq!(update_resolution::source_identity(&first), identity);

		first["evidence"][0]["source"]["message_id"] = serde_json::json!("b");

		assert_ne!(update_resolution::source_identity(&first), identity);
	}
}
