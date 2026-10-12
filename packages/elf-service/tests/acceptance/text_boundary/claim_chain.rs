use crate::acceptance::text_boundary::setup;
use elf_service::{
	DocsPutRequest,
	evidence::{ClaimCitation, ClaimEvidence, ClaimState, EvidenceCheckRequest},
};

#[tokio::test]
#[ignore = "Requires external Postgres and Qdrant."]
async fn claim_chains_preserve_bridges_bound_growth_and_recheck_access() {
	let Some(fixture) =
		setup::setup_service_with_payload("claim_chain", serde_json::json!({"notes":[]})).await
	else {
		return;
	};
	let service = &fixture.service;
	let mut citations = Vec::new();

	for content in ["Cobalt is operated by Ivo.", "Ivo retained BATCH at the August 8 review."] {
		let doc = service
			.docs_put(DocsPutRequest {
				tenant_id: "t".into(),
				project_id: "p".into(),
				agent_id: "a".into(),
				scope: "agent_private".into(),
				doc_type: None,
				title: None,
				write_policy: None,
				source_ref: serde_json::json!({"schema":"doc_source_ref/v1","doc_type":"knowledge","ts":"2026-08-08T00:00:00Z"}),
				content: content.into(),
			})
			.await
			.expect("Store original");

		citations.push(ClaimCitation::Source {
			doc_id: doc.doc_id,
			content_hash: doc.content_hash,
			quote: content.into(),
		});
	}

	let claims = vec![
		ClaimEvidence {
			text: "Ivo operates Cobalt.".into(),
			state: ClaimState::Supported,
			citations: vec![citations[0].clone()],
			depends_on: vec![],
		},
		ClaimEvidence {
			text: "Cobalt retained BATCH.".into(),
			state: ClaimState::Supported,
			citations: vec![citations[1].clone()],
			depends_on: vec![0],
		},
		ClaimEvidence {
			text: "Cobalt did not change mode.".into(),
			state: ClaimState::Supported,
			citations: vec![],
			depends_on: vec![0, 1, 1],
		},
	];
	let request = EvidenceCheckRequest {
		tenant_id: "t".into(),
		project_id: "p".into(),
		agent_id: "a".into(),
		read_profile: "private_plus_project".into(),
		claims,
	};
	let result = service.evidence_check(request.clone()).await.expect("Check chain");

	assert!(result.claims.iter().all(|c| c.binding_verified));
	assert_eq!(
		result.claims[1].resolved_citations,
		vec![Some(citations[1].clone()), Some(citations[0].clone())]
	);
	assert_eq!(result.claims[1].citation_claim_indices, vec![1, 0]);
	assert_eq!(result.claims[2].resolved_citations.len(), 2);
	assert_eq!(result.claims[2].citation_claim_indices, vec![0, 1]);

	let legacy = serde_json::to_value(&result.claims[0]).expect("Serialize legacy binding");

	assert!(legacy.get("citation_claim_indices").is_none());

	for invalid in [0, 1, 100] {
		let mut bad = request.clone();

		bad.claims[0].depends_on = vec![invalid];

		assert!(service.evidence_check(bad).await.is_err());
	}

	let mut inaccessible = request.clone();

	inaccessible.agent_id = "other".into();

	let checked = service.evidence_check(inaccessible).await.expect("Reject inaccessible chain");

	assert!(checked.claims.iter().all(|c| !c.binding_verified));
	assert_eq!(checked.claims[2].resolved_citations, vec![None, None]);

	let mut dense = request.clone();

	dense.agent_id = "other".into();
	dense.claims = (0..12)
		.map(|index| ClaimEvidence {
			text: "Inaccessible premise.".into(),
			state: ClaimState::Supported,
			citations: vec![citations[0].clone(); 8],
			depends_on: (0..index).collect(),
		})
		.collect();

	let checked = service.evidence_check(dense).await.expect("Bound dense invalid chain");

	assert_eq!(checked.claims[11].resolved_citations.len(), 96);
	assert!(!checked.claims[11].binding_verified);

	if let ClaimCitation::Source { doc_id, .. } = citations[0] {
		sqlx::query("UPDATE doc_documents SET status='deleted' WHERE doc_id=$1")
			.bind(doc_id)
			.execute(&service.db.pool)
			.await
			.expect("Delete source");
	}

	let checked = service.evidence_check(request).await.expect("Recheck current source access");

	assert!(checked.claims.iter().all(|c| !c.binding_verified));
}
