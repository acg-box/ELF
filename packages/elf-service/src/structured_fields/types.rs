use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

/// Structured note fields emitted by extraction and stored alongside a note.
#[derive(Clone, Debug, Default, Deserialize, JsonSchema, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StructuredFields {
	/// Optional one-paragraph summary.
	pub summary: Option<String>,
	/// Each fact must be a verbatim substring of note text or an evidence quote; do not
	/// paraphrase.
	pub facts: Option<Vec<String>>,
	/// Optional concept labels grounded in the note text.
	pub concepts: Option<Vec<String>>,
	/// Optional graph entities extracted from the note.
	pub entities: Option<Vec<StructuredEntity>>,
	/// Optional graph relations extracted from the note.
	pub relations: Option<Vec<StructuredRelation>>,
}
impl StructuredFields {
	/// Returns `true` when no persisted summary, fact, or concept content is present.
	pub fn is_effectively_empty(&self) -> bool {
		let summary_empty = self.summary.as_ref().map(|v| v.trim().is_empty()).unwrap_or(true);
		let facts_empty = self
			.facts
			.as_ref()
			.map(|items| items.iter().all(|v| v.trim().is_empty()))
			.unwrap_or(true);
		let concepts_empty = self
			.concepts
			.as_ref()
			.map(|items| items.iter().all(|v| v.trim().is_empty()))
			.unwrap_or(true);

		summary_empty && facts_empty && concepts_empty
	}

	/// Returns `true` when graph entities or relations are present.
	pub fn has_graph_fields(&self) -> bool {
		self.entities.as_ref().is_some_and(|entities| !entities.is_empty())
			|| self.relations.as_ref().is_some_and(|relations| !relations.is_empty())
	}
}

/// One extracted entity candidate.
#[derive(Clone, Debug, Default, Deserialize, JsonSchema, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StructuredEntity {
	/// Canonical surface for the entity, copied from the note or evidence.
	#[schemars(required)]
	pub canonical: Option<String>,
	/// Optional entity kind such as person or organization.
	pub kind: Option<String>,
	/// Optional alternate surfaces for the entity.
	pub aliases: Option<Vec<String>>,
}

/// One extracted relation candidate.
#[derive(Clone, Debug, Default, Deserialize, JsonSchema, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct StructuredRelation {
	/// Relation subject entity directly with canonical/kind/aliases, never an entity wrapper.
	#[schemars(required)]
	pub subject: Option<StructuredEntity>,
	/// Predicate copied verbatim from note text or an evidence quote; do not invent a normalized
	/// label.
	#[schemars(required)]
	pub predicate: Option<String>,
	/// Object must contain exactly one non-null entity or value, copied from note text or
	/// evidence.
	#[schemars(required)]
	pub object: Option<StructuredRelationObject>,
	#[serde(with = "crate::structured_fields::relation_time")]
	#[schemars(with = "Option<String>", description = crate::structured_fields::relation_time::FORMAT)]
	/// Optional validity-window start.
	pub valid_from: Option<OffsetDateTime>,
	#[serde(with = "crate::structured_fields::relation_time")]
	#[schemars(with = "Option<String>", description = crate::structured_fields::relation_time::FORMAT)]
	/// Optional validity-window end.
	pub valid_to: Option<OffsetDateTime>,
}

/// Extracted relation object.
#[derive(Clone, Debug, Default, Deserialize, JsonSchema, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StructuredRelationObject {
	/// Entity-shaped object value.
	pub entity: Option<StructuredEntity>,
	/// Scalar object value.
	pub value: Option<String>,
}
