use std::slice;

use crate::add_event::{
	source_ref,
	types::{EventMessage, EvidenceQuote},
};
use elf_domain::writegate::{self, WritePolicy, WriteSpan};

#[test]
fn evidence_retains_original_identity_and_the_correct_transform_audit() {
	let raw = "公开 机密 保留";
	let start = raw.find("机密").expect("Find excluded text");
	let policy = WritePolicy {
		exclusions: vec![WriteSpan { start, end: start + "机密".len() }],
		redactions: vec![],
	};
	let transformed = writegate::apply_write_policy(raw, Some(&policy)).expect("Apply policy");
	let messages = vec![
		EventMessage {
			role: "user".to_string(),
			content: "untouched".to_string(),
			ts: None,
			msg_id: None,
			write_policy: None,
		},
		EventMessage {
			role: "user".to_string(),
			content: raw.to_string(),
			ts: Some("2026-10-01".to_string()),
			msg_id: Some("原文-2".to_string()),
			write_policy: Some(policy),
		},
	];
	let refs = source_ref::evidence_sources(
		&messages,
		&["untouched".to_string(), transformed.transformed.clone()],
		&[EvidenceQuote { message_index: 1, quote: transformed.transformed.clone() }],
		Some(slice::from_ref(&transformed.audit)),
	)
	.expect("Bind source metadata");
	let source = &refs[0]["source"];

	assert_eq!(refs[0]["quote"], "公开  保留");
	assert_eq!(source["message_id"], "原文-2");
	assert_eq!(source["timestamp"], "2026-10-01");
	assert_eq!(source["content_hash"], blake3::hash(raw.as_bytes()).to_hex().to_string());
	assert_eq!(
		source["extraction_content_hash"],
		blake3::hash(transformed.transformed.as_bytes()).to_hex().to_string()
	);
	assert_ne!(source["content_hash"], source["extraction_content_hash"]);
	assert_eq!(
		source["write_policy_audit"],
		serde_json::to_value(transformed.audit).expect("Serialize audit")
	);
	assert_eq!(messages[1].content, raw);
}
