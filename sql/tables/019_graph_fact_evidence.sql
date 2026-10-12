CREATE TABLE IF NOT EXISTS graph_fact_evidence (
	evidence_id uuid PRIMARY KEY,
	fact_id uuid NOT NULL REFERENCES graph_facts(fact_id) ON DELETE CASCADE,
	note_id uuid NOT NULL REFERENCES memory_notes(note_id) ON DELETE CASCADE,
	quote text NULL,
	created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE graph_fact_evidence ADD COLUMN IF NOT EXISTS quote text NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_graph_fact_evidence_fact_note
	ON graph_fact_evidence (fact_id, note_id);
CREATE INDEX IF NOT EXISTS idx_graph_fact_evidence_note
	ON graph_fact_evidence (note_id);
CREATE INDEX IF NOT EXISTS idx_graph_fact_evidence_fact
	ON graph_fact_evidence (fact_id);

