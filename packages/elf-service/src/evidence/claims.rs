use crate::{
	docs::{DocsExcerptsGetRequest, TextQuoteSelector},
	evidence::{
		ClaimBinding, ClaimCitation, ClaimState, ElfService, Error, EvidenceCheckRequest,
		EvidenceCheckResponse, MAX_CITATIONS, MAX_CLAIMS, NoteFetchRequest, Result,
	},
	search,
};

impl ElfService {
	/// Verify current access, source hashes, and exact quotes without claiming semantic entailment.
	pub async fn evidence_check(&self, req: EvidenceCheckRequest) -> Result<EvidenceCheckResponse> {
		search::resolve_read_profile_scopes(&self.cfg, &req.read_profile)?;

		let claims = &req.claims;

		if claims.is_empty()
			|| claims.len() > MAX_CLAIMS
			|| claims.iter().any(|claim| {
				claim.text.trim().is_empty()
					|| claim.text.len() > 8_192
					|| claim.citations.len() > MAX_CITATIONS
			}) {
			return Err(Error::InvalidRequest {
				message: "Supply 1 to 12 nonempty claims, at most 8192 bytes and 8 citations each."
					.into(),
			});
		}

		let mut bindings = Vec::new();

		for (claim_index, claim) in claims.iter().enumerate() {
			let mut citation_verified = Vec::new();

			for citation in &claim.citations {
				let resolved = self.verify_claim_citation(&req, citation).await;
				let verified = match resolved {
					Ok(verified) => verified,
					Err(
						Error::NotFound { .. }
						| Error::InvalidRequest { .. }
						| Error::ScopeDenied { .. },
					) => false,
					Err(error) => return Err(error),
				};

				citation_verified.push(verified);
			}

			let enough = match claim.state {
				ClaimState::Unknown => true,
				ClaimState::Conflict => claim.citations.len() >= 2,
				_ => !claim.citations.is_empty(),
			};
			let binding_verified = enough && citation_verified.iter().all(|verified| *verified);

			bindings.push(ClaimBinding { claim_index, citation_verified, binding_verified });
		}

		Ok(EvidenceCheckResponse { claims: bindings, semantic_support: "not_evaluated" })
	}

	async fn verify_claim_citation(
		&self,
		context: &EvidenceCheckRequest,
		citation: &ClaimCitation,
	) -> Result<bool> {
		let quote = match citation {
			ClaimCitation::Note { quote, .. } | ClaimCitation::Source { quote, .. } => quote,
		};

		if quote.trim().is_empty() || quote.len() > 8_192 {
			return Ok(false);
		}

		match citation {
			ClaimCitation::Note { note_id, quote } => {
				let note = self
					.get_note(NoteFetchRequest {
						tenant_id: context.tenant_id.clone(),
						project_id: context.project_id.clone(),
						agent_id: context.agent_id.clone(),
						note_id: *note_id,
					})
					.await?;

				Ok(search::resolve_read_profile_scopes(&self.cfg, &context.read_profile)?
					.contains(&note.scope)
					&& note.text.contains(quote))
			},
			ClaimCitation::Source { doc_id, content_hash, quote } => {
				let excerpt = self
					.docs_excerpts_get(DocsExcerptsGetRequest {
						tenant_id: context.tenant_id.clone(),
						project_id: context.project_id.clone(),
						agent_id: context.agent_id.clone(),
						read_profile: context.read_profile.clone(),
						doc_id: *doc_id,
						level: "L2".into(),
						chunk_id: None,
						position: None,
						quote: Some(TextQuoteSelector {
							exact: quote.clone(),
							prefix: None,
							suffix: None,
						}),
						explain: Some(false),
					})
					.await?;

				Ok(excerpt.verification.verified
					&& excerpt.verification.content_hash == *content_hash
					&& excerpt.excerpt.contains(quote))
			},
		}
	}
}
