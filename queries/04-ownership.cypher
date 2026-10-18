MATCH (t:Team)-[:OWNS]->(s:Service) WHERE s.id IN $serviceIds
OPTIONAL MATCH (p:Person)-[:ON_CALL_FOR]->(t)
RETURN s.id, t.id, t.label, p.id, p.label ORDER BY s.id, t.id, p.id
