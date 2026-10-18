MATCH p=(s:Service)-[:DEPENDS_ON*1..6]->(root:Service {id: $serviceId})
WHERE s.id <> root.id AND all(r IN relationships(p) WHERE r.enabled = true)
RETURN DISTINCT s.id, s.label, [n IN nodes(p) | n.id] ORDER BY s.id LIMIT 256
