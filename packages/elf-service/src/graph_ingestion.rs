use sqlx::{Postgres, Transaction};
use time::{Duration, OffsetDateTime};
use uuid::Uuid;

use crate::{Error, Result, StructuredFields, structured_fields::StructuredEntity};
use elf_storage::graph;

#[allow(clippy::too_many_arguments)]
pub(crate) async fn persist_graph_fields_tx(
	tx: &mut Transaction<'_, Postgres>,
	tenant_id: &str,
	project_id: &str,
	agent_id: &str,
	scope: &str,
	note_id: Uuid,
	structured: &StructuredFields,
	now: OffsetDateTime,
) -> Result<()> {
	if !structured.has_graph_fields() {
		return Ok(());
	}

	if let Some(entities) = structured.entities.as_ref() {
		for (entity_idx, entity) in entities.iter().enumerate() {
			let base_path = format!("structured.entities[{entity_idx}]");

			upsert_graph_entity_and_aliases(tx, tenant_id, project_id, entity, base_path.as_str())
				.await?;
		}
	}

	let relations = structured.relations.as_deref().unwrap_or_default();

	for (relation_idx, relation) in relations.iter().enumerate() {
		let relation_now = now + Duration::microseconds(relation_idx as i64);
		let relation_path = format!("structured.relations[{relation_idx}]");
		let subject = relation.subject.as_ref().ok_or_else(|| Error::InvalidRequest {
			message: format!("{relation_path}.subject is required."),
		})?;
		let predicate = relation.predicate.as_deref().ok_or_else(|| Error::InvalidRequest {
			message: format!("{relation_path}.predicate is required."),
		})?;
		let subject_entity_id = upsert_graph_entity_and_aliases(
			tx,
			tenant_id,
			project_id,
			subject,
			&format!("{relation_path}.subject"),
		)
		.await?;
		let valid_from = relation.valid_from;
		let valid_to = relation.valid_to;

		if let (Some(valid_from), Some(valid_to)) = (valid_from, valid_to)
			&& valid_to <= valid_from
		{
			return Err(Error::InvalidRequest {
				message: format!("{relation_path}.valid_to must be greater than valid_from."),
			});
		}

		let object = relation.object.as_ref().ok_or_else(|| Error::InvalidRequest {
			message: format!("{relation_path}.object is required."),
		})?;
		let (object_entity_id, object_value) = match (&object.entity, &object.value) {
			(Some(entity), None) => {
				let entity_id = upsert_graph_entity_and_aliases(
					tx,
					tenant_id,
					project_id,
					entity,
					&format!("{relation_path}.object.entity"),
				)
				.await?;

				(Some(entity_id), None)
			},
			(None, Some(value)) => (None, Some(value.as_str())),
			_ => {
				return Err(Error::InvalidRequest {
					message: format!(
						"{relation_path}.object must provide exactly one of entity or value.",
					),
				});
			},
		};
		let predicate_row =
			graph::resolve_or_register_predicate(tx, tenant_id, project_id, predicate)
				.await
				.map_err(|err| Error::Storage { message: err.to_string() })?;

		reject_deprecated_predicate(predicate_row.status.as_str(), relation_path.as_str())?;

		let fact_id = graph::upsert_fact_with_evidence(
			tx,
			tenant_id,
			project_id,
			agent_id,
			scope,
			subject_entity_id,
			predicate,
			predicate_row.predicate_id,
			object_entity_id,
			object_value,
			valid_from,
			valid_to,
			&[note_id],
		)
		.await
		.map_err(|err| Error::Storage { message: err.to_string() })?;
		let is_current_truth = predicate_row.status == "active"
			&& predicate_row.cardinality == "single"
			&& valid_to.is_none()
			&& valid_from.is_some_and(|start| start <= relation_now);

		if is_current_truth {
			graph::supersede_conflicting_active_facts(
				tx,
				tenant_id,
				project_id,
				agent_id,
				scope,
				subject_entity_id,
				predicate_row.predicate_id,
				fact_id,
				note_id,
				valid_from.expect("Current truth has an explicit validity start"),
			)
			.await
			.map_err(|err| Error::Storage { message: err.to_string() })?;
		}
	}

	Ok(())
}

fn reject_deprecated_predicate(status: &str, relation_path: &str) -> Result<()> {
	if status == "deprecated" {
		return Err(Error::InvalidRequest {
			message: format!("{relation_path}.predicate is deprecated and cannot be used."),
		});
	}

	Ok(())
}

async fn upsert_graph_entity_and_aliases(
	tx: &mut Transaction<'_, Postgres>,
	tenant_id: &str,
	project_id: &str,
	entity: &StructuredEntity,
	context_path: &str,
) -> Result<Uuid> {
	let canonical = entity.canonical.as_deref().ok_or_else(|| Error::InvalidRequest {
		message: format!("{context_path}.canonical is required."),
	})?;
	let canonical = canonical.trim();
	let mut surfaces = vec![canonical.to_string()];

	surfaces.extend(entity.aliases.iter().flatten().cloned());
	surfaces.sort();
	surfaces.dedup();

	// One graph identity writer per tenant/project makes alias lookup and insert atomic.
	let identity = serde_json::json!(["graph_entity", tenant_id, project_id]).to_string();
	let digest = blake3::hash(identity.as_bytes());
	let lock = i64::from_be_bytes(digest.as_bytes()[..8].try_into().expect("Eight hash bytes"));

	sqlx::query("SELECT pg_advisory_xact_lock($1)").bind(lock).execute(&mut **tx).await?;

	let mut resolved = None;

	for surface in &surfaces {
		if let Some(existing) =
			graph::resolve_entity_by_surface(tx, tenant_id, project_id, surface).await?
		{
			if resolved.is_some_and(|id| id != existing.entity_id)
				|| matches!((&existing.kind, &entity.kind), (Some(a), Some(b)) if a != b)
			{
				return Err(Error::InvalidRequest {
					message: format!(
						"{context_path}: declared entity surfaces have conflicting identities or kinds."
					),
				});
			}

			resolved = Some(existing.entity_id);
		}
	}

	let entity_id = match resolved {
		Some(id) => {
			graph::upsert_entity_alias(tx, id, canonical).await?;

			id
		},
		None =>
			graph::upsert_entity(tx, tenant_id, project_id, canonical, entity.kind.as_deref())
				.await?,
	};

	if let Some(aliases) = entity.aliases.as_ref() {
		for (alias_idx, alias) in aliases.iter().enumerate() {
			let alias = alias.trim();

			if alias.is_empty() {
				return Err(Error::InvalidRequest {
					message: format!("{context_path}.aliases[{alias_idx}] must not be empty."),
				});
			}

			graph::upsert_entity_alias(tx, entity_id, alias)
				.await
				.map_err(|err| Error::Storage { message: err.to_string() })?;
		}
	}

	Ok(entity_id)
}
