//! Read-time evidence expansion and quote binding. No source mutation or semantic oracle.

mod claims;
mod pack;
mod recall;
mod reference;
mod source_recall;
mod sources;
mod types;

pub use self::{
	pack::{EvidencePackNote, EvidencePackRequest, EvidencePackResponse, EvidencePackSource},
	recall::{EvidenceRecallCandidate, EvidenceRecallRequest, EvidenceRecallResponse},
	types::{
		ClaimBinding, ClaimCitation, ClaimEvidence, ClaimState, EvidenceCheckRequest,
		EvidenceCheckResponse, NoteEvidenceResponse, NoteSourceEvidence,
	},
};

use crate::{ElfService, Error, NoteFetchRequest, Result};

const MAX_SOURCES: usize = 4;
const MAX_CLAIMS: usize = 12;
const MAX_CITATIONS: usize = 8;
