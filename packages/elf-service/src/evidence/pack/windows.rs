use std::{collections::HashSet, mem};

use crate::evidence::pack::{EvidencePackResponse, EvidencePackSource, reference};

/// Merge only already verified windows of the same immutable document version.
pub(super) fn merge_overlaps(pack: &mut EvidencePackResponse) {
	let mut ordered: Vec<_> = mem::take(&mut pack.sources).into_iter().enumerate().collect();
	let original_refs: Vec<_> = ordered
		.iter()
		.map(|(_, source)| {
			(
				source.reference.clone(),
				source.doc_id,
				source.start,
				source.end,
				source.content_hash.clone(),
			)
		})
		.collect();

	ordered.sort_by(|(_, left), (_, right)| {
		(left.doc_id, &left.content_hash, left.start, left.end).cmp(&(
			right.doc_id,
			&right.content_hash,
			right.start,
			right.end,
		))
	});

	let mut merged: Vec<(usize, EvidencePackSource)> = Vec::new();

	for (index, source) in ordered {
		if let Some((first_index, prior)) = merged.last_mut()
			&& prior.doc_id == source.doc_id
			&& prior.content_hash == source.content_hash
			&& source.start <= prior.end
		{
			if source.end > prior.end {
				prior.text.push_str(&source.text[prior.end - source.start..]);

				prior.end = source.end;
			}

			*first_index = (*first_index).min(index);
			prior.reference = reference::source_reference(
				prior.doc_id,
				&prior.content_hash,
				prior.start,
				prior.end,
			);
		} else {
			merged.push((index, source));
		}
	}

	merged.sort_by_key(|(index, _)| *index);

	pack.sources = merged.into_iter().map(|(_, source)| source).collect();
	pack.source_bytes = pack.sources.iter().map(|source| source.text.len()).sum();

	for note in &mut pack.notes {
		for old in &mut note.source_references {
			if let Some((_, doc_id, start, end, hash)) = original_refs.iter().find(|r| &r.0 == old)
				&& let Some(source) = pack.sources.iter().find(|source| {
					source.doc_id == *doc_id
						&& source.content_hash == *hash
						&& source.start <= *start
						&& source.end >= *end
				}) {
				*old = source.reference.clone();
			}
		}

		let mut seen = HashSet::new();

		note.source_references.retain(|reference| seen.insert(reference.clone()));

		let mut seen_quotes = HashSet::new();

		note.evidence_quotes.retain(|quote| {
			!quote.is_empty()
				&& seen_quotes.insert(quote.clone())
				&& pack.sources.iter().any(|source| {
					note.source_references.contains(&source.reference)
						&& source.text.contains(quote)
				})
		});
	}
}

#[cfg(test)]
mod tests {
	use time::OffsetDateTime;
	use uuid::Uuid;

	use crate::evidence::pack::{
		EvidencePackNote,
		windows::{self, EvidencePackResponse, EvidencePackSource, reference},
	};

	#[test]
	fn overlapping_utf8_windows_keep_bytes_references_and_first_source_order() {
		let text = "甲乙丙丁戊";
		let make = |start, end, hash: &str| EvidencePackSource {
			reference: reference::source_reference(Uuid::nil(), hash, start, end),
			doc_id: Uuid::nil(),
			content_hash: hash.into(),
			start,
			end,
			text: text[start..end].into(),
			title: None,
			origin: Some("repo:project/document@revision".into()),
			source_timestamp: None,
			captured_at: OffsetDateTime::UNIX_EPOCH,
		};
		let sources =
			vec![make(6, 15, "version-a"), make(0, 3, "version-b"), make(0, 9, "version-a")];
		let refs = sources.iter().map(|s| s.reference.clone()).collect();
		let mut pack = EvidencePackResponse {
			omitted_note_ids: vec![],
			schema: "elf.evidence_pack/v1",
			source_bytes: 21,
			complete: true,
			sources,
			notes: vec![EvidencePackNote {
				note_id: Uuid::nil(),
				note_type: "constraint".into(),
				project_id: "project".into(),
				scope: "agent_private".into(),
				text: "Derived".into(),
				facts: vec!["甲乙丙丁戊".into()],
				evidence_quotes: vec!["甲乙丙丁戊".into(), "甲乙丙丁戊".into(), "unread".into()],
				source_references: refs,
				complete: true,
			}],
		};

		windows::merge_overlaps(&mut pack);

		assert_eq!(pack.sources.len(), 2);
		assert_eq!(pack.sources[0].text, text);
		assert_eq!(pack.sources[0].content_hash, "version-a");
		assert_eq!(pack.sources[0].origin.as_deref(), Some("repo:project/document@revision"));
		assert_eq!(pack.notes[0].facts, vec!["甲乙丙丁戊"]);
		assert_eq!(pack.notes[0].evidence_quotes, vec!["甲乙丙丁戊"]);
		assert_eq!(pack.source_bytes, 18);
		assert_eq!(pack.notes[0].source_references.len(), 2);
		assert_eq!(pack.notes[0].source_references[0], pack.sources[0].reference);
		assert_eq!(pack.notes[0].source_references[1], pack.sources[1].reference);
	}
}
