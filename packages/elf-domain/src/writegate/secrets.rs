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

	let Ok(assignments) = Regex::new(
		r"(?i)(?:\b|_)(?:api[_-]?key|password|secret|token)\s*[:=]\s*(?P<value>[^\r\n]+)",
	) else {
		return false;
	};

	assignments.captures_iter(text).any(|capture| !is_environment_reference(&capture["value"]))
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
