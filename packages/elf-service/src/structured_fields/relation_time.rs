//! Relation validity boundaries accept an instant or a civil UTC day boundary.
//!
//! This is a derived graph value. Original timestamp text remains in the source
//! evidence. Other API timestamps continue to require RFC 3339.
use serde::{Deserialize as _, Deserializer, Serializer, de::Error};
use time::{Date, OffsetDateTime, format_description::well_known::Rfc3339, macros};

use crate::time_serde::option;

/// The wire contract shared by extraction instructions and the decoder.
pub(crate) const FORMAT: &str = "RFC 3339 timestamp with timezone, or YYYY-MM-DD interpreted as the start of that UTC day; null if unknown";

pub fn serialize<S>(value: &Option<OffsetDateTime>, serializer: S) -> Result<S::Ok, S::Error>
where
	S: Serializer,
{
	option::serialize(value, serializer)
}

pub fn deserialize<'de, D>(deserializer: D) -> Result<Option<OffsetDateTime>, D::Error>
where
	D: Deserializer<'de>,
{
	let Some(raw) = Option::<String>::deserialize(deserializer)? else {
		return Ok(None);
	};

	if let Ok(instant) = OffsetDateTime::parse(&raw, &Rfc3339) {
		return Ok(Some(instant));
	}

	Date::parse(&raw, macros::format_description!("[year]-[month]-[day]"))
		.map(|date| Some(date.midnight().assume_utc()))
		.map_err(|_| D::Error::custom(format!("relation time must be {FORMAT}")))
}

#[cfg(test)]
mod tests {
	use crate::structured_fields::StructuredRelation;
	#[test]
	fn dates_and_instants_share_a_defined_boundary() {
		let date: StructuredRelation =
			serde_json::from_value(serde_json::json!({"valid_from":"2026-08-01"})).unwrap();
		let instant: StructuredRelation =
			serde_json::from_value(serde_json::json!({"valid_from":"2026-08-01T00:00:00Z"}))
				.unwrap();

		assert_eq!(date.valid_from, instant.valid_from);
		assert_eq!(serde_json::to_value(date).unwrap()["valid_from"], "2026-08-01T00:00:00Z");
	}
	#[test]
	fn malformed_or_ambiguous_times_are_not_guessed() {
		for value in ["2026-02-30", "08/01/2026", "2026-08-01T10:00:00", "yesterday", ""] {
			assert!(
				serde_json::from_value::<StructuredRelation>(
					serde_json::json!({"valid_from":value})
				)
				.is_err(),
				"{value}"
			);
		}
	}
}
