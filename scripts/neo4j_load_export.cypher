// Run after the CLI has created outputs/latest/neo4j/*.csv and those files
// are available in Neo4j's import directory.

LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
CALL {
  WITH row
  WITH row WHERE row[':LABEL'] = 'Entity'
  MERGE (n:Entity {id: row['id:ID']})
  SET n.label = row.label,
      n.node_type = row.node_type,
      n.designated = toBoolean(row['designated:boolean']),
      n.programs = split(row['programs:string[]'], ';'),
      n.source = row.source
}
CALL {
  WITH row
  WITH row WHERE row[':LABEL'] = 'Address'
  MERGE (n:Address {id: row['id:ID']})
  SET n.label = row.label,
      n.node_type = row.node_type,
      n.source = row.source
}
RETURN count(*) AS nodes_loaded;

// Neo4j does not permit dynamic relationship types in plain Cypher LOAD CSV.
// Import relationships.csv with neo4j-admin database import for a new database,
// or load each relationship type with a typed query in production.
