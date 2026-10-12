use uuid::Uuid;

use crate::{
	access::ORG_PROJECT_ID,
	docs::{DocsExcerptsGetRequest, DocsGetRequest, TextPositionSelector},
	evidence::{
		ElfService, Error, EvidencePackSource, EvidenceRecallRequest, NoteSourceEvidence, Result,
	},
};

impl ElfService {
	pub(super) async fn recall_original_sources(
		&self,
		req: &EvidenceRecallRequest,
		scopes: &[String],
		grants: &[String],
		subjects: &[String],
	) -> Result<(Vec<EvidencePackSource>, bool)> {
		let rows: Vec<(Uuid, i32, i32)> = sqlx::query_as(include_str!("source_recall.sql"))
			.bind(&req.tenant_id)
			.bind(&req.project_id)
			.bind(&req.agent_id)
			.bind(scopes)
			.bind(grants)
			.bind(subjects)
			.bind(ORG_PROJECT_ID)
			.fetch_all(&self.db.pool)
			.await?;
		let mut complete = rows.len() <= 12;
		let mut sources = Vec::new();

		for (doc_id, start, end) in rows.into_iter().take(12) {
			let result =
				self.recall_original_window(req, doc_id, start as usize, end as usize).await;

			match result {
				Ok(source) => sources.push(source),
				Err(
					Error::NotFound { .. }
					| Error::ScopeDenied { .. }
					| Error::InvalidRequest { .. },
				) => complete = false,
				Err(err) => return Err(err),
			}
		}

		Ok((sources, complete))
	}

	async fn recall_original_window(
		&self,
		req: &EvidenceRecallRequest,
		doc_id: Uuid,
		start: usize,
		end: usize,
	) -> Result<EvidencePackSource> {
		let metadata = self
			.docs_get(DocsGetRequest {
				tenant_id: req.tenant_id.clone(),
				project_id: req.project_id.clone(),
				agent_id: req.agent_id.clone(),
				read_profile: req.read_profile.clone(),
				doc_id,
			})
			.await?;
		let excerpt = self
			.docs_excerpts_get(DocsExcerptsGetRequest {
				tenant_id: req.tenant_id.clone(),
				project_id: req.project_id.clone(),
				agent_id: req.agent_id.clone(),
				read_profile: req.read_profile.clone(),
				doc_id,
				level: "L2".into(),
				chunk_id: None,
				quote: None,
				position: Some(TextPositionSelector { start, end }),
				explain: Some(false),
			})
			.await?;

		if !excerpt.verification.verified
			|| excerpt.verification.content_hash != metadata.content_hash
		{
			return Err(Error::InvalidRequest { message: "Source changed during recall.".into() });
		}

		Ok(EvidencePackSource::from_evidence(NoteSourceEvidence { metadata, excerpt }))
	}
}
