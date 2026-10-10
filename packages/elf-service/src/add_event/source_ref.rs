use serde_json::Value;

use crate::{
	Error, Result,
	add_event::types::{EventMessage, EvidenceQuote},
};
use elf_domain::writegate::WritePolicyAudit;

/// Attach caller source identity and exact input hashes without copying the transcript.
pub(super) fn evidence_sources(
	messages: &[EventMessage],
	extraction_texts: &[String],
	evidence: &[EvidenceQuote],
	audits: Option<&[WritePolicyAudit]>,
) -> Result<Vec<Value>> {
	evidence
		.iter()
		.map(|quote| {
			let index = quote.message_index;
			let (message, extraction_text) = messages
				.get(index)
				.zip(extraction_texts.get(index))
				.ok_or_else(|| Error::InvalidRequest {
				message: "Evidence source message is missing.".to_string(),
			})?;
			let audit = if message.write_policy.is_some() {
				// Policy audits contain only messages that supplied a policy, in input order.
				let audit_index =
					messages[..index].iter().filter(|m| m.write_policy.is_some()).count();

				Some(audits.and_then(|items| items.get(audit_index)).ok_or_else(|| {
					Error::InvalidRequest {
						message: "Evidence source write-policy audit is missing.".to_string(),
					}
				})?)
			} else {
				None
			};

			Ok(serde_json::json!({
				"message_index": index,
				"quote": quote.quote,
				"source": {
					"schema": "elf.event_source/v1",
					"message_id": message.msg_id,
					"role": message.role,
					"timestamp": message.ts,
					"hash_algorithm": "blake3",
					"content_hash": blake3::hash(message.content.as_bytes()).to_hex().to_string(),
					"extraction_content_hash": blake3::hash(extraction_text.as_bytes()).to_hex().to_string(),
					"write_policy_audit": audit,
				}
			}))
		})
		.collect()
}

#[cfg(test)] mod tests;
