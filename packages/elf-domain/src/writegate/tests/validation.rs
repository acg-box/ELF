use crate::writegate::{self, NoteInput, RejectCode, tests::config};

#[test]
fn rejects_long_text() {
	let cfg = config::config();
	let note = NoteInput {
		note_type: "fact".to_string(),
		scope: "agent_private".to_string(),
		text: "12345678901".to_string(),
	};

	assert_eq!(writegate::writegate(&note, &cfg), Err(RejectCode::RejectTooLong));
}

#[test]
fn rejects_invalid_type() {
	let cfg = config::config();
	let note = NoteInput {
		note_type: "other".to_string(),
		scope: "agent_private".to_string(),
		text: "hello".to_string(),
	};

	assert_eq!(writegate::writegate(&note, &cfg), Err(RejectCode::RejectInvalidType));
}

#[test]
fn detects_secret_patterns() {
	assert!(writegate::contains_secrets("password: hunter2"));
}

#[test]
fn accepts_source_code_environment_references_without_changing_originals() {
	for source in [
		"const token = requiredString(process.env['GH_TOKEN'], 'GH_TOKEN');",
		"const api_key = process.env.API_KEY;",
		"GH_TOKEN: ${{ github.token }}",
		"secret = ${SERVICE_SECRET}",
		"let password = std::env::var(\"PASSWORD\")?;",
		"token = os.environ['TOKEN']",
		"jsonwebtoken = { version = \"~11.0\" }",
	] {
		assert!(!writegate::contains_secrets(source), "Non-secret source was rejected: {source}");
	}
}

#[test]
fn environment_reference_exemption_does_not_accept_literal_or_fallback_secrets() {
	for source in [
		"API_KEY = private-value",
		"GH_TOKEN: actual-credential",
		"token = 'process.env.TOKEN'",
		"token = process.env.TOKEN || 'actual-credential'",
		"token = process.env.TOKEN; password = hunter2",
		"token = requiredString(process.env.TOKEN, 'actual-credential');",
		"sk-abcdefghijklmnopqrstuvwxyz",
	] {
		assert!(writegate::contains_secrets(source), "Secret-like source was accepted: {source}");
	}
}

#[test]
fn accepts_generated_tokens_and_keyword_references_in_real_source() {
	for source in [
		"token = secrets.token_hex(24)",
		"token = secrets.token_urlsafe()",
		"env.update(LITELLM_API_KEY=token, LITELLM_BASE_URL=base,\n    OPENAI_API_KEY=token)",
		include_str!("../../../../../scripts/benchmark_budget.py"),
	] {
		assert!(!writegate::contains_secrets(source), "Runtime source was rejected.");
	}
}

#[test]
fn runtime_expressions_do_not_hide_literal_credentials() {
	for source in [
		"password: hunter2",
		"token = hunter2",
		"env.update(API_KEY='hunter2')",
		"env.update(API_KEY=token, PASSWORD='hunter2')",
		"env.update(API_KEY=token,\n    PASSWORD='hunter2')",
		"token = secrets.token_hex(24) or 'hunter2'",
		"token = secrets.token_hex('hunter2')",
		"token = unknown_generator(24)",
		"env.update(API_KEY=token + 'hunter2')",
		"env.update(API_KEY=token); password = hunter2",
		"env.update(API_KEY=token, SECRET=sk-abcdefghijklmnopqrstuvwxyz)",
	] {
		assert!(writegate::contains_secrets(source), "Secret-like source was accepted: {source}");
	}
}
