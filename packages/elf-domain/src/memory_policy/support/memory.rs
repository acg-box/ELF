use elf_config::{Memory, MemoryPolicy, MemoryPolicyRule};

pub(crate) fn test_memory_config() -> Memory {
	Memory {
		ingest_max_bytes: 32_768,
		preview_max_chars: 240,
		candidate_k: 60,
		top_k: 12,
		policy: MemoryPolicy {
			rules: vec![
				MemoryPolicyRule {
					note_type: Some("fact".to_string()),
					scope: Some("agent_private".to_string()),
					min_confidence: Some(0.9),
					min_importance: Some(0.1),
				},
				MemoryPolicyRule {
					note_type: Some("preference".to_string()),
					scope: Some("agent_private".to_string()),
					min_confidence: Some(0.75),
					min_importance: None,
				},
				MemoryPolicyRule {
					note_type: Some("preference".to_string()),
					scope: None,
					min_confidence: Some(0.6),
					min_importance: None,
				},
				MemoryPolicyRule {
					note_type: None,
					scope: None,
					min_confidence: None,
					min_importance: None,
				},
			],
		},
	}
}
