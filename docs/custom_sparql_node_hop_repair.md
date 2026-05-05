# Custom SPARQL Pure Node-Hop Repair Notes

This note documents the changes made to make forced `custom_sparql` work for questions such as:

```text
Show me models with performance more than 0.9, their test dataset, and their pipeline.
```

The goal was not to add a deterministic performance route. The goal was to keep pure custom SPARQL as an experiment in LLM query generation grounded by ontology and graph evidence.

## Problem

The original forced `custom_sparql` path could find nearby graph nodes, but it often joined them incorrectly.

For the prompt above, the LLM repeatedly did this:

1. Found performance values on `ModelPerformanceResult`.
2. Joined to `ModelEvaluation`.
3. Bound `?test_dataset` through `ModelEvaluation ml:hasDataInput ?test_dataset`.
4. Forced `?test_dataset rdf:type ml:TestDataSet`.

That collapsed to zero rows because the node bound by `ModelEvaluation ml:hasDataInput` is actually a `ModelOutputDataSet`, not the final test dataset. The real route is:

```text
ModelPerformanceResult
<- ml:hasDataOutput -
ModelEvaluation
- ml:hasDataInput ->
ModelOutputDataset
<- ml:hasDataOutput -
ModelExecution
- ml:executes ->
MLModel

ModelExecution
- ml:hasDataInput ->
PreprocessedDataset / TestDataSet
```

The earlier system also accepted some non-empty results even when selected columns were semantically wrong, for example returning `ModelOutputDataset` as the test dataset or omitting the model/performance value.

## What We Tried That Did Not Work

These attempts were useful diagnostically, but they were not enough to make pure `custom_sparql` reliable.

### 1. Prompt-Only Repair

The first repair approach was to send the failed SPARQL back to the LLM with a generic message:

```text
The SPARQL executed successfully but returned zero rows. Revise it using the ontology vocabulary.
```

This did not work consistently. The model often regenerated almost the same query, still binding:

```sparql
?evaluation ml:hasDataInput ?test_dataset .
?test_dataset rdf:type ml:TestDataSet .
```

The prompt told the model that the query was wrong, but it did not show which join was wrong or what nearby graph node could repair it.

### 2. Global Predicate And Class Counts

We added debug evidence such as:

```text
ml:hasDataInput count = 54
ml:hasDataOutput count = 54
ml:ModelEvaluation count = 18
ml:TestDataSet count = 18
```

This helped prove that the vocabulary existed, but it did not explain why the join failed. The bad query used valid predicates and valid classes; the failure was at the join level.

In this case, global counts were misleading because all these facts were true:

- `ml:hasDataInput` exists.
- `ml:TestDataSet` exists.
- `ModelEvaluation ml:hasDataInput ?x` exists.
- `?x rdf:type ml:TestDataSet` does not hold for that `?x`.

So global counts were not enough.

### 3. Numeric Filter Coercion Alone

We added a generic rewrite from:

```sparql
FILTER(?value > 0.9)
```

to:

```sparql
FILTER(xsd:decimal(?value) > 0.9)
```

This fixed one real class of failures, because GraphDB literal comparisons can otherwise behave unexpectedly. But it only solved numeric filtering. It did not fix wrong graph routes, missing selected answer variables, or incorrect class constraints.

### 4. Raw Observed Join Skeletons

We exposed raw `observed_join_skeletons` to the LLM. These were generated from real graph hops around literal values.

This contained the needed route, but it was too noisy. The prompt included many rows where `ModelEvaluation` nodes shared the same metric, and those rows appeared before the more useful `ModelOutputDataset -> ModelExecution` bridge.

The model saw lots of valid-looking evidence and still selected the wrong bridge.

This led to the later `observed_bridge_patterns` compaction and ranking.

### 5. Accepting Any Non-Empty Candidate

At one point, a route repair candidate returned rows, so the loop accepted it. The result was non-empty but wrong:

- the selected "test dataset" column contained `ModelOutputDataset*`
- the model column was missing
- the performance value column was missing

This showed that row count is not a sufficient success condition. A query must satisfy the requested answer slots, not merely return nearby graph nodes.

This led to answer-slot semantic validation.

### 6. Semantic Repair Prompt Alone

After adding semantic validation, the loop correctly rejected non-empty wrong tables. However, asking the LLM to repair from `answer_semantic_debug` alone was still not reliable.

The model understood that columns were missing, but often kept the same incorrect route or selected a loosely related pipeline:

```sparql
?pipeline bfo:BFO_0000063 ?execution .
```

without connecting that execution to the specific model output or evaluation result.

This showed that semantic validation can detect failure, but it also needs route evidence or a graph-derived candidate to recover.

### 7. Generic Class-Constraint Bridge Repair Alone

The class-constraint bridge repair successfully rewrote the collapsing dataset join:

```sparql
?evaluation ml:hasDataInput ?test_dataset_bridge .
?test_dataset_bridge ml:informationContentEntityDerivedFrom ?test_dataset .
?test_dataset rdf:type ml:TestDataSet .
```

That repaired the dataset part, but the query could still be semantically incomplete. For example, it could still omit `?model` or `?performance_value`, or bind a pipeline that was not connected tightly enough to the performance row.

So the bridge repair was necessary but not sufficient.

### 8. Large First-Pass Grounding

When we added richer graph observations, the first prompt grew past 100k characters. This was too large for the intended harness window and made the model more likely to miss the relevant rows.

The fix was not to remove grounding, but to compact and rank it:

- fewer raw term-match rows
- fewer raw skeleton rows
- more focused bridge rows
- repair contexts reduced to the first collapsing join and answer-slot failures

### 9. Enhanced Grounding

Enhanced grounding can solve this kind of prompt more directly because it includes curated MLLO patterns and examples. However, that was not the experiment here.

For this test, enhanced grounding was intentionally kept off. The pure path needed to succeed using graph observations and ontology structure, not hand-authored query examples.

### 10. Trusting LLM Constants Without Canonicalization

Later lineage/downstream prompts showed another general failure:

```sparql
<http://example/PreprocessedDataset1>
<http://example/MnistG16>
```

The graph probe had already found the real IRIs:

```text
http://example.com/MNIST#PreprocessedDataset1
http://example.com/MNIST#MnistG16
```

But the generated SPARQL kept using invented namespaces. Join debugging correctly showed zero rows, but the repair loop did not rewrite the bad constants.

### 11. Treating Identifier Fragments As Requested Slots

Semantic validation initially matched terms inside identifiers. For example:

```text
What was used to create PreprocessedDataset1?
```

was treated as requiring a generic `dataset` answer slot because `dataset` appears inside `PreprocessedDataset1`. That caused valid source answers such as `MnistG16` to be rejected.

## Constraints

The pure path must remain different from enhanced grounding.

- Pure `custom_sparql` may use ontology schema, term matches, node hops, observed individual hops, literal properties, join skeletons, and repair diagnostics.
- Pure `custom_sparql` must not rely on curated MLLO query examples or hardcoded performance-query templates.
- Enhanced grounding can keep curated terms, patterns, and examples as an optional mode.

## Implemented Flow

### 1. Compact Pure Graph Observations

`mllo_web/core/workflows/nlq_graph.py` now compacts graph-native probe output before sending it to the LLM.

The prompt keeps evidence from:

- approximate term matches
- seed node hops
- class instance expansion
- individual hops
- literal properties
- observed bridge patterns
- observed join skeletons
- short candidate connection paths

The prompt budget was reduced to roughly 65k characters for the target prompt, keeping it under the intended 100k context window.

### 2. Observed Bridge Patterns

Raw join skeletons were too noisy. I added `observed_bridge_patterns`, a condensed representation derived from actual node hops around literal values.

A bridge pattern records:

```text
literal_value
literal_source
shared_neighbor
bridge_node
bridge_out_property
bridge_out_neighbor
```

For the target query, this surfaces evidence like:

```text
EvaluationResult1 --value--> 0.9789
ModelEvaluation1 --hasDataInput--> ModelOutputDataset1
ModelExecution1 --hasDataOutput--> ModelOutputDataset1
ModelExecution1 --executes--> MLModel1
ModelExecution1 --hasDataInput--> PreprocessedDataset1
```

Bridge rows are ranked so data-flow and `ModelExecution` pivots appear before lower-value metric-sharing rows.

### 3. Join-Level Debugging

When a generated SPARQL returns zero rows, the repair loop now probes each clause cumulatively.

It records:

- per-clause counts
- cumulative join counts
- first collapsing join/filter
- sample variable bindings at collapse
- neighborhoods for the collapsing variable
- pivot contexts around that variable

This exposed the key failure:

```text
?test_dataset rdf:type ml:TestDataSet
```

collapsed because `?test_dataset` was actually bound to `ModelOutputDataset*`.

The neighborhood probe showed the needed bridge:

```text
ModelOutputDataset* ml:informationContentEntityDerivedFrom PreprocessedDataset*
```

### 4. Generic Bridge Repair Candidate

The repair loop now has a generic class-constraint bridge repair.

If a variable is bound to the wrong class but its observed neighborhood contains a node of the requested class, the repair rewrites:

```sparql
?evaluation ml:hasDataInput ?test_dataset .
?test_dataset rdf:type ml:TestDataSet .
```

into:

```sparql
?evaluation ml:hasDataInput ?test_dataset_bridge .
?test_dataset_bridge ml:informationContentEntityDerivedFrom ?test_dataset .
?test_dataset rdf:type ml:TestDataSet .
```

This is not specific to test datasets. It is driven by the first collapsing class constraint plus observed neighboring nodes.

### 5. Answer-Slot Semantic Validation

Non-empty results are no longer automatically accepted.

For each question, the system infers required answer slots from the wording. For the target question, the required slots are:

```text
model
performance_value
test_dataset
pipeline
```

The system checks that selected columns satisfy those slots:

- model columns must bind model-like individuals/classes.
- performance columns must contain numeric literals.
- test dataset columns must bind `ml:TestDataSet` instances.
- pipeline/process columns must be selected and non-empty.

If the table is non-empty but semantically wrong, the loop treats it as a repairable failure instead of returning it.

### 6. Observed Bridge Answer Synthesis

If the LLM still misses the answer slots, the loop can synthesize a candidate query directly from `observed_bridge_patterns`.

This is still pure graph-grounded behavior:

- It uses only properties/classes discovered in the graph observations.
- It does not call the deterministic performance route.
- It does not use the enhanced example prompt.

For the target prompt, the synthesized query was:

```sparql
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?model ?performance_value ?test_dataset ?pipeline WHERE {
  ?performance_result iof-core:hasSimpleExpressionValue ?performance_value .
  FILTER(xsd:decimal(?performance_value) > 0.9)
  ?literal_source ml:hasDataOutput ?performance_result .
  ?literal_source ml:hasDataInput ?shared_artifact .
  ?pipeline ml:hasDataOutput ?shared_artifact .
  ?pipeline ml:executes ?model .
  ?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
  ?pipeline ml:hasDataInput ?test_dataset .
  ?test_dataset rdf:type/rdfs:subClassOf* ml:TestDataSet .
}
LIMIT 100
```

### 7. Observed Canonical IRI Rewrite

Generated SPARQL constants are now checked against exact seed IRIs found by the graph probe.

If the LLM writes:

```sparql
<http://example/MnistG16>
```

and graph observations contain:

```text
http://example.com/MNIST#MnistG16
```

the execution loop rewrites the constant before querying GraphDB. This is graph-observation-driven; it does not infer a domain route.

### 8. Observed Node-Hop Answer Candidates

For direct lineage/downstream questions, the repair loop can now synthesize a candidate directly from observed seed hops.

Example observed hop:

```text
PreprocessedDataset1
- ml:informationContentEntityDerivedFrom ->
MnistG16
```

Candidate:

```sparql
SELECT DISTINCT ?source ?source_type WHERE {
  <http://example.com/MNIST#PreprocessedDataset1>
    <http://www.semanticweb.org/mnd14/ml/informationContentEntityDerivedFrom>
    ?source .
  FILTER(isIRI(?source))
  OPTIONAL { ?source rdf:type ?source_type }
}
LIMIT 100
```

This keeps the pure path graph-grounded: it only uses observed seed nodes, observed predicates, and ontology property names already discovered in the graph.

### 9. Word-Boundary Answer-Slot Detection

Answer-slot inference now matches real words, not substrings inside identifiers.

So:

```text
Show me models with their test dataset and pipeline
```

still requires:

```text
model, test_dataset, pipeline
```

but:

```text
What was used to create PreprocessedDataset1?
```

does not incorrectly require a generic `dataset` output column.

## Verified Result

Live forced pure custom SPARQL was run with:

- repo: `mllo4`
- enhanced grounding: off
- provider observed in the test: `lm_studio google/gemma-4-e4b`
- prompt: `Show me models with performance more than 0.9, their test dataset, and their pipeline.`

It returned 8 rows:

```text
MLModel1  0.9789  PreprocessedDataset1   ModelExecution1
MLModel2  0.9671  PreprocessedDataset13  ModelExecution13
MLModel1  0.9671  PreprocessedDataset2   ModelExecution2
MLModel3  0.9236  PreprocessedDataset23  ModelExecution23
MLModel3  0.9234  PreprocessedDataset25  ModelExecution25
MLModel1  0.9807  PreprocessedDataset4   ModelExecution4
MLModel1  0.9803  PreprocessedDataset5   ModelExecution5
MLModel1  0.9675  PreprocessedDataset6   ModelExecution6
```

The semantic validator confirmed:

- `model` values are machine learning model instances.
- `performance_value` is numeric.
- `test_dataset` values are `ml:TestDataSet`.
- `pipeline` values are the exact `ModelExecution*` nodes.

Additional forced pure custom checks:

```text
What downstream artifacts use MnistG16?
```

returned rows after canonicalizing `MnistG16` to `http://example.com/MNIST#MnistG16`.

```text
What was used to create PreprocessedDataset1?
```

returned:

```text
MnistG16
```

with SPARQL:

```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?Source
WHERE {
  <http://example.com/MNIST#PreprocessedDataset1> ml:informationContentEntityDerivedFrom ?Source .
}
LIMIT 100
```

## Verification Commands

```bash
conda run -n mlloweb python -m py_compile \
  mllo_web/core/workflows/generation.py \
  mllo_web/core/workflows/nlq_graph.py

conda run -n mlloweb python -m unittest tests.nlq.test_langgraph_orchestration
```

Both passed.

## Files Changed

Main logic:

- `mllo_web/core/workflows/nlq_graph.py`
- `mllo_web/core/workflows/generation.py`

Key areas:

- pure node-hop prompt compaction
- observed bridge pattern extraction/ranking
- join-level zero-row debugging
- generic class-constraint bridge repair
- answer-slot semantic validation
- observed bridge answer synthesis
- observed canonical IRI rewriting
- observed node-hop answer candidates
- word-boundary answer-slot detection
- repair prompt guidance for semantic failures

## Remaining Notes

This improves the pure custom SPARQL harness, but it does not make LLM query generation magically reliable. The important change is that the loop now has graph-grounded checks and repair evidence:

- If a join collapses, it can identify the exact clause.
- If a selected answer is semantically wrong, it can reject the result.
- If the observed bridge evidence is clear, it can synthesize a candidate route from graph observations.

This makes the harness better suited for evaluating whether an LLM can be guided by ontology and instance-level graph structure.
