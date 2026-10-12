use std::sync::Arc;

use rmcp::model::JsonObject;

pub(in crate::app::server) fn events_ingest_schema() -> Arc<JsonObject> {
	Arc::new(rmcp::object!({
		"type": "object",
		"additionalProperties": true,
		"required": ["messages"],
		"properties": {
			"scope": { "type": ["string", "null"] },
			"dry_run": { "type": ["boolean", "null"] },
			"ingestion_profile": {
				"type": "object",
				"additionalProperties": true,
				"required": ["id"],
				"properties": {
					"id": { "type": "string" },
					"version": { "type": ["integer", "null"] },
				},
			},
			"messages": {
				"type": "array",
				"items": {
					"type": "object",
					"additionalProperties": true,
					"required": ["role", "content"],
					"properties": {
						"role": { "type": "string" },
						"content": { "type": "string" },
						"ts": { "type": ["string", "null"] },
						"msg_id": { "type": ["string", "null"] },
						"source_document": {
							"type": ["object", "null"],
							"additionalProperties": false,
							"required": ["doc_id", "content_hash", "position"],
							"properties": {
								"doc_id": {"type":"string", "format":"uuid"},
								"content_hash": {"type":"string"},
								"position": {"type":"object", "required":["start","end"], "properties":{
									"start":{"type":"integer","minimum":0},
									"end":{"type":"integer","minimum":1}
								}}
							}
						},
						"write_policy": { "type": ["object", "null"] }
					}
				}
			}
		}
	}))
}
