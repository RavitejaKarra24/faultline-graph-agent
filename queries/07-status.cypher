MATCH (s:Service {id: $serviceId}) RETURN s.status, s.tier
