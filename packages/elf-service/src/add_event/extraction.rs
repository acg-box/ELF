use serde_json::Value;

use crate::{
	Error, Result,
	add_event::types::{EvidenceQuote, ExtractedEvidence, ExtractorOutput},
	docs::TextPositionSelector,
};

/// These request-local selections bind to exact input bytes, not model-copied text.
pub(super) fn evidence_spans(messages: &[String], max_bytes: usize) -> Result<Vec<Vec<&str>>> {
	messages
		.iter()
		.map(|text| {
			let mut spans = Vec::new();
			let mut start = 0;

			while start < text.len() {
				let mut end = (start + max_bytes).min(text.len());

				while !text.is_char_boundary(end) {
					end -= 1;
				}

				if end == start {
					return Err(Error::InvalidRequest {
						message: "Evidence byte limit cannot hold a source character.".into(),
					});
				}
				if end < text.len()
					&& let Some(newline) = text[start..end].rfind('\n')
				{
					end = start + newline + 1;
				}

				spans.push(&text[start..end]);

				start = end;
			}

			Ok(spans)
		})
		.collect()
}

pub(super) fn attach_spans(messages: &mut Value, spans: &[Vec<&str>]) {
	for (message, pieces) in messages.as_array_mut().expect("Message array").iter_mut().zip(spans) {
		message["evidence_spans"] = serde_json::json!(
			pieces
				.iter()
				.enumerate()
				.map(|(span_id, text)| serde_json::json!({"span_id": span_id, "text": text}))
				.collect::<Vec<_>>()
		);
	}
}

pub(super) fn resolve_selections(
	extracted: &mut ExtractorOutput,
	spans: &[Vec<&str>],
) -> Result<()> {
	for note in &mut extracted.notes {
		for evidence in note.evidence.iter_mut().flatten() {
			let ExtractedEvidence::Selection(selection) = evidence else { continue };
			let end_span_id = selection.end_span_id.unwrap_or(selection.span_id);
			let selected = spans
				.get(selection.message_index)
				.and_then(|pieces| pieces.get(selection.span_id..=end_span_id))
				.filter(|pieces| !pieces.is_empty())
				.ok_or_else(|| Error::InvalidRequest {
					message: "Extractor selected an unknown message or evidence span.".into(),
				})?;
			let quote = selected.concat();
			let start = spans[selection.message_index][..selection.span_id]
				.iter()
				.map(|span| span.len())
				.sum();

			*evidence = ExtractedEvidence::Quote(EvidenceQuote {
				position: Some(TextPositionSelector { start, end: start + quote.len() }),
				message_index: selection.message_index,
				quote,
			});
		}
	}

	Ok(())
}

#[cfg(test)]
mod tests {
	use crate::add_event::{extraction, types::ExtractorOutput};

	#[test]
	fn selections_preserve_newlines_and_multibyte_originals() {
		let originals = vec!["项目甲\n  uses A;\n  then B.\n".to_string()];
		let before = originals.clone();
		let spans = extraction::evidence_spans(&originals, 16).expect("UTF-8 spans");

		assert_eq!(spans[0].concat(), originals[0]);
		assert!(spans[0].iter().all(|span| span.len() <= 16));

		let mut output: ExtractorOutput = serde_json::from_value(serde_json::json!({"notes":[{
			"text":"Example", "evidence":[{"message_index":0,"span_id":1}]
		}]}))
		.expect("Selection output");

		extraction::resolve_selections(&mut output, &spans).expect("Exact selection");

		assert_eq!(
			serde_json::to_value(output).expect("Output")["notes"][0]["evidence"][0]["quote"],
			spans[0][1]
		);

		let normalized = serde_json::from_value::<ExtractorOutput>(
			serde_json::json!({"notes":[{"evidence":[{"message_index":0,"quote":"unchanged"}]}]}),
		)
		.expect("Legacy quotes remain valid");

		assert!(matches!(
			&normalized.notes[0].evidence.as_ref().expect("Evidence")[0],
			crate::add_event::types::ExtractedEvidence::Quote(_)
		));
		assert_eq!(originals, before);
	}

	#[test]
	fn contiguous_ranges_keep_qualifications_beyond_one_span() {
		let original =
			format!("{}\n仅在2026年10月15日之后且审核通过时适用。", "项目甲保留原文。".repeat(40));
		let originals = vec![original.clone()];
		let spans = extraction::evidence_spans(&originals, 320).expect("Spans");
		let mut output: ExtractorOutput = serde_json::from_value(serde_json::json!({"notes":[{
			"text":original, "evidence":[{"message_index":0,"span_id":0,"end_span_id":spans[0].len()-1}]
		}]}))
		.expect("Range");

		extraction::resolve_selections(&mut output, &spans).expect("Exact range");

		let crate::add_event::types::ExtractedEvidence::Quote(quote) =
			&output.notes[0].evidence.as_ref().expect("Evidence")[0]
		else {
			panic!("Resolved quote")
		};
		let position = quote.position.as_ref().expect("Server-owned position");

		assert_eq!(quote.quote, original);
		assert_eq!(position.start, 0);
		assert_eq!(position.end, original.len());

		for (start, end) in [(1, 0), (0, usize::MAX)] {
			let mut invalid: ExtractorOutput =
				serde_json::from_value(serde_json::json!({"notes":[{
					"evidence":[{"message_index":0,"span_id":start,"end_span_id":end}]
				}]}))
				.expect("Syntactic range");

			assert!(extraction::resolve_selections(&mut invalid, &spans).is_err());
		}
	}

	#[test]
	fn unknown_or_ambiguous_selection_cannot_become_evidence() {
		let mut unknown: ExtractorOutput = serde_json::from_value(serde_json::json!({"notes":[{
			"evidence":[{"message_index":0,"span_id":99}]
		}]}))
		.expect("Syntactically valid selection");

		assert!(extraction::resolve_selections(&mut unknown, &[vec!["original"]]).is_err());
		assert!(
			serde_json::from_value::<ExtractorOutput>(serde_json::json!({"notes":[{
				"evidence":[{"message_index":0,"span_id":0,"quote":"different"}]
			}]}))
			.is_err()
		);
	}
}
