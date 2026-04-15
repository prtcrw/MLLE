from __future__ import annotations


ONTOLOGY_SCHEMA_QUERY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?entity ?label ?type ?domain ?range WHERE {
  {
    ?entity a owl:Class .
    BIND("Class" AS ?type)
    OPTIONAL { ?entity rdfs:label ?label }
    OPTIONAL {
      ?entity rdfs:subClassOf ?domain .
      FILTER(isIRI(?domain))
    }
  }
  UNION
  {
    ?entity a owl:ObjectProperty .
    BIND("ObjectProperty" AS ?type)
    OPTIONAL { ?entity rdfs:label ?label }
    OPTIONAL { ?entity rdfs:domain ?domain }
    OPTIONAL { ?entity rdfs:range ?range }
  }
  UNION
  {
    ?entity a owl:DatatypeProperty .
    BIND("DatatypeProperty" AS ?type)
    OPTIONAL { ?entity rdfs:label ?label }
    OPTIONAL { ?entity rdfs:domain ?domain }
    OPTIONAL { ?entity rdfs:range ?range }
  }
  UNION
  {
    ?entity a owl:AnnotationProperty .
    BIND("AnnotationProperty" AS ?type)
    OPTIONAL { ?entity rdfs:label ?label }
  }
  FILTER(isIRI(?entity))
}
ORDER BY ?type ?entity
LIMIT 1000
"""


PREFIX_QUERY = """
SELECT ?prefix ?namespace WHERE {
  VALUES (?prefix ?namespace) {
    ("rdf" "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    ("rdfs" "http://www.w3.org/2000/01/rdf-schema#")
    ("owl" "http://www.w3.org/2002/07/owl#")
    ("xsd" "http://www.w3.org/2001/XMLSchema#")
    ("ml" "http://www.semanticweb.org/mnd14/ml/")
    ("bfo" "http://purl.obolibrary.org/obo/")
    ("iof-core" "https://spec.industrialontologies.org/ontology/core/Core/")
  }
}
"""


SAMPLE_TRIPLES_QUERY = """
SELECT DISTINCT ?s ?p ?o WHERE {
  ?s ?p ?o .
  FILTER(isIRI(?s))
}
LIMIT 50
"""


NAMED_INDIVIDUALS_QUERY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?individual ?label ?type WHERE {
  ?individual rdf:type ?type .
  FILTER(isIRI(?individual))
  FILTER(isIRI(?type))
  FILTER(?type != owl:NamedIndividual)
  FILTER NOT EXISTS { ?individual a owl:Class }
  FILTER NOT EXISTS { ?individual a owl:ObjectProperty }
  FILTER NOT EXISTS { ?individual a owl:DatatypeProperty }
  FILTER NOT EXISTS { ?individual a owl:AnnotationProperty }
  OPTIONAL { ?individual rdfs:label ?label }
}
ORDER BY ?individual ?type
LIMIT 300
"""
