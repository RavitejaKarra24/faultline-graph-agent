MATCH p=(c:Customer)-[:DEPENDS_ON*1..6]->(root:Service {id: $serviceId})
WHERE all(r IN relationships(p) WHERE r.enabled = true)
RETURN DISTINCT c.id, c.label, [n IN nodes(p) | n.id] ORDER BY c.id LIMIT 256
