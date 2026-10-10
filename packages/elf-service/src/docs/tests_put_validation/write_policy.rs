use crate::docs::{self, DocType, DocsPutRequest, Error};
use elf_domain::writegate::{WritePolicy, WriteSpan};

#[test]
fn validate_docs_put_rejects_source_rewriting() {
	let err = docs::validate_docs_put(&DocsPutRequest {
		tenant_id: "t".to_string(),
		project_id: "p".to_string(),
		agent_id: "a".to_string(),
		scope: "project_shared".to_string(),
		doc_type: Some(DocType::Knowledge.as_str().to_string()),
		title: None,
		write_policy: Some(WritePolicy {
			exclusions: vec![WriteSpan { start: 6, end: 35 }],
			redactions: vec![],
		}),
		source_ref: serde_json::json!({
			"schema": "doc_source_ref/v1",
			"doc_type": "knowledge",
			"ts": "2026-02-25T12:00:00Z",
		}),
		content: "Hello sk-abcdefghijklmnopqrstuvwxyz!".to_string(),
	})
	.expect_err("Source bytes must not be rewritten.");

	assert!(matches!(err, Error::InvalidRequest { message } if message.contains("immutable")));
}

#[test]
fn validate_docs_put_rejects_secret_after_write_policy() {
	let err = docs::validate_docs_put(&DocsPutRequest {
		tenant_id: "t".to_string(),
		project_id: "p".to_string(),
		agent_id: "a".to_string(),
		scope: "project_shared".to_string(),
		doc_type: Some(DocType::Knowledge.as_str().to_string()),
		title: None,
		write_policy: Some(WritePolicy { exclusions: vec![], redactions: vec![] }),
		source_ref: serde_json::json!({
			"schema": "doc_source_ref/v1",
			"doc_type": "knowledge",
			"ts": "2026-02-25T12:00:00Z",
		}),
		content: "Hello sk-abcdefghijklmnopqrstuvwxyz!".to_string(),
	})
	.expect_err("Expected secret-bearing content to be rejected.");

	match err {
		Error::InvalidRequest { message } => assert!(message.contains("contains secrets")),
		other => panic!("Unexpected error: {other:?}"),
	}
}
