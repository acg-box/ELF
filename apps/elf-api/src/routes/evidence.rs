use serde::Deserialize;

use crate::routes::{self, ApiError, AppState, HeaderMap, Json, Path, RequestContext, State, Uuid};
use elf_service::{
	NoteFetchRequest,
	evidence::{
		ClaimEvidence, EvidenceCheckRequest, EvidenceCheckResponse, EvidencePackRequest,
		EvidencePackResponse, EvidenceRecallRequest, EvidenceRecallResponse, NoteEvidenceResponse,
	},
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct PackBody {
	note_ids: Vec<Uuid>,
	max_source_bytes: Option<usize>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct CheckBody {
	claims: Vec<ClaimEvidence>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct RecallBody {
	subjects: Vec<String>,
	as_of: Option<String>,
}

#[utoipa::path(get, path = "/v2/notes/{note_id}/evidence", tag = "notes", params(("note_id" = Uuid, Path, description = "Note ID.")), responses((status = 200, description = "Derived note and bounded verified original context.", body = Value)))]
pub(super) async fn note_evidence(
	State(state): State<AppState>,
	headers: HeaderMap,
	Path(note_id): Path<Uuid>,
) -> Result<Json<NoteEvidenceResponse>, ApiError> {
	let ctx = RequestContext::from_headers(&headers)?;
	let read_profile = routes::required_read_profile(&headers)?;

	Ok(Json(
		state
			.service
			.note_evidence(
				NoteFetchRequest {
					tenant_id: ctx.tenant_id,
					project_id: ctx.project_id,
					agent_id: ctx.agent_id,
					note_id,
				},
				read_profile,
			)
			.await?,
	))
}

#[utoipa::path(post, path = "/v2/evidence/check", tag = "notes", request_body = Value, responses((status = 200, description = "Quote bindings only; semantic support is not evaluated.", body = Value)))]
pub(super) async fn evidence_check(
	State(state): State<AppState>,
	headers: HeaderMap,
	Json(body): Json<CheckBody>,
) -> Result<Json<EvidenceCheckResponse>, ApiError> {
	let ctx = RequestContext::from_headers(&headers)?;
	let read_profile = routes::required_read_profile(&headers)?;

	Ok(Json(
		state
			.service
			.evidence_check(EvidenceCheckRequest {
				tenant_id: ctx.tenant_id,
				project_id: ctx.project_id,
				agent_id: ctx.agent_id,
				read_profile,
				claims: body.claims,
			})
			.await?,
	))
}

#[utoipa::path(post, path = "/v2/evidence/pack", tag = "notes", request_body = Value, responses((status = 200, description = "Derived notes and bounded original context with native citations.", body = Value)))]
pub(super) async fn evidence_pack(
	State(state): State<AppState>,
	headers: HeaderMap,
	Json(body): Json<PackBody>,
) -> Result<Json<EvidencePackResponse>, ApiError> {
	let ctx = RequestContext::from_headers(&headers)?;
	let read_profile = routes::required_read_profile(&headers)?;

	Ok(Json(
		state
			.service
			.evidence_pack(EvidencePackRequest {
				tenant_id: ctx.tenant_id,
				project_id: ctx.project_id,
				agent_id: ctx.agent_id,
				read_profile,
				note_ids: body.note_ids,
				max_source_bytes: body.max_source_bytes,
			})
			.await?,
	))
}

#[utoipa::path(post, path = "/v2/evidence/recall", tag = "notes", request_body = Value, responses((status = 200, description = "Source-diverse lexical and graph evidence candidates.", body = Value)))]
pub(super) async fn evidence_recall(
	State(state): State<AppState>,
	headers: HeaderMap,
	Json(body): Json<RecallBody>,
) -> Result<Json<EvidenceRecallResponse>, ApiError> {
	let ctx = RequestContext::from_headers(&headers)?;
	let read_profile = routes::required_read_profile(&headers)?;

	Ok(Json(
		state
			.service
			.evidence_recall(EvidenceRecallRequest {
				tenant_id: ctx.tenant_id,
				project_id: ctx.project_id,
				agent_id: ctx.agent_id,
				read_profile,
				subjects: body.subjects,
				as_of: routes::parse_optional_rfc3339(body.as_of.as_ref(), "as_of")?,
			})
			.await?,
	))
}

#[cfg(test)]
mod tests {
	use crate::routes::evidence::RecallBody;

	#[test]
	fn recall_time_is_optional_at_the_http_boundary() {
		let body: RecallBody = serde_json::from_value(serde_json::json!({"subjects":["Cedar"]}))
			.expect("Omitted optional time");

		assert!(body.as_of.is_none());
	}
}
