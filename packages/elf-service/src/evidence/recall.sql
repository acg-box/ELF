WITH visible_notes AS MATERIALIZED (
    SELECT n.note_id, n.source_ref, n.text, n.tenant_id, n.project_id
    FROM memory_notes n
    WHERE n.tenant_id = $1
      AND (n.project_id = $2 OR (n.project_id = $7 AND n.scope = 'org_shared'))
      AND n.status = 'active' AND (n.expires_at IS NULL OR n.expires_at > now())
      AND n.scope = ANY($4::text[])
      AND ((n.scope = 'agent_private' AND n.agent_id = $3)
        OR (n.scope IN ('project_shared', 'org_shared') AND
            (n.agent_id = $3 OR (n.scope || ':' || n.agent_id) = ANY($5::text[]))))
), matches AS (
    SELECT n.note_id, n.source_ref,
        EXISTS (SELECT 1 FROM unnest($6::text[]) s WHERE strpos(lower(n.text), s) > 0) AS lexical_match,
        ARRAY(
            SELECT DISTINCT ge.entity_id
            FROM graph_fact_evidence e
            JOIN graph_facts f ON f.fact_id = e.fact_id
            JOIN graph_entities ge ON ge.entity_id IN (f.subject_entity_id, f.object_entity_id)
            WHERE e.note_id = n.note_id
              AND f.tenant_id = n.tenant_id AND f.project_id = n.project_id
              AND ge.tenant_id = f.tenant_id AND ge.project_id = f.project_id
              AND f.scope = ANY($4::text[])
              AND ((f.scope = 'agent_private' AND f.agent_id = $3)
                OR (f.scope IN ('project_shared', 'org_shared') AND
                    (f.agent_id = $3 OR (f.scope || ':' || f.agent_id) = ANY($5::text[]))))
              AND EXISTS (SELECT 1 FROM unnest($6::text[]) s
                  WHERE strpos(lower(ge.canonical), s) > 0
                    OR EXISTS (SELECT 1 FROM graph_entity_aliases a
                        WHERE a.entity_id = ge.entity_id AND a.authority = 'caller' AND strpos(lower(a.alias), s) > 0))
            ORDER BY ge.entity_id
        ) AS entity_ids
    FROM visible_notes n
)
SELECT note_id, source_ref, lexical_match, entity_ids
FROM matches
WHERE lexical_match OR cardinality(entity_ids) > 0
ORDER BY (lexical_match AND cardinality(entity_ids) > 0) DESC, note_id
LIMIT 129
