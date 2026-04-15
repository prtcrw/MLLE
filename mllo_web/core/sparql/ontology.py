from __future__ import annotations


def resolve_explore_category_target(category_name: str) -> str:
    category_value = (category_name or "").strip()
    if not category_value:
        return "ml:MachineLearningModel"
    if category_value.startswith("http://") or category_value.startswith("https://"):
        return f"<{category_value}>"
    lowered = category_value.lower()
    keyword_map = {
        "model": "ml:MachineLearningModel",
        "models": "ml:MachineLearningModel",
        "dataset": "ml:MachineLearningDataSet",
        "datasets": "ml:MachineLearningDataSet",
        "pipeline": "ml:DataProcessingPipeline",
        "pipelines": "ml:DataProcessingPipeline",
        "metric": "ml:PerformanceMetric",
        "metrics": "ml:PerformanceMetric",
        "performance": "ml:PerformanceMetric",
    }
    if lowered in keyword_map:
        return keyword_map[lowered]
    if ":" in category_value:
        return category_value
    return f"ml:{category_value}"


def build_explore_category_query(category_name: str) -> str:
    target = resolve_explore_category_target(category_name)
    return f"""
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?entity ?entity_type ?label
WHERE {{
    {{
        ?entity rdfs:subClassOf+ {target} .
        BIND("Class" AS ?entity_type)
        OPTIONAL {{ ?entity rdfs:label ?label }}
        FILTER(?entity != <http://www.w3.org/2002/07/owl#Nothing>)
    }}
    UNION
    {{
        ?entity rdf:type/rdfs:subClassOf* {target} .
        OPTIONAL {{ ?entity rdf:type/rdfs:label ?entity_type }}
        OPTIONAL {{ ?entity rdfs:label ?label }}
        FILTER(?entity != <http://www.w3.org/2002/07/owl#Nothing>)
    }}
}}
LIMIT 100
"""

