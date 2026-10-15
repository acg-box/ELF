use crate::writegate::Regex;

/// Returns whether the input appears to contain secret material.
pub fn contains_secrets(text: &str) -> bool {
	let patterns = [
		r"(?i)-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----",
		r"(?i)ssh-rsa",
		r"(?i)sk-[a-z0-9]{20,}",
		r"(?i)seed phrase",
	];

	for pattern in patterns {
		if Regex::new(pattern).map(|re| re.is_match(text)).unwrap_or(false) {
			return true;
		}
	}

	let Ok(assignments) =
		Regex::new(r"(?i)(?:\b|_)(?:api[_-]?key|password|secret|token)[\t ]*(?P<op>[:=])[\t ]*")
	else {
		return false;
	};

	// Do not consume a value: a second assignment on the same line needs its own
	// check even when the first one is a recognized runtime expression.
	assignments.captures_iter(text).any(|capture| {
		let assignment = capture.get(0).expect("A capture has a complete match.");
		let value = text[assignment.end()..].lines().next().unwrap_or_default();

		!is_environment_reference(value)
			&& !is_generated_token(value)
			&& !is_keyword_reference(text, assignment.start(), &capture["op"], value)
	})
}

fn is_generated_token(value: &str) -> bool {
	// These calls contain a size, not a credential. Unknown functions, string
	// arguments, fallbacks, and appended expressions retain the conservative check.
	Regex::new(r"^secrets\.token_(?:hex|urlsafe|bytes)\([\t ]*[0-9]*[\t ]*\)[\t ]*$")
		.map(|re| re.is_match(value))
		.unwrap_or(false)
}

fn is_keyword_reference(text: &str, start: usize, operator: &str, value: &str) -> bool {
	if operator != "=" {
		return false;
	}

	// A bare identifier after `password:` could be a real unquoted secret. Only
	// recognize a keyword argument: `(API_KEY=token, ...)` or `, API_KEY=token)`.
	// Walk over the name prefix because the credential match can start at `_`.
	let prefix = text[..start].trim_end_matches(|c: char| c.is_ascii_alphanumeric() || c == '_');

	if !prefix.trim_end().ends_with(['(', ',']) {
		return false;
	}

	Regex::new(r"^[A-Za-z_][A-Za-z0-9_]*[\t ]*[,)]").map(|re| re.is_match(value)).unwrap_or(false)
}

fn is_environment_reference(value: &str) -> bool {
	// Only complete references are exempt. Literals, fallbacks, concatenation, and
	// trailing expressions still pass through the conservative assignment check.
	let pattern = r#"(?x)^\s*(?:
		process\.env(?:\.[A-Za-z_][A-Za-z0-9_]*|\[['"][A-Za-z_][A-Za-z0-9_]*['"]\])
		|requiredString\(\s*process\.env(?:\.[A-Za-z_][A-Za-z0-9_]*|\[['"][A-Za-z_][A-Za-z0-9_]*['"]\])\s*,\s*['"][A-Z_][A-Z0-9_]*['"]\s*\)
		|\$\{\{\s*(?:secrets|vars|github|env)\.[A-Za-z_][A-Za-z0-9_.]*\s*\}\}
		|\$\{[A-Za-z_][A-Za-z0-9_]*\}
		|(?:std::)?env::var\(\s*"[A-Za-z_][A-Za-z0-9_]*"\s*\)\??
		|os\.environ\[['"][A-Za-z_][A-Za-z0-9_]*['"]\]
	)\s*;?\s*$"#;

	Regex::new(pattern).map(|reference| reference.is_match(value)).unwrap_or(false)
}
