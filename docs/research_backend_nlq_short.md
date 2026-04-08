# Short Research Note: MLLO-Web Backend and NLQ

## Overview

MLLO-Web is a semantic-query backend built on top of an RDF/OWL knowledge graph stored in GraphDB. In the setup described here, GraphDB contains the core ontology file `MLLO.rdf`, imported supporting ontologies such as BFO and IOF Core, and instance data loaded from `data.ttl`. Its purpose is not general chatbot interaction, but ontology-grounded querying over ML lifecycle data modeled with MLLO. The backend combines symbolic components such as SPARQL, GraphDB reasoning, and ontology-aware query templates with LLM-based components such as intent classification, SPARQL generation, SPARQL repair, and answer summarization.

## Backend architecture

The backend has four main parts:

1. A FastAPI service layer that exposes REST endpoints for datasets, models, pipelines, and natural-language query (NLQ).
2. A GraphDB semantic storage layer that holds both ontology schema and instance data.
3. An LLM orchestration layer that classifies questions, generates or repairs SPARQL, and summarizes query results.
4. An MCP server that exposes ontology and graph tools for external agent use.

The architecture is hybrid rather than purely neural. Deterministic SPARQL templates are used whenever possible, and the LLM is used only where natural-language interpretation or flexible query synthesis is needed.

## NLQ architecture

The NLQ pipeline is multi-stage:

1. The question is classified into an intent such as dataset lookup, model lookup, pipeline comparison, category exploration, or custom SPARQL.
2. The backend decides whether GraphDB inference should be enabled.
3. If the question matches a known pattern, a deterministic SPARQL query builder is used.
4. If the question is more open-ended, the system loads ontology context from GraphDB and asks the LLM to generate SPARQL.
5. The generated SPARQL is validated against known ontology terms.
6. If validation or execution fails, the system performs a repair pass.
7. The final results are summarized in natural language.

This design was chosen because it is more reliable than direct end-to-end question answering. It separates interpretation, symbolic execution, and verbalization.

## NLQ tools, prompts, and loops

Every NLQ request starts with an LLM intent-selection prompt. That prompt asks the model to choose one tool, produce JSON parameters, decide whether inference should be enabled, and give brief reasoning. The selectable tools are:

- `find_datasets`
- `find_models`
- `find_pipelines`
- `analyze_deployed_models`
- `compare_pipelines`
- `get_artifact_details`
- `explore_category`
- `custom_sparql`

If the classifier fails, the backend falls back to rule-based keyword routing.

### Literal prompt text used by the backend

#### Intent-selection system prompt (`INTENT_SYSTEM_PROMPT`)

```text
You classify ML lifecycle questions for the MLLE ontology explorer.

Available tools:
- find_datasets: dataset lookup by name, role, timeframe, or related model
- find_models: model lookup by dataset, model type, or search term
- find_pipelines: pipeline lookup by name, pipeline type, associated model, or dataset
- analyze_deployed_models: deployed model inventory and runtime analysis
- compare_pipelines: explicit comparison between multiple named pipelines
- get_artifact_details: direct IRI lookup or questions about a specific full IRI
- explore_category: conceptual or hierarchical exploration of a class/category/type
- custom_sparql: fallback for anything too custom for the structured tools

Set use_inference=true for conceptual or hierarchical questions, especially when the question includes:
"type of", "kind of", "category", "all supervised", "is it a", "related to", "what are", "classify"

Set use_inference=false for exact lookup questions, especially when the question includes:
specific names, dates, owners, counts, "show me X", "find X named Y"

Use custom_sparql with use_inference=false for ranking, aggregation, or metric-based questions, especially when the question includes:
"best", "top", "highest", "lowest", "maximum", "minimum", "max", "min", "most accurate", "least accurate", "performance", "accuracy", "score", "metric"

Do not use explore_category for ranking, performance, or superlative questions.

Return JSON only with:
{
  "tool": "...",
  "params": {},
  "use_inference": true|false,
  "reasoning": "brief explanation"
}
```

#### SPARQL-generation system prompt (`SYSTEM_MESSAGE`)

```text
You are an expert Semantic Web engineer specialising in the MLLO (Machine Learning Lifecycle Ontology).
Generate ONLY valid SPARQL that strictly follows the provided ontology schema and example queries.

ENTITY DEFINITIONS in MLLO:
- DATASET: an entity used as input to an ML process via ml:hasDataInput.
- MODEL: a MachineLearningModel linked from an ML process via ml:executes | bfo:BFO_0000057.
- PIPELINE: a DataProcessingPipeline or MachineLearningModelDevelopmentPipeline with components via bfo:BFO_0000117.
- ML PROCESS: the central node linking models, datasets, inputs, and outputs.

KEY PATTERNS:
- ML processes link to models via: ml:executes | bfo:BFO_0000057
- ML processes link to datasets via: ml:hasDataInput / ml:hasDataOutput
- Individuals are linked to classes via: ?individual rdf:type ?class
- Include subclass hierarchy with rdf:type/rdfs:subClassOf* or rdfs:subClassOf*
- Use property paths as shown in the examples

IMPORTANT RULES:
- Do not invent classes, properties, or IRIs.
- Use only the listed prefixes and vocabulary.
- Always include LIMIT 100 unless the user explicitly asks for all results.
- Prefer OPTIONAL blocks for fields that may not exist.
- If the question cannot be answered with the ontology, return exactly: CANNOT_ANSWER_WITH_ONTOLOGY
- Return ONLY the SPARQL query, with no markdown fences.
```

#### Repair prompt (`REPAIR_MESSAGE`)

```text
The previous SPARQL was invalid for this ontology or could not be parsed. Fix it strictly using the provided ontology vocabulary and return ONLY corrected SPARQL.
```

#### Answer-summarization system prompt

```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets or pipelines, use them directly and do not replace them with generic guesses.
```

### `find_datasets`

Uses a deterministic SPARQL template for dataset-centered lifecycle lookup. It does not use LLM SPARQL generation. Inference is usually off unless the question is conceptual.
System prompts used:

- routing: `INTENT_SYSTEM_PROMPT`
- summarization: answer-summarization system prompt

### `find_models`

Uses a deterministic SPARQL template for dataset-to-model lookup, including dataset roles, characteristics, timestamps, and performance values. No SPARQL generation loop is used.
System prompts used:

- routing: `INTENT_SYSTEM_PROMPT`
- summarization: answer-summarization system prompt

### `find_pipelines`

Uses a deterministic SPARQL template for pipeline retrieval, pipeline components, and associated models or datasets. No SPARQL repair loop is needed because the query is template-built.
System prompts used:

- routing: `INTENT_SYSTEM_PROMPT`
- summarization: answer-summarization system prompt

### `analyze_deployed_models`

Uses a deterministic query over deployment state, execution, training time, IOF Core engineered systems, and optional performance metrics. This path depends on both MLLO and imported ontologies such as BFO and IOF Core.
System prompts used:

- routing: `INTENT_SYSTEM_PROMPT`
- summarization: answer-summarization system prompt

### `compare_pipelines`

Uses a deterministic comparison query for explicitly named pipelines. It is exact and normally runs without inference.
System prompts used:

- routing: `INTENT_SYSTEM_PROMPT`
- summarization: answer-summarization system prompt

### `get_artifact_details`

Uses a deterministic IRI-based query that fetches datatype properties, annotation properties, and type labels for one entity.
System prompts used:

- routing: `INTENT_SYSTEM_PROMPT`
- summarization: answer-summarization system prompt

### `explore_category`

Uses a deterministic class/instance exploration query and usually enables inference, because it is intended for conceptual or hierarchical questions.
System prompts used:

- routing: `INTENT_SYSTEM_PROMPT`
- summarization: answer-summarization system prompt

### Performance-analysis path

Questions about best model, top accuracy, threshold performance, and similar patterns are intercepted by handcrafted logic before normal tool execution. The backend builds deterministic ranking/filter queries and may run follow-up queries to attach test-dataset or pipeline context.
System prompts used:

- routing: `INTENT_SYSTEM_PROMPT`
- summarization: answer-summarization system prompt

### `custom_sparql`

This is the main LLM query-synthesis path. It uses:

- an intent-selection prompt;
- a SPARQL-generation prompt that includes ontology context and MLLO-specific example queries;
- a repair prompt if validation fails;
- a second repair prompt if GraphDB execution fails;
- a final answer-summarization prompt.

System prompts used:

- routing: `INTENT_SYSTEM_PROMPT`
- SPARQL generation: `SYSTEM_MESSAGE`
- repair: `REPAIR_MESSAGE`
- summarization: answer-summarization system prompt

So `custom_sparql` includes two possible loops:

1. validation-repair loop
2. execution-repair loop

## What techniques are used, and why

The main techniques are:

- intent classification, to route simple questions to reliable structured queries;
- handcrafted SPARQL templates, to improve precision for common analytical tasks;
- ontology-context injection, to ground the LLM in the actual schema of the selected repository;
- few-shot prompting with MLLO-specific SPARQL examples, to teach the model valid query patterns;
- lexical ontology subgraph selection, to reduce prompt size while keeping relevant classes and properties;
- post-generation validation and repair, to reduce invented ontology terms and malformed queries;
- optional GraphDB inference, to support conceptual and hierarchical questions.

These techniques are used to improve faithfulness to the ontology and reduce hallucination.

## How LLM and MCP flow interact

In the current implementation, the FastAPI NLQ route does not internally call MCP. The two flows are parallel:

- web NLQ flow: frontend -> FastAPI -> LLM gateway + GraphDB
- MCP flow: external agent -> MCP server -> GraphDB-backed tools

Therefore, MCP is not the internal planner for the current NLQ backend. Instead, MCP provides an alternative agent-facing interface that exposes deterministic tools such as node lookup, class hierarchy exploration, graph traversal, and direct SPARQL execution.

Conceptually, MCP is important because it supports tool-mediated semantic reasoning. An external LLM using MCP can inspect the ontology step by step instead of generating the entire query in one shot.

## Is it zero-shot?

The text-to-SPARQL part is not zero-shot. It is better described as ontology-grounded few-shot constrained generation.

It is ontology-grounded because the current repository schema is retrieved from GraphDB and inserted into the prompt. It is few-shot because the prompt includes several MLLO-specific SPARQL examples. It is constrained because the prompt forbids invented vocabulary and the backend validates generated terms against the ontology context.

The intent-classification step is closer to instruction-based zero-shot classification, but the main query-generation stage is not zero-shot.

## How hallucination is reduced

The system reduces hallucination through a stack of safeguards:

- deterministic query builders for common tasks;
- repository-specific ontology grounding at runtime;
- MLLO-specific example queries in the prompt;
- temperature-zero generation for OpenAI-compatible models;
- validation of prefixes and ontology terms;
- repair prompts when invalid or failing SPARQL is produced;
- explicit rejection when the ontology cannot answer the question.

This does not provide formal guarantees, but it is substantially more constrained than a generic LLM chatbot.

## How the LLM uses the ontology strictly

The LLM uses the ontology through runtime prompt grounding and output validation. The backend fetches classes, properties, prefixes, and named individuals from GraphDB, then includes them in the prompt. After generation, the backend checks whether the SPARQL uses known ontology terms.

This means the model is constrained by:

- the vocabulary shown in the prompt,
- the example query patterns,
- the validator that rejects unknown terms,
- the repair loop if a generated query is invalid.

Strictness is therefore practical rather than formal. The system strongly restricts ontology vocabulary use, but it does not yet use grammar-constrained decoding or full semantic proof checking.

## How the LLM knows relationships in MLLO

The LLM is not expected to know MLLO purely from pretraining. It learns MLLO structure at runtime from:

- class and superclass information;
- object properties with domain and range;
- named individuals from the current repository;
- example SPARQL queries showing how MLLO relations are traversed in practice.

This is especially important for recurring MLLO patterns such as:

- process to model links through `ml:executes` or `bfo:BFO_0000057`;
- process to dataset links through `ml:hasDataInput` and `ml:hasDataOutput`;
- performance assessment chains;
- pipeline composition relations.

So the model’s operational knowledge of MLLO comes mainly from prompt grounding plus examples, not from memorized prior knowledge.

## If new datasets are loaded and mapped to MLLO, will the system answer well?

In general, yes, if the data are mapped correctly into MLLO-compatible RDF patterns.

The reason is that the backend queries by ontology structure, not by memorized dataset names. If newly loaded data in `data.ttl` use the same semantic relations expected by the query builders and the generated SPARQL, then the same queries will retrieve them. In practice, those instance triples must align with classes and relations from `MLLO.rdf` and, where needed, the imported BFO and IOF Core terms.

Answer quality will usually be good when:

- datasets, models, processes, metrics, and pipelines are linked with the expected MLLO relations;
- imported ontology terms from BFO and IOF Core are present where the query patterns rely on them;
- type assertions and subclass structure are present;
- labels are meaningful;
- performance values are represented using the same modeling pattern as the existing repository.

Answer quality will degrade when:

- the mapping is incomplete or inconsistent;
- key relations are missing;
- labels are poor;
- the data use nonstandard modeling choices that differ from the patterns assumed by the backend.

So the main dependency is not only the LLM. It is the quality of the ontology mapping and the consistency of the RDF graph.

## Suggested figures

### Figure 1: Overall system architecture

Draw five blocks:

1. Frontend/User
2. FastAPI backend
3. LLM gateway
4. GraphDB repository
5. MCP server

Show that the web NLQ path goes from FastAPI to LLM and GraphDB, while the MCP server is a parallel agent-facing layer rather than an internal step of the current NLQ pipeline.

### Figure 2: NLQ pipeline

Draw a sequential flow:

1. Question input
2. Intent classification
3. Structured query path or custom SPARQL path
4. Ontology context loading
5. SPARQL generation
6. Validation and repair
7. GraphDB execution
8. Answer summarization

This figure should emphasize that the architecture is staged and hybrid.

### Figure 3: Hallucination-control strategy

Draw the LLM in the center and place around it:

- ontology context,
- example queries,
- deterministic routing,
- SPARQL validation,
- repair loop,
- GraphDB execution grounding.

The point of the figure is to show that hallucination control is achieved by multiple interacting safeguards, not by prompt wording alone.

## Short paper-style summary

MLLO-Web implements a hybrid ontology-grounded NLQ backend for ML lifecycle knowledge graphs. It combines deterministic SPARQL templates, GraphDB reasoning, and runtime ontology retrieval with LLM-based intent classification, constrained SPARQL generation, repair, and answer summarization. The system is not zero-shot text-to-SPARQL; it is an ontology-grounded few-shot pipeline designed to reduce hallucination and improve semantic fidelity when querying MLLO-aligned data.
