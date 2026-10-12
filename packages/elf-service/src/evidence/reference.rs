use blake3::Hash;
use uuid::Uuid;

use crate::{
	docs::{DEFAULT_L2_MAX_BYTES, DocsExcerptsGetRequest, TextPositionSelector},
	evidence::{ClaimCitation, ElfService, Error, EvidenceCheckRequest, Result},
};

impl ElfService {
	pub(super) async fn resolve_evidence_reference(
		&self,
		context: &EvidenceCheckRequest,
		reference: &str,
	) -> Result<ClaimCitation> {
		let invalid = || Error::InvalidRequest { message: "Invalid source reference.".into() };
		let (doc_id, content_hash, start, end) = parse(reference).ok_or_else(invalid)?;
		let excerpt = self
			.docs_excerpts_get(DocsExcerptsGetRequest {
				tenant_id: context.tenant_id.clone(),
				project_id: context.project_id.clone(),
				agent_id: context.agent_id.clone(),
				read_profile: context.read_profile.clone(),
				doc_id,
				level: "L2".into(),
				chunk_id: None,
				quote: None,
				position: Some(TextPositionSelector { start, end }),
				explain: Some(false),
			})
			.await?;

		if !excerpt.verification.verified || excerpt.verification.content_hash != content_hash {
			return Err(invalid());
		}

		let local_start = start.checked_sub(excerpt.start_offset).ok_or_else(invalid)?;
		let local_end = end.checked_sub(excerpt.start_offset).ok_or_else(invalid)?;
		let quote = excerpt.excerpt.get(local_start..local_end).ok_or_else(invalid)?.to_string();

		if quote.trim().is_empty() {
			return Err(invalid());
		}

		Ok(ClaimCitation::Source { doc_id, content_hash, quote })
	}
}

pub(super) fn source_reference(doc_id: Uuid, hash: &str, start: usize, end: usize) -> String {
	format!("elf-source-v1/{doc_id}/{hash}/{start}/{end}")
}

fn parse(reference: &str) -> Option<(Uuid, String, usize, usize)> {
	if reference.len() > 192 {
		return None;
	}

	let parts: Vec<_> = reference.split('/').collect();
	let ["elf-source-v1", id, hash, start, end] = parts.as_slice() else {
		return None;
	};
	let id = Uuid::parse_str(id).ok()?;
	let hash = Hash::from_hex(hash).ok()?.to_hex().to_string();
	let start: usize = start.parse().ok()?;
	let end: usize = end.parse().ok()?;

	if end <= start || end - start > DEFAULT_L2_MAX_BYTES {
		return None;
	}

	Some((id, hash, start, end))
}

#[cfg(test)]
mod tests {
	use uuid::Uuid;

	use crate::{docs::DEFAULT_L2_MAX_BYTES, evidence::reference};

	#[test]
	fn source_locators_are_versioned_bounded_and_hash_guarded() {
		let id = Uuid::new_v4();
		let hash = blake3::hash("白鹭".as_bytes()).to_hex().to_string();

		assert_eq!(
			reference::parse(&reference::source_reference(id, &hash, 3, 9)),
			Some((id, hash.clone(), 3, 9))
		);

		for (start, end) in [(9, 3), (3, 3), (0, DEFAULT_L2_MAX_BYTES + 1)] {
			assert!(
				reference::parse(&reference::source_reference(id, &hash, start, end)).is_none()
			);
		}

		assert!(reference::parse(&reference::source_reference(id, "bad-hash", 0, 9)).is_none());
		assert!(reference::parse("elf-source-v2/x/y/0/9").is_none());
		assert!(
			reference::parse(&format!("{}/extra", reference::source_reference(id, &hash, 0, 9)))
				.is_none()
		);
	}
}
