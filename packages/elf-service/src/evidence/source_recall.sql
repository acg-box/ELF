SELECT d.doc_id,
    octet_length(left(d.content, hit.position - 1)) AS start,
    octet_length(left(d.content, hit.position - 1 + hit.width)) AS end
FROM doc_documents d
CROSS JOIN LATERAL (
    SELECT strpos(lower(d.content), s) AS position, char_length(s) AS width
    FROM unnest($6::text[]) s
    WHERE strpos(lower(d.content), s) > 0
    ORDER BY position, s
    LIMIT 1
) hit
WHERE d.tenant_id = $1
    AND (d.project_id = $2 OR (d.project_id = $7 AND d.scope = 'org_shared'))
    AND d.status = 'active' AND d.scope = ANY($4::text[])
    AND ((d.scope = 'agent_private' AND d.agent_id = $3)
        OR (d.scope IN ('project_shared', 'org_shared') AND
            (d.agent_id = $3 OR (d.scope || ':' || d.agent_id) = ANY($5::text[]))))
ORDER BY d.doc_id
LIMIT 13
