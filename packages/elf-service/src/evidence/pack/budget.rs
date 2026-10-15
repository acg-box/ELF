use std::collections::HashSet;

use serde::Serialize;

use crate::evidence::pack::{Error, EvidencePackResponse, Result};

impl EvidencePackResponse {
	/// Drop complete tail entries, never a note's qualifications or a cited byte range.
	pub(in crate::evidence) fn limit_bytes(&mut self, maximum: usize) -> Result<()> {
		while serialized_size(self)? > maximum {
			if !self.remove_last_entry() {
				return Err(Error::InvalidRequest {
					message: "Evidence locators do not fit the response budget.".into(),
				});
			}
		}

		Ok(())
	}

	pub(in crate::evidence) fn remove_last_entry(&mut self) -> bool {
		self.complete = false;

		if let Some(note) = self.notes.pop() {
			self.omitted_note_ids.push(note.note_id);

			let retained: HashSet<_> =
				self.notes.iter().flat_map(|note| note.source_references.iter()).collect();

			self.sources.retain(|source| {
				!note.source_references.contains(&source.reference)
					|| retained.contains(&source.reference)
			});
		} else if self.sources.pop().is_none() {
			return false;
		}

		self.source_bytes = self.sources.iter().map(|source| source.text.len()).sum();

		true
	}
}

pub(in crate::evidence) fn response_limit(requested: Option<usize>) -> Result<usize> {
	let limit = requested.unwrap_or(32_768);

	if !(1_024..=32_768).contains(&limit) {
		return Err(Error::InvalidRequest {
			message: "max_bytes must be between 1024 and 32768.".into(),
		});
	}

	Ok(limit)
}

pub(in crate::evidence) fn serialized_size(value: &impl Serialize) -> Result<usize> {
	serde_json::to_vec(value)
		.map(|bytes| bytes.len())
		.map_err(|error| Error::Storage { message: format!("Cannot serialize evidence: {error}") })
}
