use std::{
	collections::HashSet,
	env, fs,
	path::{Path, PathBuf},
};

use color_eyre::{Result, eyre};
use serde::Deserialize;

#[derive(Deserialize)]
struct Makefile {
	#[serde(default)]
	extend: Vec<Extension>,
}

#[derive(Deserialize)]
#[serde(untagged)]
enum Extension {
	Path(String),
	Options {
		path: String,
		#[serde(default)]
		optional: bool,
	},
}

pub(crate) fn make_task_catalog() -> Result<String> {
	let path = super::workspace_root()?.join("Makefile.toml");

	read_catalog(&path, &mut HashSet::new())
}

fn read_catalog(path: &Path, active: &mut HashSet<PathBuf>) -> Result<String> {
	let canonical = path.canonicalize()?;

	if !active.insert(canonical.clone()) {
		return Err(eyre::eyre!("Cyclic makefile extension: {}", path.display()));
	}

	let source = fs::read_to_string(&canonical)?;
	let parsed: Makefile = toml::from_str(&source)?;
	let parent = canonical.parent().ok_or_else(|| eyre::eyre!("Makefile has no parent."))?;
	let mut catalog = String::new();

	for extension in parsed.extend {
		let (relative, optional) = match extension {
			Extension::Path(path) => (path, false),
			Extension::Options { path, optional } => (path, optional),
		};
		let child = parent.join(relative);

		if optional && !child.exists() {
			continue;
		}

		catalog.push_str(&read_catalog(&child, active)?);
		catalog.push('\n');
	}

	catalog.push_str(&source);
	active.remove(&canonical);

	Ok(catalog)
}

#[test]
fn catalog_follows_extensions_and_excludes_unregistered_files() -> Result<()> {
	let root = env::temp_dir().join(format!("elf-make-catalog-{}", uuid::Uuid::new_v4()));

	fs::create_dir_all(root.join("nested"))?;
	fs::write(
		root.join("Makefile.toml"),
		"extend = [{ path = 'nested/tasks.toml' }]\n[tasks.root]\n",
	)?;
	fs::write(root.join("nested/tasks.toml"), "extend = ['leaf.toml']\n[tasks.child]\n")?;
	fs::write(root.join("nested/leaf.toml"), "[tasks.leaf]\n")?;
	fs::write(root.join("unused.toml"), "[tasks.unregistered]\n")?;

	let result = read_catalog(&root.join("Makefile.toml"), &mut HashSet::new());

	fs::remove_dir_all(&root)?;

	let catalog = result?;

	assert!(catalog.contains("[tasks.root]"));
	assert!(catalog.contains("[tasks.child]"));
	assert!(catalog.contains("[tasks.leaf]"));
	assert!(!catalog.contains("[tasks.unregistered]"));

	Ok(())
}

#[test]
fn catalog_rejects_missing_required_extensions_and_cycles() -> Result<()> {
	let root = env::temp_dir().join(format!("elf-make-catalog-{}", uuid::Uuid::new_v4()));

	fs::create_dir_all(&root)?;

	let path = root.join("Makefile.toml");

	fs::write(&path, "extend = ['missing.toml']")?;

	let missing = read_catalog(&path, &mut HashSet::new());

	fs::write(&path, "extend = ['Makefile.toml']")?;

	let cyclic = read_catalog(&path, &mut HashSet::new());

	fs::remove_dir_all(&root)?;

	assert!(missing.is_err());
	assert!(cyclic.is_err());

	Ok(())
}
