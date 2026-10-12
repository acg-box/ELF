//! Bind event provenance to an existing immutable source without copying it.
use sqlx::PgConnection;

use crate::{
	ElfService, Error, Result, access,
	add_event::{AddEventRequest, EventMessage, EventSourceDocument},
	docs::excerpts,
};

impl ElfService {
	pub(crate) async fn validate_event_source_document(
		&self,
		tx: &mut PgConnection,
		req: &AddEventRequest,
		note_scope: &str,
		message: &EventMessage,
		source: &EventSourceDocument,
	) -> Result<()> {
		let doc = excerpts::load_doc_document_for_read(
			&mut *tx,
			source.doc_id,
			&req.tenant_id,
			&req.project_id,
		)
		.await?
		.ok_or_else(|| Error::NotFound { message: "Source document not found.".into() })?;
		let scopes = vec![note_scope.to_string()];
		let grants = access::load_shared_read_grants_with_org_shared(
			&mut *tx,
			&req.tenant_id,
			&req.project_id,
			&req.agent_id,
			note_scope == "org_shared",
		)
		.await?;

		if doc.status != "active"
			|| !excerpts::doc_read_allowed(
				&req.agent_id,
				&scopes,
				&grants,
				&doc.agent_id,
				&doc.scope,
			) {
			return Err(Error::NotFound {
				message: "Source document not found in the note scope.".into(),
			});
		}
		if source.content_hash != doc.content_hash
			|| source.position.start >= source.position.end
			|| doc.content.get(source.position.start..source.position.end)
				!= Some(message.content.as_str())
		{
			return Err(Error::InvalidRequest {
				message: "Source document hash or original message byte span does not match."
					.into(),
			});
		}

		Ok(())
	}
}
