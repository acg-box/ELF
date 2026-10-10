use std::{env, fs, path::PathBuf};

use crate::helpers::{self, TRACE_GATE_CONFIG_TOML};

#[test]
fn required_config_fields_must_be_explicit() {
	let cases = [
		(&["storage", "qdrant", "docs_collection"][..], "docs_collection"),
		(&["memory", "policy"][..], "policy"),
		(&["search", "recursive"][..], "recursive"),
		(&["search", "graph_context"][..], "graph_context"),
		(&["security", "auth_keys"][..], "auth_keys"),
	];

	for (path, field) in cases {
		let payload = helpers::remove_required_config_key(&helpers::sample_toml(), path);
		let config_path = helpers::write_temp_config(payload);
		let result = elf_config::load(&config_path);

		fs::remove_file(&config_path).expect("Failed to remove test config.");
		helpers::assert_missing_field_error(result, field);
	}
}

#[test]
fn docker_local_config_is_strict_valid() {
	let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../config/local/elf.docker.toml");
	let cfg = elf_config::load(path.as_path()).expect("Docker local config must load.");

	assert_eq!(
		cfg.storage.postgres.dsn,
		"postgres://elf_dev:elf_dev_password@127.0.0.1:51888/elf_local"
	);
	assert_eq!(cfg.storage.qdrant.url, "http://127.0.0.1:51890");
	assert_eq!(cfg.storage.qdrant.collection, "elf_local_notes");
	assert_eq!(cfg.storage.qdrant.docs_collection, "elf_local_doc_chunks");
	assert_eq!(cfg.providers.embedding.provider_id, "local");
	assert_eq!(cfg.providers.rerank.provider_id, "local");
	assert_eq!(cfg.search.expansion.mode, "off");
}

#[test]
fn obsolete_language_toggle_is_rejected() {
	let payload =
		helpers::sample_toml().replace("[security]", "[security]\nreject_non_english = true");

	assert!(toml::from_str::<elf_config::Config>(&payload).is_err());
}

#[test]
fn elf_example_toml_is_valid() {
	let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));

	path.push("../../elf.example.toml");

	elf_config::load(&path).expect("Expected elf.example.toml to be a valid config.");
}

#[test]
fn trace_gate_fixture_toml_is_valid() {
	let path = helpers::write_temp_config(TRACE_GATE_CONFIG_TOML.to_string());

	elf_config::load(&path).expect("Expected trace gate fixture config to be valid.");
	fs::remove_file(&path).expect("Failed to remove test config.");
}
