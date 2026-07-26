CREATE CONSTRAINT entity_id IF NOT EXISTS
FOR (entity:Entity) REQUIRE entity.id IS UNIQUE;

CREATE CONSTRAINT address_id IF NOT EXISTS
FOR (address:Address) REQUIRE address.id IS UNIQUE;

CREATE INDEX entity_name IF NOT EXISTS
FOR (entity:Entity) ON (entity.label);
