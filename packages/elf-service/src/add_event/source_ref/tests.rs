use std::slice;

use uuid::Uuid;

use crate::{
	EventSourceDocument,
	add_event::{
		source_ref,
		types::{EventMessage, EvidenceQuote},
	},
	docs::TextPositionSelector,
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
			source_document: None,
			write_policy: None,
		},
		EventMessage {
			role: "user".to_string(),
			content: raw.to_string(),
			ts: Some("2026-10-01".to_string()),
			msg_id: Some("原文-2".to_string()),
			source_document: None,
			write_policy: Some(policy),
		},
	];
	let refs = source_ref::evidence_sources(
		&messages,
		&["untouched".to_string(), transformed.transformed.clone()],
		&[EvidenceQuote {
			position: None,
			message_index: 1,
			quote: transformed.transformed.clone(),
		}],
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

#[test]
fn selected_occurrence_keeps_its_original_byte_position() {
	let message = EventMessage {
		role: "user".into(),
		content: "same\nsame\n".into(),
		ts: None,
		msg_id: None,
		write_policy: None,
		source_document: Some(EventSourceDocument {
			doc_id: Uuid::nil(),
			content_hash: "hash".into(),
			position: TextPositionSelector { start: 100, end: 110 },
		}),
	};
	let evidence = EvidenceQuote {
		message_index: 0,
		quote: "same\n".into(),
		position: Some(TextPositionSelector { start: 5, end: 10 }),
	};
	let refs =
		source_ref::evidence_sources(&[message], &["same\nsame\n".into()], &[evidence], None)
			.expect("Exact repeated occurrence");

	assert_eq!(
		refs[0]["source"]["document"]["locator"]["position"],
		serde_json::json!({"start":105,"end":110})
	);
	assert_eq!(refs[0]["source"]["extraction_position"], serde_json::json!({"start":5,"end":10}));
}
