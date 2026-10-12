CREATE TABLE IF NOT EXISTS graph_entity_aliases (
	alias_id uuid PRIMARY KEY,
	entity_id uuid NOT NULL REFERENCES graph_entities(entity_id) ON DELETE CASCADE,
	alias text NOT NULL,
	alias_norm text NOT NULL,
	authority text NOT NULL DEFAULT 'unknown' CHECK (authority IN ('unknown', 'extracted', 'caller')),
	created_at timestamptz NOT NULL DEFAULT now()
);

-- Historical aliases do not record who authorized identity equivalence.
ALTER TABLE graph_entity_aliases
    ADD COLUMN IF NOT EXISTS authority text NOT NULL DEFAULT 'unknown'
    CHECK (authority IN ('unknown', 'extracted', 'caller'));

CREATE UNIQUE INDEX IF NOT EXISTS idx_graph_entity_aliases_entity_alias_norm
	ON graph_entity_aliases (entity_id, alias_norm);
CREATE INDEX IF NOT EXISTS idx_graph_entity_aliases_alias_norm
	ON graph_entity_aliases (alias_norm);

