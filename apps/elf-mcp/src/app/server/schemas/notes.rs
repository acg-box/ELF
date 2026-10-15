use std::sync::Arc;

use rmcp::model::JsonObject;
use serde_json::Value;

pub(in crate::app::server) fn notes_ingest_schema() -> Arc<JsonObject> {
	Arc::new(
		serde_json::from_value(serde_json::json!({
			"type": "object",
			"additionalProperties": true,
			"required": ["scope", "notes"],
			"properties": {
				"scope": { "type": "string" },
				"notes": {
					"type": "array",
					"items": {
						"type": "object",
						"additionalProperties": true,
						"required": ["type", "text", "importance", "confidence", "source_ref"],
						"properties": {
							"type": { "type": "string" },
							"key": { "type": ["string", "null"] },
							"text": { "type": "string" },
							"write_policy": { "type": ["object", "null"] },
							"importance": { "type": "number" },
							"confidence": { "type": "number" },
							"ttl_days": { "type": ["integer", "null"] },
							"source_ref": { "type": "object", "additionalProperties": true },
							"structured": notes_structured_schema()
						}
					}
				}
			}
		}))
		.expect("notes_ingest_schema must be valid JSON object"),
	)
}

pub(in crate::app::server) fn notes_list_schema() -> Arc<JsonObject> {
	Arc::new(rmcp::object!({
		"type": "object",
		"additionalProperties": true,
		"properties": {
			"scope": { "type": ["string", "null"] },
			"status": { "type": ["string", "null"] },
			"type": { "type": ["string", "null"] }
		}
	}))
}

pub(in crate::app::server) fn notes_get_schema() -> Arc<JsonObject> {
	Arc::new(rmcp::object!({
		"type": "object",
		"additionalProperties": true,
		"required": ["note_id"],
		"properties": {
			"note_id": { "type": "string" }
		}
	}))
}

pub(in crate::app::server) fn notes_patch_schema() -> Arc<JsonObject> {
	Arc::new(rmcp::object!({
		"type": "object",
		"additionalProperties": true,
	"required": ["note_id"],
	"properties": {
		"note_id": { "type": "string" },
		"text": { "type": ["string", "null"] },
		"importance": { "type": ["number", "null"] },
		"confidence": { "type": ["number", "null"] },
		"ttl_days": { "type": ["integer", "null"] }
	}
	}))
}

pub(in crate::app::server) fn notes_publish_schema() -> Arc<JsonObject> {
	Arc::new(rmcp::object!({
		"type": "object",
		"additionalProperties": true,
		"required": ["note_id", "space"],
		"properties": {
			"note_id": { "type": "string" },
			"space": { "type": "string", "enum": ["team_shared", "org_shared"] }
		}
	}))
}

pub(in crate::app::server) fn notes_unpublish_schema() -> Arc<JsonObject> {
	notes_publish_schema()
}

pub(in crate::app::server) fn evidence_check_schema() -> Arc<JsonObject> {
	Arc::new(serde_json::from_value(serde_json::json!({
        "type":"object", "additionalProperties":false, "required":["claims"],
        "properties":{"claims":{"type":"array", "minItems":1,"maxItems":12,"items":{
            "type":"object","additionalProperties":false,"required":["text","state","citations"],"properties":{
                "depends_on":{"type":"array","maxItems":12,"items":{"type":"integer","minimum":0,"maximum":11},"description":"Earlier claim indices that supply required subject, scope, or temporal evidence. No self or forward references."},
                "text":{"type":"string"},"state":{"type":"string","enum":["supported","absent","unknown","conflict"]},
                "citations":{"type":"array","maxItems":8,"items":{"oneOf":[
                    {"type":"object","additionalProperties":false,"required":["kind","reference"],"properties":{"kind":{"const":"reference"},"reference":{"type":"string","maxLength":192}}},
                    {"type":"object","additionalProperties":false,"required":["kind","note_id","quote"],"properties":{"kind":{"const":"note"},"note_id":{"type":"string"},"quote":{"type":"string"}}},
                    {"type":"object","additionalProperties":false,"required":["kind","doc_id","content_hash","quote"],"properties":{"kind":{"const":"source"},"doc_id":{"type":"string"},"content_hash":{"type":"string"},"quote":{"type":"string"}}}
                ]}}
            }
        }}}
    })).expect("Valid evidence check schema"))
}

pub(in crate::app::server) fn evidence_pack_schema() -> Arc<JsonObject> {
	Arc::new(serde_json::from_value(serde_json::json!({
        "type":"object", "additionalProperties":false, "required":["note_ids"],
        "properties":{
            "note_ids":{"type":"array","minItems":1,"maxItems":12,"items":{"type":"string","format":"uuid"}},
            "max_source_bytes":{"type":"integer","minimum":1,"maximum":32_768},
            "max_bytes":{"type":"integer","minimum":1_024,"maximum":32_768}
        }
    })).expect("Valid evidence pack schema"))
}

pub(in crate::app::server) fn evidence_recall_schema() -> Arc<JsonObject> {
	Arc::new(serde_json::from_value(serde_json::json!({
		"type": "object", "additionalProperties": false, "required": ["subjects"],
		"properties": {
			"subjects": {"type":"array", "minItems":1, "maxItems":4, "items":{"type":"string", "minLength":2, "maxLength":128}},
			"as_of": {"type":["string", "null"], "format":"date-time"},
			"max_bytes":{"type":"integer","minimum":1_024,"maximum":32_768}
		}
	})).expect("Valid evidence recall schema"))
}

fn notes_structured_entity_schema() -> Value {
	serde_json::json!({
		"type": "object",
		"additionalProperties": true,
		"required": ["canonical"],
		"properties": {
			"canonical": { "type": "string" },
			"entity_id": { "type": ["string", "null"], "description": "Existing caller-selected identity. Automatic extraction cannot assign this field." },
			"kind": { "type": ["string", "null"] },
			"aliases": {
				"type": ["array", "null"],
				"items": { "type": "string" }
			}
		}
	})
}

fn notes_structured_relation_object_schema() -> Value {
	serde_json::json!({
		"type": "object",
		"additionalProperties": true,
		"oneOf": [
			{
				"type": "object",
				"required": ["entity"],
				"properties": {
					"entity": notes_structured_entity_schema(),
					"value": { "type": "null" }
				}
			},
			{
				"type": "object",
				"required": ["value"],
				"properties": {
					"entity": { "type": ["object", "null"] },
					"value": { "type": "string" }
				}
			}
		]
	})
}

fn notes_structured_schema() -> Value {
	serde_json::json!({
		"type": ["object", "null"],
		"additionalProperties": true,
		"properties": {
			"summary": { "type": ["string", "null"] },
			"facts": {
				"type": ["array", "null"],
				"items": { "type": "string" }
			},
			"concepts": {
				"type": ["array", "null"],
				"items": { "type": "string" }
			},
			"entities": {
				"type": ["array", "null"],
				"items": notes_structured_entity_schema()
			},
			"relations": {
				"type": ["array", "null"],
				"items": {
					"type": "object",
					"additionalProperties": true,
					"required": ["subject", "predicate", "object"],
					"properties": {
						"subject": notes_structured_entity_schema(),
						"predicate": { "type": "string" },
						"evidence_quote": { "type": ["string", "null"] },
						"object": notes_structured_relation_object_schema(),
						"valid_from": { "type": ["string", "null"], "format": "date-time" },
						"valid_to": { "type": ["string", "null"], "format": "date-time" }
					}
				}
			}
		}
	})
}
