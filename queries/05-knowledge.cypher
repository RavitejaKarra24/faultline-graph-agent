MATCH (d)-[:ABOUT]->(s:Service) WHERE s.id IN $serviceIds AND d.kind IN $kinds
RETURN d.id, d.label, d.description, d.kind, s.id ORDER BY d.id, s.id LIMIT 128
