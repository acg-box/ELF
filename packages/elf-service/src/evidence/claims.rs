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
		// Backward-only edges give a bounded topological order without a graph store.
		if claims.iter().enumerate().any(|(i, claim)| {
			claim.depends_on.len() > MAX_CLAIMS
				|| claim.depends_on.iter().any(|&dependency| dependency >= i)
		}) {
			return Err(Error::InvalidRequest {
				message: "Claim dependencies must refer to earlier claim indices.".into(),
			});
		}

		let mut bindings: Vec<ClaimBinding> = Vec::new();

		for (claim_index, claim) in claims.iter().enumerate() {
			let mut citation_verified = Vec::new();
			let mut resolved_citations = Vec::new();

			for citation in &claim.citations {
				let resolved = match citation {
					ClaimCitation::Reference { reference } =>
						self.resolve_evidence_reference(&req, reference).await.map(Some),
					_ => self
						.verify_claim_citation(&req, citation)
						.await
						.map(|verified| verified.then(|| citation.clone())),
				};
				let verified = match resolved {
					Ok(resolved) => resolved,
					Err(
						Error::NotFound { .. }
						| Error::InvalidRequest { .. }
						| Error::ScopeDenied { .. },
					) => None,
					Err(error) => return Err(error),
				};

				citation_verified.push(verified.is_some());
				resolved_citations.push(verified);
			}

			let dependencies_bound = claim.depends_on.iter().all(|&d| bindings[d].binding_verified);
			let mut citation_claim_indices = Vec::new();

			if !claim.depends_on.is_empty() {
				citation_claim_indices.resize(resolved_citations.len(), claim_index);

				let mut required = [false; MAX_CLAIMS];

				for &dependency in &claim.depends_on {
					required[dependency] = true;
				}
				for dependency in (0..claim_index).rev() {
					if required[dependency] {
						for &parent in &claims[dependency].depends_on {
							required[parent] = true;
						}
					}
				}
				for dependency in 0..claim_index {
					if !required[dependency] {
						continue;
					}

					let prior = &bindings[dependency];

					// Read only each premise's direct slots. Diamond paths and invalid
					// citations must not multiply the bounded 12-by-8 input.
					for (index, citation) in prior
						.resolved_citations
						.iter()
						.take(claims[dependency].citations.len())
						.enumerate()
					{
						if citation.is_some() && resolved_citations.contains(citation) {
							continue;
						}

						resolved_citations.push(citation.clone());
						citation_verified.push(prior.citation_verified[index]);
						citation_claim_indices.push(dependency);
					}
				}
			}

			let enough = match claim.state {
				ClaimState::Unknown => true,
				ClaimState::Conflict => resolved_citations.len() >= 2,
				_ => !resolved_citations.is_empty(),
			};
			let binding_verified =
				dependencies_bound && enough && citation_verified.iter().all(|verified| *verified);

			bindings.push(ClaimBinding {
				citation_claim_indices,
				claim_index,
				citation_verified,
				binding_verified,
				resolved_citations,
			});
		}

		Ok(EvidenceCheckResponse { claims: bindings, semantic_support: "not_evaluated" })
	}

	async fn verify_claim_citation(
		&self,
		context: &EvidenceCheckRequest,
		citation: &ClaimCitation,
	) -> Result<bool> {
		let quote = match citation {
			ClaimCitation::Reference { .. } => return Ok(false),
			ClaimCitation::Note { quote, .. } | ClaimCitation::Source { quote, .. } => quote,
		};

		if quote.trim().is_empty() || quote.len() > 8_192 {
			return Ok(false);
		}

		match citation {
			ClaimCitation::Reference { .. } => Ok(false),
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
						max_bytes: None,
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
