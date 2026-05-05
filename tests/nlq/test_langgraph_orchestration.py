from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, patch

from mllo_web.app.api.services.settings_model import MLLESettings
from mllo_web.core.workflows.generation import (
    build_empty_result_repair_messages,
    empty_result_fallback_candidates,
    fatal_validation_errors,
    generate_sparql,
    relationship_fallback_candidates,
    validate_sparql,
)
from mllo_web.core.workflows.nlq import execute_nlq
from mllo_web.core.workflows.nlq_graph import (
    LangGraphOrchestrationError,
    _canonical_iris_from_graph_observations,
    _canonicalize_sparql_iri_constants,
    _debug_empty_sparql,
    _observed_node_hop_answer_candidates,
    _required_answer_slots,
    _run_safe_graph_native_probe,
    _search_terms_from_question,
    execute_nlq_graph,
)
from mllo_web.core.workflows.schema_bridge import ML_NS, schema_bridge_grounding


class FakeGateway:
    def __init__(self, intent_tool: str = "find_models") -> None:
        self.intent_tool = intent_tool
        self.calls: list[str | None] = []

    async def chat_completion(self, messages: list[dict], provider_config: dict, purpose: str | None = None) -> str:
        self.calls.append(purpose)
        if purpose == "intent_classification":
            return json.dumps(
                {
                    "tool": self.intent_tool,
                    "params": {"question": "Which models use MnistG16?"},
                    "use_inference": False,
                    "reasoning": "test intent",
                }
            )
        if purpose == "sparql_repair_execution":
            return "SELECT ?model WHERE { ?model ?p ?o } LIMIT 10"
        return "Found matching MLLE results."


class PromptCaptureGateway:
    def __init__(self, response: str = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 100") -> None:
        self.response = response
        self.messages_by_purpose: dict[str | None, list[dict]] = {}

    async def chat_completion(self, messages: list[dict], provider_config: dict, purpose: str | None = None) -> str:
        self.messages_by_purpose[purpose] = messages
        return self.response


class FakeGraphDB:
    def __init__(self, *, fail_first_query: bool = False) -> None:
        self.fail_first_query = fail_first_query
        self.query_calls = 0

    async def validate_repo(self, repo: str) -> str:
        return repo

    async def query(self, sparql: str, repo: str, use_inference: bool = False) -> list[dict]:
        self.query_calls += 1
        if self.fail_first_query and self.query_calls == 1:
            raise RuntimeError("SPARQL parse error")
        return [{"model": "http://example.com/model/MnistModel", "label": "MnistModel"}]


class SchemaBridgeFakeGraphDB:
    async def validate_repo(self, repo: str) -> str:
        return repo

    async def query(
        self,
        sparql: str,
        repo: str,
        use_inference: bool = False,
        show_upper_ontology: bool = False,
    ) -> list[dict]:
        if "SELECT ?source_class ?property ?target_class" in sparql:
            return [
                {
                    "source_class": f"{ML_NS}ModelExecution",
                    "property": f"{ML_NS}hasDataInput",
                    "target_class": f"{ML_NS}TestDataSet",
                    "count": "18",
                },
                {
                    "source_class": f"{ML_NS}ModelExecution",
                    "property": f"{ML_NS}hasDataOutput",
                    "target_class": f"{ML_NS}ModelOutputDataset",
                    "count": "18",
                },
                {
                    "source_class": f"{ML_NS}ModelExecution",
                    "property": f"{ML_NS}executes",
                    "target_class": f"{ML_NS}MachineLearningModel",
                    "count": "18",
                },
                {
                    "source_class": f"{ML_NS}ModelPerformanceAssessment",
                    "property": f"{ML_NS}hasDataInput",
                    "target_class": f"{ML_NS}ModelOutputDataset",
                    "count": "18",
                },
                {
                    "source_class": f"{ML_NS}ModelPerformanceAssessment",
                    "property": f"{ML_NS}hasDataOutput",
                    "target_class": f"{ML_NS}ModelPerformanceMetric",
                    "count": "18",
                },
            ]
        if "possiblyMissing" in sparql:
            return []
        if "ModelPerformanceAssessment" in sparql and "hasSimpleExpressionValue" in sparql:
            return [
                {
                    "model_name": "http://example.com/MNIST#MLModel1",
                    "ml_process": "http://example.com/MNIST#ModelExecution4",
                    "test_dataset": "http://example.com/MNIST#PreprocessedDataset4",
                    "model_performance_metric": "classification accuracy",
                    "model_performance_value": "0.9807",
                }
            ]
        return []


class ProbeCaptureGraphDB:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def query(
        self,
        sparql: str,
        repo: str,
        use_inference: bool = False,
        show_upper_ontology: bool = False,
    ) -> list[dict]:
        self.queries.append(sparql)
        if "luc:query" in sparql:
            return [
                {
                    "matched_term": "PreprocessedDataset1",
                    "term_rank": "0",
                    "node": "http://example.com/MNIST#PreprocessedDataset1",
                    "label": "PreprocessedDataset1",
                    "type": f"{ML_NS}TestDataSet",
                    "score": "0.9",
                    "match_rank": "-1",
                    "node_kind_rank": "1",
                }
            ]
        if "SELECT DISTINCT ?matched_term ?term_rank ?node" in sparql:
            return [
                {
                    "matched_term": "PreprocessedDataset1",
                    "term_rank": "0",
                    "node": "http://example.com/MNIST#PreprocessedDataset1",
                    "label": "PreprocessedDataset1",
                    "type": f"{ML_NS}TestDataSet",
                    "match_rank": "0",
                },
                {
                    "matched_term": "raw",
                    "term_rank": "1",
                    "node": f"{ML_NS}RawDataSet",
                    "label": "raw data set",
                    "type": "http://www.w3.org/2002/07/owl#Class",
                    "match_rank": "1",
                },
            ]
        return []


class EmptyDebugGraphDB:
    async def query(
        self,
        sparql: str,
        repo: str,
        use_inference: bool = False,
        show_upper_ontology: bool = False,
    ) -> list[dict]:
        if "evaluatedBy" in sparql:
            return [{"count": "0"}]
        if "hasDataOutput" in sparql:
            return [{"count": "18"}]
        if "ModelEvaluation" in sparql:
            return [{"count": "18"}]
        return [{"count": "1"}]


class CanonicalIriGraphDB:
    def __init__(self) -> None:
        self.executed_sparql: list[str] = []

    async def validate_repo(self, repo: str) -> str:
        return repo

    async def query(
        self,
        sparql: str,
        repo: str,
        use_inference: bool = False,
        show_upper_ontology: bool = False,
    ) -> list[dict]:
        self.executed_sparql.append(sparql)
        if "<http://example.com/MNIST#MnistG16>" in sparql:
            return [{"downstreamArtifact": "http://example.com/MNIST#PreprocessedDataset1"}]
        return []


class LangGraphOrchestrationTests(unittest.IsolatedAsyncioTestCase):
    def _minimal_ontology_context(self) -> dict:
        return {
            "prefixes": {
                "ml": ML_NS,
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            },
            "classes": [
                {"iri": f"{ML_NS}MachineLearningModel", "label": ""},
                {"iri": f"{ML_NS}TestDataSet", "label": ""},
            ],
            "object_properties": [
                {"iri": f"{ML_NS}hasDataInput", "domain": "", "range": ""},
                {"iri": f"{ML_NS}executes", "domain": "", "range": ""},
            ],
            "datatype_properties": [],
            "annotation_properties": [],
            "individuals": [{"iri": "http://example.com/MNIST#PreprocessedDataset1", "label": "", "type": f"{ML_NS}TestDataSet"}],
            "sample_triples": [],
        }

    def test_custom_sparql_seed_terms_are_question_terms_not_prompt_words(self) -> None:
        terms = _search_terms_from_question(
            "Show me models with performance more than 0.9, their test dataset, and their pipeline."
        )

        self.assertNotIn("Show", terms)
        self.assertIn("performance", terms)
        self.assertIn("model", terms)
        self.assertIn("dataset", terms)
        self.assertIn("pipeline", terms)
        self.assertNotIn("and", terms)

    def test_custom_sparql_seed_terms_drop_common_relation_words(self) -> None:
        terms = _search_terms_from_question("What raw dataset is used to make PreprocessedDataset1?")

        self.assertEqual(terms[0], "PreprocessedDataset1")
        self.assertIn("raw", terms)
        self.assertIn("dataset", terms)
        self.assertNotIn("is", terms)
        self.assertNotIn("to", terms)
        self.assertNotIn("make", terms)

    async def test_graph_native_probe_prioritizes_seed_terms_before_limit(self) -> None:
        graphdb = ProbeCaptureGraphDB()

        observations = await _run_safe_graph_native_probe(
            "What raw dataset is used to make PreprocessedDataset1?",
            "mllo4",
            graphdb,
        )

        self.assertEqual(observations["search_terms"][0], "PreprocessedDataset1")
        self.assertIn('BIND("PreprocessedDataset1" AS ?matched_term)', graphdb.queries[0])
        self.assertIn("ORDER BY ?match_rank ?node_kind_rank", graphdb.queries[0])
        self.assertEqual(observations["results"][0]["payload"][0]["node"], "http://example.com/MNIST#PreprocessedDataset1")

    async def test_graph_native_probe_can_include_optional_lucene_seed_discovery(self) -> None:
        graphdb = ProbeCaptureGraphDB()

        with patch.dict("os.environ", {"GRAPHDB_LUCENE_CONNECTOR": "mllo_search"}):
            observations = await _run_safe_graph_native_probe(
                "What raw dataset is used to make PreprocessedDataset1?",
                "mllo4",
                graphdb,
            )

        self.assertTrue(any("luc:query" in query for query in graphdb.queries))
        self.assertIn("graphdb_lucene_term_search", [result["tool"] for result in observations["results"]])

    def test_observed_seed_iris_canonicalize_generated_constants(self) -> None:
        observations = {
            "results": [
                {
                    "tool": "local_filter_by_string",
                    "payload": [
                        {
                            "matched_term": "MnistG16",
                            "node": "http://example.com/MNIST#MnistG16",
                            "type": "http://www.w3.org/2002/07/owl#NamedIndividual",
                            "match_rank": "0",
                            "node_kind_rank": "1",
                        }
                    ],
                }
            ]
        }

        canonical_iris = _canonical_iris_from_graph_observations(observations)
        rewritten, replacements = _canonicalize_sparql_iri_constants(
            "SELECT ?x WHERE { ?p ml:hasDataInput <http://example/MnistG16> . }",
            canonical_iris,
        )

        self.assertIn("<http://example.com/MNIST#MnistG16>", rewritten)
        self.assertEqual(replacements[0]["from"], "http://example/MnistG16")
        self.assertEqual(replacements[0]["to"], "http://example.com/MNIST#MnistG16")

    def test_observed_node_hops_synthesize_upstream_candidate(self) -> None:
        observations = {
            "results": [
                {
                    "tool": "local_filter_by_string",
                    "payload": [
                        {
                            "matched_term": "PreprocessedDataset1",
                            "node": "http://example.com/MNIST#PreprocessedDataset1",
                            "type": "http://www.w3.org/2002/07/owl#NamedIndividual",
                            "match_rank": "0",
                            "node_kind_rank": "1",
                        }
                    ],
                },
                {
                    "tool": "local_node_hops",
                    "payload": [
                        {
                            "seed": "http://example.com/MNIST#PreprocessedDataset1",
                            "direction": "outgoing",
                            "property": f"{ML_NS}informationContentEntityDerivedFrom",
                            "neighbor": "http://example.com/MNIST#MnistG16",
                        }
                    ],
                },
            ]
        }

        candidates = dict(
            _observed_node_hop_answer_candidates(
                "What was used to create PreprocessedDataset1?",
                observations,
                self._minimal_ontology_context(),
            )
        )

        self.assertIn("observed_upstream_direct_informationContentEntityDerivedFrom", candidates)
        self.assertIn("<http://example.com/MNIST#PreprocessedDataset1>", candidates["observed_upstream_direct_informationContentEntityDerivedFrom"])
        self.assertIn(f"<{ML_NS}informationContentEntityDerivedFrom>", candidates["observed_upstream_direct_informationContentEntityDerivedFrom"])

    def test_answer_slots_do_not_treat_identifier_fragments_as_requested_slots(self) -> None:
        self.assertEqual(_required_answer_slots("What was used to create PreprocessedDataset1?"), [])
        self.assertEqual(_required_answer_slots("Show me models with their test dataset and pipeline"), ["model", "test_dataset", "pipeline"])

    async def test_custom_sparql_uses_observed_canonical_iri_before_querying(self) -> None:
        observations = {
            "search_term": "MnistG16",
            "results": [
                {
                    "tool": "local_filter_by_string",
                    "payload": [
                        {
                            "matched_term": "MnistG16",
                            "node": "http://example.com/MNIST#MnistG16",
                            "type": "http://www.w3.org/2002/07/owl#NamedIndividual",
                            "match_rank": "0",
                            "node_kind_rank": "1",
                        }
                    ],
                }
            ],
        }
        graphdb = CanonicalIriGraphDB()

        with patch(
            "mllo_web.core.workflows.nlq_graph._run_safe_graph_native_probe",
            new=AsyncMock(return_value=observations),
        ), patch(
            "mllo_web.core.workflows.nlq_graph.generate_sparql",
            new=AsyncMock(
                return_value=(
                    "SELECT ?downstreamArtifact WHERE { ?pipeline ml:hasDataInput <http://example/MnistG16> . ?pipeline ml:hasDataOutput ?downstreamArtifact . } LIMIT 100",
                    {"prefixes": {"ml": ML_NS}},
                )
            ),
        ):
            response, state = await execute_nlq_graph(
                question="What downstream artifacts use MnistG16?",
                repo="mllo4",
                answer_mode="auto",
                settings=MLLESettings(graphdb_default_repo="mllo4"),
                graphdb_client=graphdb,
                gateway=FakeGateway(intent_tool="custom_sparql"),
                force_custom_sparql=True,
            )

        self.assertEqual(response.execution_tool, "custom_sparql")
        self.assertEqual(response.results, [{"downstreamArtifact": "http://example.com/MNIST#PreprocessedDataset1"}])
        self.assertIn("sparql_canonical_iri_rewrite_1", state.artifacts)
        self.assertTrue(any("<http://example.com/MNIST#MnistG16>" in query for query in graphdb.executed_sparql))

    async def test_empty_result_debug_flags_zero_support_predicates(self) -> None:
        ctx = {
            "prefixes": {
                "ml": ML_NS,
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            }
        }
        sparql = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT ?model WHERE {
  ?evaluation ml:hasDataOutput ?result .
  ?model ml:evaluatedBy ?evaluation .
  ?evaluation a ml:ModelEvaluation .
}
LIMIT 100
"""

        debug = await _debug_empty_sparql(sparql, ctx, EmptyDebugGraphDB(), "mllo4")

        self.assertIn("ml:evaluatedBy", debug["zero_support_predicates"])
        self.assertNotIn("ml:hasDataOutput", debug["zero_support_predicates"])

    async def test_pure_custom_sparql_prompt_has_no_hardcoded_examples_or_rules(self) -> None:
        gateway = PromptCaptureGateway()
        grounding_context = {
            "prompt_mode": "pure_node_hops",
            "graph_native_observations": {"local_node_hops": [{"node": "PreprocessedDataset1", "outgoing": []}]},
        }

        with patch(
            "mllo_web.core.workflows.generation.load_ontology_context",
            new=AsyncMock(return_value=self._minimal_ontology_context()),
        ):
            await generate_sparql(
                "Show me models with performance more than 0.9",
                "mllo4",
                MLLESettings(graphdb_default_repo="mllo4"),
                FakeGraphDB(),
                gateway,
                grounding_context=grounding_context,
                enhanced_prompt=False,
            )

        prompt_text = "\n".join(message["content"] for message in gateway.messages_by_purpose["sparql_generation"])
        self.assertIn("pure_node_hops", prompt_text)
        self.assertIn("Graph observations", prompt_text)
        self.assertNotIn("ENTITY DEFINITIONS", prompt_text)
        self.assertNotIn("KEY PATTERNS", prompt_text)
        self.assertNotIn("EXAMPLE QUERIES", prompt_text)
        self.assertNotIn("Models above an accuracy threshold", prompt_text)
        self.assertNotIn("Name matching rule", prompt_text)
        self.assertNotIn("Dataset type rule", prompt_text)
        self.assertNotIn("Schema grounding rule", prompt_text)

    async def test_enhanced_custom_sparql_prompt_keeps_optional_grounding_examples(self) -> None:
        gateway = PromptCaptureGateway()
        grounding_context = {
            "prompt_mode": "enhanced_schema_grounding",
            "schema_bridge_grounding": {"candidate_class_paths": []},
        }

        with patch(
            "mllo_web.core.workflows.generation.load_ontology_context",
            new=AsyncMock(return_value=self._minimal_ontology_context()),
        ):
            await generate_sparql(
                "Show me models with performance more than 0.9",
                "mllo4",
                MLLESettings(graphdb_default_repo="mllo4"),
                FakeGraphDB(),
                gateway,
                grounding_context=grounding_context,
                enhanced_prompt=True,
            )

        prompt_text = "\n".join(message["content"] for message in gateway.messages_by_purpose["sparql_generation"])
        self.assertIn("ENTITY DEFINITIONS", prompt_text)
        self.assertIn("EXAMPLE QUERIES", prompt_text)
        self.assertIn("Name matching rule", prompt_text)
        self.assertIn("Dataset type rule", prompt_text)
        self.assertIn("Schema grounding rule", prompt_text)
        self.assertIn("schema_bridge_grounding", prompt_text)

    def test_pure_empty_result_repair_does_not_reintroduce_examples(self) -> None:
        repair_messages = build_empty_result_repair_messages(
            "Trace the lineage of PreprocessedDataset1 upstream.",
            "SELECT ?x WHERE { ?x ?p ?o } LIMIT 100",
            self._minimal_ontology_context(),
            {"prompt_mode": "pure_node_hops", "graph_native_observations": {"local_node_hops": []}},
            enhanced_prompt=False,
        )

        prompt_text = "\n".join(message["content"] for message in repair_messages)
        self.assertIn("pure_node_hops", prompt_text)
        self.assertNotIn("EXAMPLE QUERIES", prompt_text)
        self.assertNotIn("Name matching rule", prompt_text)
        self.assertNotIn("Dataset type rule", prompt_text)
        self.assertNotIn("Schema grounding rule", prompt_text)

    def test_sparql_validation_rejects_class_used_as_property_path_predicate(self) -> None:
        ctx = {
            "prefixes": {
                "ml": "http://www.semanticweb.org/mnd14/ml/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            },
            "classes": [{"iri": "http://www.semanticweb.org/mnd14/ml/MachineLearningModelDevelopmentPipeline"}],
            "object_properties": [{"iri": "http://www.semanticweb.org/mnd14/ml/hasDataInput"}],
            "datatype_properties": [],
            "annotation_properties": [],
            "individuals": [],
        }
        sparql = "SELECT ?x WHERE { ?x a/ml:MachineLearningModelDevelopmentPipeline ?y }"

        errors = validate_sparql(sparql, ctx)

        self.assertTrue(any("Class used as property-path predicate" in error for error in errors))

    def test_sparql_validation_allows_named_individual_constants(self) -> None:
        ctx = {
            "prefixes": {
                "ml": "http://www.semanticweb.org/mnd14/ml/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            },
            "classes": [{"iri": "http://www.semanticweb.org/mnd14/ml/MachineLearningDataSet"}],
            "object_properties": [{"iri": "http://www.semanticweb.org/mnd14/ml/hasDataInput"}],
            "datatype_properties": [],
            "annotation_properties": [],
            "individuals": [],
        }
        sparql = "SELECT ?process WHERE { ?process ml:hasDataInput ml:PreprocessedDataset1 . }"

        errors = validate_sparql(sparql, ctx)

        self.assertEqual(errors, [])

    def test_sparql_validation_ignores_prefix_like_text_in_comments(self) -> None:
        ctx = {
            "prefixes": {
                "ml": "http://www.semanticweb.org/mnd14/ml/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            },
            "classes": [],
            "object_properties": [
                {"iri": "http://www.semanticweb.org/mnd14/ml/hasDataInput"},
                {"iri": "http://www.semanticweb.org/mnd14/ml/hasDataOutput"},
            ],
            "datatype_properties": [],
            "annotation_properties": [],
            "individuals": [],
        }
        sparql = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT ?artifact WHERE {
  # 3-hop downstream: this comment is not a prefix use
  ?process ml:hasDataInput ?dataset .
  ?process ml:hasDataOutput ?artifact .
}
"""

        errors = validate_sparql(sparql, ctx)

        self.assertEqual(errors, [])

    def test_unknown_property_validation_is_nonfatal_for_execution_probe(self) -> None:
        ctx = {
            "prefixes": {"ml": "http://www.semanticweb.org/mnd14/ml/"},
            "classes": [],
            "object_properties": [],
            "datatype_properties": [],
            "annotation_properties": [],
            "individuals": [],
        }
        sparql = "SELECT ?x WHERE { ?x ml:possiblyMissingFromSchema ?y . }"

        errors = validate_sparql(sparql, ctx)

        self.assertGreater(len(errors), 0)
        self.assertEqual(fatal_validation_errors(errors), [])

    def test_empty_result_fallback_rewrites_label_and_type_constraints(self) -> None:
        sparql = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?pipeline WHERE {
  ?dataset a ml:MachineLearningDataSet ;
           rdfs:label "PreprocessedDataset1" .
  ?pipeline ml:hasDataOutput ?dataset .
}
LIMIT 100
"""

        candidates = dict(empty_result_fallback_candidates(sparql))

        self.assertIn("replace_label_constraints_with_iri_local_name_matching", candidates)
        self.assertIn('STRAFTER(STR(?dataset), "#")', candidates["replace_label_constraints_with_iri_local_name_matching"])
        self.assertIn("?dataset rdf:type/rdfs:subClassOf* ?dataset_type", candidates["replace_label_constraints_with_iri_local_name_matching"])

    def test_empty_result_fallback_removes_standalone_type_constraints(self) -> None:
        sparql = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?process WHERE {
  ?dataset rdf:type/rdfs:subClassOf* ?dataset_type .
  ?process ml:hasDataInput ?dataset .
}
LIMIT 100
"""

        candidates = dict(empty_result_fallback_candidates(sparql))

        self.assertIn("remove_simple_variable_type_constraints", candidates)
        self.assertNotIn("rdf:type/rdfs:subClassOf* ?dataset_type", candidates["remove_simple_variable_type_constraints"])
        self.assertIn("?process ml:hasDataInput ?dataset", candidates["remove_simple_variable_type_constraints"])

    def test_relationship_fallback_candidates_use_stable_output_dataset_alias(self) -> None:
        candidates = dict(relationship_fallback_candidates("Which model outputs are later used as inputs to another process?"))

        self.assertIn("model_output_reused_as_downstream_input", candidates)
        self.assertIn("SELECT DISTINCT ?output_dataset ?downstream_process", candidates["model_output_reused_as_downstream_input"])
        self.assertIn("?downstream_process ml:hasDataInput ?output_dataset", candidates["model_output_reused_as_downstream_input"])

    async def test_schema_bridge_grounding_exposes_observed_class_paths(self) -> None:
        grounding = await schema_bridge_grounding(
            "Which models perform best based on test dataset?",
            SchemaBridgeFakeGraphDB(),
            "mllo4",
        )

        self.assertIn("candidate_class_paths", grounding)
        self.assertIn("relevant_observed_edges", grounding)
        self.assertIn("TestDataSet", grounding["seed_classes"])
        self.assertIn("MachineLearningModel", grounding["target_classes"])
        self.assertTrue(
            any("ModelExecution" in " ".join(path["path"]) for path in grounding["candidate_class_paths"])
            or any(edge["source_class"] == "ModelExecution" for edge in grounding["relevant_observed_edges"])
        )

    async def test_structured_intent_uses_graph_and_preserves_response_shape(self) -> None:
        response, state = await execute_nlq_graph(
            question="Which models use MnistG16?",
            repo="mllo4",
            answer_mode="auto",
            settings=MLLESettings(graphdb_default_repo="mllo4"),
            graphdb_client=FakeGraphDB(),
            gateway=FakeGateway(intent_tool="find_models"),
        )

        self.assertEqual(response.intent.tool, "find_models")
        self.assertEqual(response.repo_used, "mllo4")
        self.assertGreater(len(response.results), 0)
        self.assertEqual(state.artifacts["orchestration"]["engine"], "langgraph")
        self.assertEqual(state.steps[0].tool, "find_models")

    async def test_custom_question_runs_graph_native_probe_before_custom_sparql(self) -> None:
        with patch(
            "mllo_web.core.workflows.nlq_graph._run_safe_graph_native_probe",
            new=AsyncMock(return_value={"search_term": "MnistG16", "results": [{"tool": "filter_by_string", "payload": {"results": []}}]}),
        ), patch(
            "mllo_web.core.workflows.nlq_graph.generate_sparql",
            new=AsyncMock(return_value=("SELECT ?model WHERE { ?model ?p ?o } LIMIT 10", {"prefixes": []})),
        ):
            response, state = await execute_nlq_graph(
                question="Which models and pipelines share the same dataset?",
                repo="mllo4",
                answer_mode="auto",
                settings=MLLESettings(graphdb_default_repo="mllo4"),
                graphdb_client=FakeGraphDB(),
                gateway=FakeGateway(intent_tool="custom_sparql"),
            )

        self.assertEqual(response.intent.tool, "custom_sparql")
        self.assertIn("graph_native_observations", state.artifacts)
        self.assertEqual([step.tool for step in state.steps], ["safe_ontology_probe", "custom_sparql"])

    async def test_contextual_custom_question_is_not_rerouted_by_previous_performance_context(self) -> None:
        question = """Conversation context:
User: Show me models with performance more than 0.9, their test dataset, and their pipeline.
Assistant: MLModel1 has performance more than 0.9.

Current user question: Which pipelines share a dataset with the MLmodel1?
Resolve references to earlier turns when needed. If the current question stands on its own, prioritize the current question."""
        with patch(
            "mllo_web.core.workflows.nlq_graph._run_safe_graph_native_probe",
            new=AsyncMock(return_value={"search_term": "MLmodel1", "results": []}),
        ), patch(
            "mllo_web.core.workflows.nlq_graph.generate_sparql",
            new=AsyncMock(return_value=("SELECT ?pipeline WHERE { ?pipeline ?p ?dataset } LIMIT 10", {"prefixes": []})),
        ):
            response, state = await execute_nlq_graph(
                question=question,
                repo="mllo4",
                answer_mode="auto",
                settings=MLLESettings(graphdb_default_repo="mllo4"),
                graphdb_client=FakeGraphDB(),
                gateway=FakeGateway(intent_tool="custom_sparql"),
            )

        self.assertEqual(response.intent.tool, "custom_sparql")
        self.assertEqual(response.execution_tool, "custom_sparql")
        self.assertEqual([step.tool for step in state.steps], ["safe_ontology_probe", "custom_sparql"])

    async def test_force_custom_sparql_bypasses_performance_route(self) -> None:
        with patch(
            "mllo_web.core.workflows.nlq_graph._run_safe_graph_native_probe",
            new=AsyncMock(return_value={"search_term": "performance", "results": []}),
        ), patch(
            "mllo_web.core.workflows.nlq_graph.generate_sparql",
            new=AsyncMock(return_value=("SELECT ?model WHERE { ?model ?p ?o } LIMIT 10", {"prefixes": []})),
        ) as generated:
            response, state = await execute_nlq_graph(
                question="Show me models with performance more than 0.9",
                repo="mllo4",
                answer_mode="auto",
                settings=MLLESettings(graphdb_default_repo="mllo4"),
                graphdb_client=FakeGraphDB(),
                gateway=FakeGateway(intent_tool="custom_sparql"),
                force_custom_sparql=True,
            )

        generated.assert_awaited_once()
        self.assertEqual(response.execution_tool, "custom_sparql")
        self.assertEqual([step.tool for step in state.steps], ["safe_ontology_probe", "custom_sparql"])

    async def test_custom_sparql_repair_records_attempt_and_returns_repaired_results(self) -> None:
        with patch(
            "mllo_web.core.workflows.nlq_graph._run_safe_graph_native_probe",
            new=AsyncMock(return_value={"search_term": "model output", "results": []}),
        ), patch(
            "mllo_web.core.workflows.nlq_graph.generate_sparql",
            new=AsyncMock(return_value=("SELECT BAD WHERE {", {"prefixes": []})),
        ):
            response, state = await execute_nlq_graph(
                question="Which datasets are produced by processes that also use a model output?",
                repo="mllo4",
                answer_mode="auto",
                settings=MLLESettings(graphdb_default_repo="mllo4"),
                graphdb_client=FakeGraphDB(fail_first_query=True),
                gateway=FakeGateway(intent_tool="custom_sparql"),
            )

        self.assertEqual(response.intent.tool, "custom_sparql")
        self.assertEqual(state.artifacts["sparql_repair_attempts"], 1)
        self.assertIn("sparql_repair_1", state.artifacts)
        self.assertEqual(state.steps[-1].tool, "custom_sparql")

    async def test_custom_sparql_passes_schema_bridge_grounding_to_llm(self) -> None:
        with patch(
            "mllo_web.core.workflows.nlq_graph._run_safe_graph_native_probe",
            new=AsyncMock(return_value={"search_term": "test dataset", "results": []}),
        ), patch(
            "mllo_web.core.workflows.nlq_graph.generate_sparql",
            new=AsyncMock(
                return_value=(
                    "SELECT ?model_name ?test_dataset ?model_performance_value WHERE { ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment . ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value . } LIMIT 10",
                    {"prefixes": {"ml": ML_NS, "iof-core": "https://spec.industrialontologies.org/ontology/core/Core/"}},
                )
            ),
        ) as generated:
            response, state = await execute_nlq_graph(
                question="Which models perform best based on test dataset?",
                repo="mllo4",
                answer_mode="auto",
                settings=MLLESettings(graphdb_default_repo="mllo4"),
                graphdb_client=SchemaBridgeFakeGraphDB(),
                gateway=FakeGateway(intent_tool="custom_sparql"),
                force_custom_sparql=True,
                custom_sparql_enhanced_prompt=True,
            )

        grounding_context = generated.await_args.kwargs["grounding_context"]
        self.assertEqual(response.execution_tool, "custom_sparql")
        self.assertEqual(state.artifacts["custom_sparql_prompt_mode"], "enhanced_schema_grounding")
        self.assertTrue(generated.await_args.kwargs["enhanced_prompt"])
        self.assertIn("schema_bridge_grounding", grounding_context)
        self.assertIn("schema_bridge_grounding", state.artifacts)
        self.assertIn("candidate_class_paths", grounding_context["schema_bridge_grounding"])
        self.assertGreater(len(response.results), 0)
        self.assertIn("test_dataset", response.results[0])
        self.assertIn("model_performance_value", response.results[0])

    async def test_forced_custom_sparql_defaults_to_pure_node_hop_prompt(self) -> None:
        with patch(
            "mllo_web.core.workflows.nlq_graph._run_safe_graph_native_probe",
            new=AsyncMock(return_value={"search_term": "test dataset", "results": []}),
        ), patch(
            "mllo_web.core.workflows.nlq_graph.generate_sparql",
            new=AsyncMock(
                return_value=(
                    "SELECT ?model_name ?test_dataset ?model_performance_value WHERE { ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment . ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value . } LIMIT 10",
                    {"prefixes": {"ml": ML_NS, "iof-core": "https://spec.industrialontologies.org/ontology/core/Core/"}},
                )
            ),
        ) as generated:
            response, state = await execute_nlq_graph(
                question="Which models perform best based on test dataset?",
                repo="mllo4",
                answer_mode="auto",
                settings=MLLESettings(graphdb_default_repo="mllo4"),
                graphdb_client=SchemaBridgeFakeGraphDB(),
                gateway=FakeGateway(intent_tool="custom_sparql"),
                force_custom_sparql=True,
            )

        grounding_context = generated.await_args.kwargs["grounding_context"]
        self.assertEqual(response.execution_tool, "custom_sparql")
        self.assertEqual(state.artifacts["custom_sparql_prompt_mode"], "pure_node_hops")
        self.assertFalse(generated.await_args.kwargs["enhanced_prompt"])
        self.assertEqual(grounding_context["prompt_mode"], "pure_node_hops")
        self.assertNotIn("schema_bridge_grounding", grounding_context)
        self.assertNotIn("schema_bridge_grounding", state.artifacts)

    async def test_execute_nlq_falls_back_to_legacy_only_for_graph_orchestration_error(self) -> None:
        legacy_response = await execute_nlq_graph(
            question="Which models use MnistG16?",
            repo="mllo4",
            answer_mode="auto",
            settings=MLLESettings(graphdb_default_repo="mllo4"),
            graphdb_client=FakeGraphDB(),
            gateway=FakeGateway(intent_tool="find_models"),
        )
        with patch("mllo_web.core.workflows.nlq.execute_nlq_graph", new=AsyncMock(side_effect=LangGraphOrchestrationError("broken graph"))), patch(
            "mllo_web.core.workflows.nlq.execute_nlq_legacy",
            new=AsyncMock(return_value=legacy_response[0]),
        ) as legacy:
            response = await execute_nlq("Which models use MnistG16?", repo="mllo4", answer_mode="auto")

        self.assertEqual(response.intent.tool, "find_models")
        legacy.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
