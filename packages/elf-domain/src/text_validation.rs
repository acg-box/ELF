//! Language-neutral text validity. These checks never rewrite source bytes.

use serde_json::Value;

/// Input roles; identifiers additionally exclude invisible directional controls.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TextKind {
	/// Prose, evidence, names, code, and queries in any language.
	NaturalLanguage,
	/// Structured caller identifiers, not human-language classification.
	Identifier,
}

/// Text format failures, independent of language or script.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TextRejectReason {
	/// A control character other than ordinary document whitespace.
	DisallowedControlChar,
	/// An invisible formatting control in an identifier.
	DisallowedIdentifierFormat,
}

/// Validate text without normalization, transliteration, or language detection.
pub fn validate(input: &str, kind: TextKind) -> Result<(), TextRejectReason> {
	for ch in input.chars() {
		if ch.is_control() && !matches!(ch, '\n' | '\r' | '\t') {
			return Err(TextRejectReason::DisallowedControlChar);
		}
		if kind == TextKind::Identifier
			&& matches!(ch,
            '\u{200B}' | '\u{2060}' | '\u{FEFF}' | '\u{202A}'..='\u{202E}' | '\u{2066}'..='\u{2069}')
		{
			return Err(TextRejectReason::DisallowedIdentifierFormat);
		}
	}

	Ok(())
}

/// Whether Unicode natural-language text has a valid storage format.
pub fn is_valid_text(input: &str) -> bool {
	validate(input, TextKind::NaturalLanguage).is_ok()
}

/// Whether an identifier has a valid format, regardless of script.
pub fn is_valid_identifier(input: &str) -> bool {
	validate(input, TextKind::Identifier).is_ok()
}

/// Return the first invalid string's JSON path, preserving the caller's field context.
pub fn find_invalid_path(value: &Value, path: &str) -> Option<String> {
	match value {
		serde_json::Value::String(text) => (!is_valid_text(text)).then(|| path.to_owned()),
		serde_json::Value::Array(items) => items
			.iter()
			.enumerate()
			.find_map(|(i, v)| find_invalid_path(v, &format!("{path}[{i}]"))),
		serde_json::Value::Object(items) => items.iter().find_map(|(k, v)| {
			find_invalid_path(
				v,
				&format!("{path}[\"{}\"]", k.replace('\\', "\\\\").replace('"', "\\\"")),
			)
		}),
		_ => None,
	}
}

#[cfg(test)]
mod tests {
	use crate::text_validation::{self};
	#[test]
	fn languages_and_original_unicode_are_supported() {
		for text in [
			"中文原文",
			"Привет мир",
			"مرحبا بالعالم",
			"Bonjour, voici un texte français.",
			"👩‍💻",
			"می\u{200c}روم",
			"e\u{301}",
			"Ｆｕｌｌｗｉｄｔｈ",
		] {
			assert!(text_validation::is_valid_text(text), "{text}");
		}

		assert!(text_validation::is_valid_identifier("项目甲"));
	}
	#[test]
	fn storage_controls_and_identifier_spoofing_are_separate() {
		assert!(!text_validation::is_valid_text("bad\0text"));
		assert!(!text_validation::is_valid_text("bad\u{7}text"));
		assert!(text_validation::is_valid_text("line\n\tline"));
		assert!(text_validation::is_valid_text("original\u{202e}text"));
		assert!(!text_validation::is_valid_identifier("key\u{202e}suffix"));
	}
}
