use crate::{
	add_note::validation::invalid_text,
	structured_fields::{
		StructuredEntity, StructuredFields, StructuredRelation, StructuredRelationObject,
	},
};

#[test]
fn source_ref_path_escapes_quotes_and_backslashes() {
	let value = serde_json::json!({
		"hint\"s": {
			"quote\\path": "你好世界\0",
		},
	});

	assert_eq!(
		invalid_text::find_invalid_path(&value, "$.source_ref"),
		Some("$.source_ref[\"hint\\\"s\"][\"quote\\\\path\"]".to_string())
	);
}

#[test]
fn structured_relation_object_entity_alias_reports_precise_path() {
	let structured = StructuredFields {
		relations: Some(vec![StructuredRelation {
			object: Some(StructuredRelationObject {
				entity: Some(StructuredEntity {
					aliases: Some(vec!["English alias".to_string(), "你好世界\0".to_string()]),
					..StructuredEntity::default()
				}),
				..StructuredRelationObject::default()
			}),
			..StructuredRelation::default()
		}]),
		..StructuredFields::default()
	};

	assert_eq!(
		invalid_text::find_invalid_path_in_structured(Some(&structured), "$.notes[0].structured",),
		Some("$.notes[0].structured.relations[0].object.entity.aliases[1]".to_string())
	);
}
