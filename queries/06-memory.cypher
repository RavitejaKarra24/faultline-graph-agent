MATCH (m:Memory)-[:ABOUT]->(s:Service) WHERE s.id IN $serviceIds
RETURN properties(m) ORDER BY m.createdAt DESC, m.id DESC LIMIT 100
