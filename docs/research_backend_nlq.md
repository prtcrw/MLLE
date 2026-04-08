# MLLO-Web Backend and NLQ Architecture for Research Documentation

## 1. Scope and Positioning

This document describes the backend architecture of MLLO-Web with emphasis on the natural-language-query (NLQ) subsystem, the ontology-grounding strategy, and the relationship between the LLM-facing API path and the MCP tool server. The intended audience is a research-paper author, not an end user.

The backend is not a generic chatbot over arbitrary documents. It is a semantic-query system built around an RDF/OWL knowledge graph, queried through SPARQL, with the Machine Learning Lifecycle Ontology (MLLO) as the central schema. In the deployed GraphDB setting described here, the repository contains the core MLLO ontology (`MLLO.rdf`), supporting upper/foundation ontologies such as BFO and IOF Core, and instance data loaded from `data.ttl`. Its main function is to translate natural-language questions into ontology-grounded graph queries, execute those queries against GraphDB, and summarize the results.

At a high level, the system combines four layers:

1. A FastAPI application that exposes REST endpoints for structured lookup and NLQ.
2. A GraphDB-backed semantic data layer that stores MLLO-aligned ontology and instance data.
3. An LLM orchestration layer that performs intent classification, SPARQL generation, repair, and answer synthesis.
4. A separate MCP server that exposes ontology- and graph-oriented tools to external agents.

An important architectural clarification is that the current NLQ path does not internally invoke the MCP server. The web API and the MCP server are two parallel access layers over the same ontology/query functionality. The FastAPI NLQ route talks directly to the GraphDB client and the LLM gateway; the MCP server exposes many of the same capabilities as agent tools for external use.

## 2. Backend Architecture

### 2.1 Service decomposition

The backend is organized into the following functional modules:

- `mllo_web/app/api_app.py`: FastAPI application bootstrap, router registration, SPARQL backend selection, and static UI mounting.
- `mllo_web/app/api/routers/*.py`: REST endpoints for datasets, models, pipelines, SPARQL conversion, settings, and NLQ.
- `mllo_web/app/api/services/graphdb_client.py`: asynchronous GraphDB access, repository validation, ontology-schema retrieval, and result normalization.
- `mllo_web/app/api/services/llm_gateway.py`: provider-agnostic chat-completions gateway supporting OpenAI-compatible APIs, Anthropic, Gemini, and LM Studio.
- `mllo_web/app/api/services/intent_classifier.py`: LLM-based intent routing plus rule-based fallback.
- `mllo_web/app/api/services/query_state.py`: execution trace structure for multi-step NLQ runs.
- `mllo_web/app/tools/*.py` and `mllo_mcp_server.py`: MCP tool layer and graph-native tools.

The GraphDB repository is the authoritative data source for both ontology schema and instance-level ML lifecycle data. In practice, this means the same repository contains:

- the domain ontology layer from `MLLO.rdf`,
- imported supporting ontologies such as BFO and IOF Core,
- the instance/data layer from `data.ttl`.

The backend therefore uses the same RDF store both as:

- schema source, to constrain LLM query generation, and
- answer source, to execute the final SPARQL against actual mapped data.

### 2.2 Query surfaces

The system exposes two distinct query surfaces:

#### Structured REST routes

These include deterministic routes such as:

- dataset search,
- model search,
- pipeline search,
- deployed-model analysis,
- artifact detail lookup.

These routes rely on handcrafted SPARQL query builders. For common analytical tasks, this path is more reliable than free-form text-to-SPARQL generation because it uses predefined query templates.

#### Natural-language route

The NLQ route (`/api/v1/nlq/query`) accepts a user question and returns:

- the inferred intent,
- the SPARQL executed,
- the raw results,
- a natural-language answer,
- the repository used,
- whether GraphDB inference was enabled.

This route is a hybrid architecture. It does not always translate the question directly into SPARQL. Instead, it first decides whether the question can be handled by a structured query builder. Only if the question is too custom does it fall back to LLM-generated SPARQL.

This hybrid design is central to the backend’s hallucination-mitigation strategy.

## 3. NLQ Processing Pipeline

### 3.1 End-to-end control flow

The NLQ execution path proceeds as follows:

1. Validate the target GraphDB repository.
2. Classify the question into a tool/intention category.
3. Decide whether inference should be enabled.
4. Execute one of three paths:
   - deterministic structured query,
   - deterministic performance-query pipeline,
   - ontology-constrained LLM SPARQL generation.
5. Run the SPARQL against GraphDB.
6. Summarize the returned bindings with the LLM.

This means the system is not a single-step "prompt in, answer out" architecture. It is a staged orchestration pipeline with explicit intermediate representations:

- `QueryIntent`,
- SPARQL string,
- GraphDB result bindings,
- `NLQQueryState` execution trace,
- final answer summary.

### 3.2 Intent classification

The first LLM task is not SPARQL generation. It is intent classification. The classifier selects among:

- `find_datasets`
- `find_models`
- `find_pipelines`
- `analyze_deployed_models`
- `compare_pipelines`
- `get_artifact_details`
- `explore_category`
- `custom_sparql`

It also predicts:

- `params`: structured parameters for the chosen tool
- `use_inference`: whether GraphDB reasoning should be enabled
- `reasoning`: a short explanation

This is a routing model, not an answer-generation model. It narrows the problem before any free-form query synthesis occurs.

If the classifier fails, the backend falls back to deterministic keyword heuristics. This fallback prevents total pipeline failure and is also a reliability feature.

### 3.3 Deterministic path for frequent analytical questions

A notable design choice is that performance-oriented questions are intercepted by handcrafted logic rather than delegated to free-form SPARQL synthesis. Questions containing terms such as "best", "top", "highest", "accuracy", "score", or threshold expressions such as "more than 0.9" are converted into a deterministic performance query specification.

The backend then builds SPARQL from fixed templates and, if needed, follows with secondary queries to attach:

- test datasets for the selected models,
- pipelines associated with those models.

This is effectively a small query-planning layer. It improves accuracy because the system does not ask the LLM to synthesize ranking logic, threshold logic, or multi-step joins in those common cases.

### 3.4 Structured tool execution

If the intent is one of the known structured operations, the backend instantiates a specific query builder and executes the resulting SPARQL directly. In this case, the LLM is used only for:

- intent classification, and
- final answer summarization.

For these questions, ontology adherence is largely guaranteed by the handcrafted query templates rather than by the LLM.

### 3.5 Free-form SPARQL generation

Only when the question falls outside the structured cases does the system invoke the LLM to generate SPARQL.

This generation stage is not unconstrained. Before prompting the model, the backend dynamically constructs an ontology context from the current GraphDB repository. The internal context object gathers:

- ontology classes,
- object properties with domain/range,
- datatype properties with domain/range,
- annotation properties,
- named individuals,
- prefixes,
- sample triples.

The prompt-facing serialization is stricter: it currently shows prefixes, classes, object properties, datatype properties, and named individuals. The context is then reduced using question-token overlap so that only a relevant ontology subgraph is shown to the model. This is a prompt-budget control mechanism and also a grounding mechanism.

### 3.6 Prompts used in the NLQ pipeline

The NLQ subsystem uses four prompt roles.

#### Intent-classification prompt

The classifier prompt defines the available tools, explains when inference should be enabled, and requires a JSON object with:

- `tool`
- `params`
- `use_inference`
- `reasoning`

It explicitly distinguishes:

- lookup-style questions,
- conceptual or hierarchical questions,
- ranking and metric questions, which should go to `custom_sparql`.

#### SPARQL-generation prompt

The SPARQL-generation system prompt defines the model as an MLLO-focused semantic-web engineer and imposes strict rules:

- generate only valid SPARQL,
- use only listed prefixes and vocabulary,
- do not invent classes, properties, or IRIs,
- use `LIMIT 100` unless the user asks otherwise,
- return `CANNOT_ANSWER_WITH_ONTOLOGY` if the ontology is insufficient.

The user-side prompt then provides:

- the original question,
- the reduced ontology context,
- several MLLO-specific SPARQL examples.

#### Repair prompt

When validation fails or GraphDB execution fails, the backend sends a repair prompt saying that the previous SPARQL was invalid and must be fixed strictly using the provided ontology vocabulary. The repair message is augmented with either:

- validation errors, or
- the GraphDB execution error text.

#### Answer-summarization prompt

After execution, the backend uses a separate summarization prompt instructing the model to summarize ontology query results concisely and factually, and to avoid inventing generic replacements for already joined result fields such as test datasets or pipelines.

## 4. Tool-by-Tool NLQ Execution

### 4.1 Start: intent selection

Every NLQ request starts with LLM intent selection. The classifier chooses one of the following tools:

- `find_datasets`
- `find_models`
- `find_pipelines`
- `analyze_deployed_models`
- `compare_pipelines`
- `get_artifact_details`
- `explore_category`
- `custom_sparql`

If the classifier output is invalid, the backend falls back to rule-based intent assignment using question keywords. After intent selection, the backend either follows a deterministic query-builder path or the ontology-constrained `custom_sparql` path.

### 4.2 `find_datasets`

Purpose:

- retrieve datasets linked to ML processes, associated models, objectives, timestamps, outputs, and output utilization.

How it works:

- uses `FindDatasetsQueryBuilder`;
- emits a deterministic SPARQL template;
- can filter by dataset role and model type;
- uses process-centered MLLO patterns such as `ml:hasDataInput` and model links through `ml:executes | bfo:BFO_0000057`.

Query structure:

- starts from an ML process node;
- links the process to a model through `ml:executes | bfo:BFO_0000057`;
- links the same process to an input dataset through `ml:hasDataInput`;
- optionally retrieves timestamps through BFO/IOF Core time-value chains;
- optionally retrieves downstream model outputs and the utilization process that consumes those outputs;
- optionally retrieves performance-assessment information through graph paths from the ML process output.

Expected output:

- one row per matched dataset usage context;
- typically includes model IRI, model type label, model objective label, dataset IRI, optional input timestamp, optional model output, and optional downstream utilization label;
- intended to answer questions such as which datasets were used, by which models, for what role, and with what downstream outputs.

Parameters typically inferred by the intent stage:

- dataset search term,
- dataset role filters such as training, test, validation, production, raw,
- model type filters.

Why this tool exists:

- many user questions about datasets are structurally repetitive;
- deterministic SPARQL is safer than free-form generation for this lifecycle pattern.

Prompt use:

- system prompt used for routing: `INTENT_SYSTEM_PROMPT`
- no tool-specific SPARQL-generation system prompt is used here;
- result verbalization uses the answer-summarization system prompt.

System-prompt role in this tool:

- the LLM only decides that the question belongs to `find_datasets`;
- the actual SPARQL is produced entirely by the deterministic query builder.

Looping and repair:

- no generation loop;
- no SPARQL repair loop, because the query is template-generated.

Failure behavior:

- failures mainly come from repository access or data incompleteness rather than LLM generation;
- if no results are returned, the summarizer simply reports that no matching results were found.

Inference:

- controlled by the intent-selection stage or answer mode;
- usually exact lookup, so often `use_inference=false`, unless the classifier marks it conceptual.

### 4.3 `find_models`

Purpose:

- retrieve models associated with datasets, dataset roles, timestamps, characteristics, and performance metrics.

How it works:

- uses `FindModelsQueryBuilder`;
- builds deterministic SPARQL centered on `?ml_process ml:hasDataInput/ml:informationContentEntityDerivedFrom* ?dataset` and model associations;
- can filter by dataset role and model type;
- aggregates dataset characteristic information.

Query structure:

- begins with datasets and the ML processes that consume them;
- follows process-to-model links to retrieve associated models;
- extracts dataset role/type labels;
- optionally retrieves timestamps for the input event;
- retrieves model performance assessments when they exist;
- builds a combined string of dataset characteristics and datatype-property values.

Expected output:

- one row per dataset-model association;
- typically includes dataset IRI, dataset role/type label, usage purpose, dataset characteristics, optional timestamp, model IRI, optional performance metric label, and optional performance value;
- intended to answer which models are associated with a dataset and what properties or performance evidence are attached to that pairing.

Parameters typically inferred by the intent stage:

- dataset name or search term,
- dataset-role filters,
- model types.

Why this tool exists:

- model lookup from datasets is a frequent and structurally stable question type;
- deterministic query construction preserves the intended joins between datasets, processes, and model performance.

Prompt use:

- system prompt used for routing: `INTENT_SYSTEM_PROMPT`
- no tool-specific SPARQL-generation system prompt is used here;
- result verbalization uses the answer-summarization system prompt.

System-prompt role in this tool:

- the LLM selects `find_models` and may populate parameters;
- the query itself is deterministic.

Looping and repair:

- no LLM query-generation loop for the SPARQL itself.

Failure behavior:

- failures are usually due to repository unavailability or missing mappings in `data.ttl`;
- no repair pass is needed because the SPARQL itself is not LLM-generated.

Inference:

- configurable through routing;
- typically off for exact dataset-model lookup.

### 4.4 `find_pipelines`

Purpose:

- retrieve pipelines, their types, components, data inputs/outputs, and associated models.

How it works:

- uses `FindPipelinesQueryBuilder`;
- performs deterministic SPARQL over pipeline composition relations such as `bfo:BFO_0000117` and downstream model links;
- can operate in model-centered mode or dataset-centered mode depending on the toggle constraint;
- groups pipeline components using `GROUP_CONCAT`.

Query structure:

- first identifies candidate pipelines and their pipeline types;
- traverses pipeline component relations through `bfo:BFO_0000117`;
- constrains the pipeline either by linked models or by linked datasets;
- optionally retrieves pipeline data inputs and outputs;
- optionally follows composition paths to models associated with the pipeline.

Expected output:

- one row per pipeline;
- typically includes pipeline local name, pipeline type label, concatenated component labels, optional pipeline data input, optional pipeline data output, and optional associated model;
- intended to summarize pipeline structure and its relation to datasets or models.

Parameters typically inferred by the intent stage:

- pipeline search term,
- pipeline type,
- whether the query is model-constrained or dataset-constrained.

Why this tool exists:

- pipeline questions often need composition logic and repeated ontology paths;
- deterministic templates reduce the risk of omitting key joins in pipeline structure.

Prompt use:

- system prompt used for routing: `INTENT_SYSTEM_PROMPT`
- no tool-specific SPARQL-generation system prompt is used here;
- result verbalization uses the answer-summarization system prompt.

System-prompt role in this tool:

- the LLM only routes the question to `find_pipelines`;
- query construction is template-based.

Looping and repair:

- no SPARQL synthesis loop.

Failure behavior:

- the most common issue is sparse or inconsistent pipeline composition data;
- there is no LLM repair cycle because the SPARQL is predefined.

Inference:

- usually off for direct retrieval, unless routed as a conceptual query.

### 4.5 `analyze_deployed_models`

Purpose:

- retrieve deployed-model state, deployment target system, latest training timestamp, execution time, inputs, outputs, output utilization, and optional performance metrics.

How it works:

- uses `DeployedModelsQueryBuilder`;
- runs a deterministic query over deployment state, model execution, model training, engineered systems, and performance-assessment relations;
- depends on both MLLO terms and imported ontology terms, especially from IOF Core and BFO.

Query structure:

- starts from a deployed state entity;
- links that state to both a model and an engineered system;
- identifies model executions attached to that deployed state;
- connects executions back to the relevant training activity;
- retrieves execution timestamps and latest training timestamps via IOF Core time expressions;
- optionally attaches performance metrics and utilization of model outputs.

Expected output:

- one row per deployed-model execution context;
- typically includes model IRI, deployed system IRI, latest model update timestamp, model execution timestamp, model input, model output, optional output-utilization node, optional performance metric, and optional performance value;
- intended to describe runtime deployment status together with training recency and execution evidence.

Parameters typically inferred by the intent stage:

- mostly none, because deployed-model analysis is usually a global inventory query;
- optional search term if the question narrows the scope.

Why this tool exists:

- deployment/runtime questions require a specific composite query involving execution, training, and deployment state;
- this logic is easier to encode deterministically than to trust to generated SPARQL.

Prompt use:

- system prompt used for routing: `INTENT_SYSTEM_PROMPT`
- no tool-specific SPARQL-generation system prompt is used here;
- result verbalization uses the answer-summarization system prompt.

System-prompt role in this tool:

- the LLM identifies the deployed-model analysis intent;
- the actual backend query remains deterministic.

Looping and repair:

- no LLM SPARQL generation loop.

Failure behavior:

- failures usually indicate missing deployment-state modeling or absent IOF/BFO time structures in the repository;
- these are data-model issues rather than language-model issues.

Inference:

- generally exact, so usually off unless explicitly forced into conceptual mode.

### 4.6 `compare_pipelines`

Purpose:

- compare explicitly named pipelines side by side.

How it works:

- uses a deterministic helper `_build_compare_pipelines_query`;
- extracts pipeline names from parameters;
- performs a two-stage SPARQL structure with grouped components and optional linked inputs, outputs, and associated models.

Query structure:

- takes a set of explicit pipeline identifiers;
- filters pipelines by local name;
- groups component labels for each pipeline;
- optionally attaches data inputs, outputs, and associated models for side-by-side comparison.

Expected output:

- one row per selected pipeline;
- typically includes pipeline name, pipeline type, grouped component list, optional inputs, optional outputs, and optional associated models;
- intended to support direct comparison of two or more named pipelines.

Parameters typically inferred by the intent stage:

- pipeline names or identifiers parsed from the question text.

Why this tool exists:

- comparison questions are explicit and structurally stable;
- deterministic SPARQL avoids ambiguity about which entities are being compared.

Prompt use:

- system prompt used for routing: `INTENT_SYSTEM_PROMPT`
- no tool-specific SPARQL-generation system prompt is used here;
- result verbalization uses the answer-summarization system prompt.

System-prompt role in this tool:

- the LLM decides that the question is an explicit comparison request;
- the comparison SPARQL is deterministic once pipeline identifiers are extracted.

Looping and repair:

- no SPARQL synthesis loop.

Failure behavior:

- if pipeline names are not extracted cleanly, the query may return no rows;
- there is no SPARQL repair path because the query is not LLM-generated.

Inference:

- typically off, because comparison is identity-based and exact.

### 4.7 `get_artifact_details`

Purpose:

- retrieve details for a single specified IRI.

How it works:

- uses `IriQueryBuilder`;
- binds the target entity through `VALUES ?entity { <IRI> }`;
- collects datatype-property/value pairs, annotation-property/value pairs, and labels for the entity’s types.

Query structure:

- exact binding of one IRI;
- retrieval of RDF type labels;
- retrieval of datatype properties and annotation properties only, rather than arbitrary outgoing graph neighborhoods.

Expected output:

- usually a compact record for a single entity;
- includes concatenated datatype-property/value pairs, annotation-property/value pairs, and type labels;
- intended to provide a direct attribute-level description of one artifact rather than a full neighborhood subgraph.

Parameters typically inferred by the intent stage:

- the full artifact IRI.

Why this tool exists:

- direct IRI inspection is common when the user already knows the entity identity;
- an exact lookup path is more appropriate than open-ended graph exploration.

Prompt use:

- system prompt used for routing: `INTENT_SYSTEM_PROMPT`
- no tool-specific SPARQL-generation system prompt is used here;
- result verbalization uses the answer-summarization system prompt.

System-prompt role in this tool:

- the LLM detects that the query is about a specific IRI or artifact;
- the IRI lookup SPARQL is deterministic.

Looping and repair:

- no LLM SPARQL synthesis loop.

Failure behavior:

- empty results usually mean the IRI is absent from the repository or modeled differently than expected;
- there is no repair loop because the SPARQL is fixed.

Inference:

- usually off, because the target is a specific node.

### 4.8 `explore_category`

Purpose:

- explore classes and instances related to a conceptual category.

How it works:

- uses a deterministic helper `_build_explore_category_query`;
- resolves broad terms such as model, dataset, pipeline, or metric to canonical MLLO class targets;
- queries both subclasses and instances under that category.

Query structure:

- maps a natural-language category term to a target class IRI;
- retrieves subclasses under that target;
- retrieves instances typed under that target or its subclasses;
- uses a union so that both schema-level and instance-level exploration are returned together.

Expected output:

- a mixed set of rows covering both subclasses and instances under the target category;
- typically includes entity IRI, whether it is being returned as a class or instance, and optional labels/type labels;
- intended to answer conceptual questions such as what subclasses or members exist under a category.

Parameters typically inferred by the intent stage:

- category name or conceptual class target.

Why this tool exists:

- conceptual questions such as "what kinds of models exist?" are common;
- such questions are better handled by class-hierarchy exploration than by free-form SPARQL synthesis.

Prompt use:

- system prompt used for routing: `INTENT_SYSTEM_PROMPT`
- no tool-specific SPARQL-generation system prompt is used here;
- result verbalization uses the answer-summarization system prompt.

System-prompt role in this tool:

- the LLM classifies the question as conceptual/category exploration;
- the category-expansion query is deterministic.

Looping and repair:

- no SPARQL synthesis loop.

Failure behavior:

- ambiguity in category naming may lead to overly broad or overly narrow matches;
- because class resolution is rule-based, the main limitation is semantic coverage rather than prompt instability.

Inference:

- always conceptually oriented;
- typically uses `use_inference=true`, because hierarchy exploration benefits from reasoning.

### 4.9 Deterministic performance-analysis path

Although not exposed as a separate intent label, performance questions are intercepted before ordinary tool execution if the question contains ranking or threshold language such as:

- best,
- top,
- highest,
- lowest,
- performance,
- accuracy,
- score,
- more than 0.9.

How it works:

- the backend derives a structured performance specification;
- builds a deterministic performance SPARQL query;
- executes it with `use_inference=true`;
- if the question asks for test-dataset context, it runs a second deterministic query joining matched models to test datasets;
- if the question asks for pipeline context, it runs a second deterministic query joining matched models to pipelines.

Query structure:

- identifies models participating in ML processes;
- follows process output to performance-assessment nodes;
- extracts metric labels and numeric values;
- applies threshold filters or ranking order;
- optionally enriches the best or matched models with test-dataset context;
- optionally enriches the same models with pipeline context.

Expected output:

- for the base performance query, one row per matched model-performance observation;
- typically includes model IRI, performance metric label, and performance value;
- for enriched variants, rows may also include test datasets or related pipelines;
- intended to answer best-model, threshold, and ranking questions with optional contextual joins.

Why this path exists:

- ranking and metric questions are especially error-prone for generic text-to-SPARQL generation;
- the deterministic planner handles superlatives, thresholds, and follow-up joins more reliably.

Looping and repair:

- no LLM SPARQL generation is needed for the main performance query;
- this is a handcrafted multi-step query plan rather than a prompt-driven loop.

System prompts used:

- routing still begins with `INTENT_SYSTEM_PROMPT`;
- no dedicated SPARQL-generation system prompt is used for the deterministic performance queries;
- result verbalization uses the answer-summarization system prompt.

### 4.10 `custom_sparql`

Purpose:

- answer questions too custom for the structured query builders.

How it works:

1. Load ontology context from GraphDB.
2. Reduce the ontology context to a relevant lexical subgraph.
3. Prompt the LLM with the MLLO system prompt, ontology context, and example SPARQL queries.
4. Extract the SPARQL from the model output.
5. Validate prefixes and ontology terms.
6. If validation fails, run the repair loop.
7. Execute the SPARQL in GraphDB.
8. If execution fails, run an execution-error repair loop.
9. Summarize the final results.

Query structure:

- not fixed in advance;
- synthesized from ontology context plus example patterns;
- constrained to the current repository vocabulary and validated before execution.

Expected output:

- depends on the generated SPARQL, but always returns a structured SPARQL result table from GraphDB;
- after summarization, the backend presents a concise natural-language answer plus the raw result bindings;
- intended to cover question types not already captured by the deterministic tools.

Parameters typically inferred by the intent stage:

- usually just the original question, passed through as `params["question"]`.

Why this tool exists:

- some questions are too specific, compositional, or analytically unusual for the fixed tool set;
- this path provides coverage beyond the deterministic templates.

Prompt use:

- routing system prompt: `INTENT_SYSTEM_PROMPT`
- SPARQL-generation system prompt: `SYSTEM_MESSAGE`
- repair instruction prompt: `REPAIR_MESSAGE` combined with validation errors or GraphDB execution errors
- result verbalization system prompt: answer-summarization prompt

System-prompt role in this tool:

- `INTENT_SYSTEM_PROMPT` decides that the request is too custom for deterministic tools;
- `SYSTEM_MESSAGE` constrains the model to MLLO-grounded SPARQL only;
- `REPAIR_MESSAGE` drives correction loops when the first query is invalid or non-executable;
- the answer-summarization prompt verbalizes the executed results rather than generating the answer from scratch.

Looping and repair:

- first loop: validation-repair loop based on ontology-term errors;
- second loop: execution-repair loop based on GraphDB runtime errors.

Inference:

- determined by intent routing or answer mode;
- ranking/metric questions routed here by the classifier usually set `use_inference=false`, but some conceptual custom questions may run with inference enabled.

Failure behavior:

- residual failure can still occur if the ontology context omitted relevant terms, if the question requires semantics not present in the graph, or if the repaired SPARQL remains incompatible with the repository contents;
- in that case the backend returns an error rather than silently fabricating an answer.
## 5. Ontology Grounding Strategy

### 4.1 How the LLM knows the MLLO vocabulary

The model is not expected to know MLLO from pretraining alone. Instead, the backend retrieves ontology metadata live from GraphDB and inserts it into the prompt. The prompt therefore contains a local schema representation generated from the repository currently being queried.

The model is explicitly given:

- compact prefix declarations,
- MLLO classes,
- object properties with domains and ranges,
- datatype properties with domains and ranges,
- named individuals,
- example query patterns.

Although the backend also retrieves annotation properties and sample triples from GraphDB, those are not currently serialized into the main LLM prompt text.

This means the model’s operational knowledge of MLLO is primarily runtime grounding, not background memory.

### 4.2 How the LLM knows relationships in MLLO

The model learns relationship structure from three sources provided at runtime:

#### Schema-level relationships

Object properties are listed with domain and range. This tells the model which class-to-class relations are legal or expected.

#### Taxonomic relationships

Classes are given together with superclass information. In addition, the prompt explicitly instructs the model to use subclass paths such as `rdf:type/rdfs:subClassOf*`.

#### Demonstration patterns

The prompt includes multiple MLLO-specific SPARQL exemplars showing how the ontology is actually traversed in this application, for example:

- linking ML processes to models via `ml:executes | bfo:BFO_0000057`,
- linking processes to datasets via `ml:hasDataInput` and `ml:hasDataOutput`,
- traversing to performance assessments through graph paths,
- identifying pipelines by process-composition relations.

This is important. The LLM is not merely shown a schema; it is shown the canonical query idioms used by the system designers for MLLO.

### 4.3 Relevant-subgraph selection

The backend does not dump the entire ontology into the prompt unfiltered. It tokenizes the user question, scores ontology elements by lexical overlap with labels and IRI local names, and selects the most relevant classes, properties, and individuals. It then expands that selection slightly by including connected domains, ranges, and superclasses.

This is not graph embedding retrieval or vector search. It is lexical schema retrieval with relation-aware expansion.

The advantage is interpretability and simplicity. The limitation is that it depends on lexical overlap. If the question uses terminology very different from ontology labels, relevant concepts may be missed from the reduced prompt context.

## 6. Prompting Technique: Zero-shot or Not?

The SPARQL generation stage is not zero-shot.

It is better described as ontology-grounded few-shot constrained generation:

- ontology-grounded, because the current repository schema is injected into the prompt;
- few-shot, because multiple MLLO-specific SPARQL examples are included;
- constrained, because the prompt explicitly forbids invented terms and requires rejection if the ontology is insufficient.

The intent-classification stage is closer to schema-guided zero-shot classification, since it relies on instructions rather than query examples. But the actual text-to-SPARQL stage is clearly not zero-shot.

## 7. Hallucination Mitigation

### 6.1 Main anti-hallucination mechanisms

The backend uses several complementary mechanisms:

#### 1. Prefer deterministic query builders when possible

Many questions never reach free-form SPARQL generation. This is the strongest mitigation strategy in the system.

#### 2. Prompt with repository-specific ontology context

The model is not asked to infer the vocabulary from memory. It is shown the schema and available individuals retrieved from the target repository.

#### 3. Use MLLO-specific query exemplars

Examples teach the correct topological patterns of the ontology, especially for process-model-dataset-performance relations.

#### 4. Set temperature to zero

The LLM gateway uses deterministic decoding (`temperature=0`) for OpenAI-compatible calls, reducing output variance.

#### 5. Validate generated SPARQL against ontology terms

After generation, the backend checks:

- prefix validity,
- whether used prefixed terms correspond to known classes, properties, or individuals,
- whether undeclared prefixes appear.

If invalid terms are found, the model is asked to repair the query using the validation errors.

#### 6. Reject unanswerable questions explicitly

The prompt instructs the model to emit `CANNOT_ANSWER_WITH_ONTOLOGY` if the question cannot be answered from the ontology. The backend detects this and returns a failure rather than fabricating an answer.

#### 7. Repair after execution errors

If a generated query passes lexical validation but fails against GraphDB, the backend performs a second repair turn using the execution error message.

### 6.2 Is ontology use strict?

The system enforces ontology use more strictly than a plain prompt-only NLQ system, but it is not a formally guaranteed constrained decoder.

More precisely:

- It is strict at the level of term vocabulary checking.
- It is semi-strict at the level of query pattern guidance.
- It is not fully strict at the level of logical soundness or semantic completeness.

For example, the validator can reject an invented class or property name. However, it does not prove that the generated triple patterns are semantically optimal or that a domain/range combination is logically correct in every case. Therefore, the system substantially reduces hallucination risk, but does not eliminate it in a formal sense.

### 6.3 Why this still works reasonably well

The ontology is not used merely as post hoc validation. It is part of the prompt context before generation, and it is reinforced by examples and by query execution. This combination is often sufficient for high-quality ontology-grounded generation when the ontology is not excessively large and the question is close to known lifecycle patterns.

## 8. Use of GraphDB Reasoning

The backend can enable or disable GraphDB inference on a per-query basis.

- `use_inference=false` adds `infer=false` to the GraphDB request.
- `use_inference=true` uses the repository’s reasoning capabilities.

Inference is typically enabled for conceptual or hierarchical questions, such as:

- "What kinds of models exist?"
- category or type questions,
- subclass-based exploration.

Inference is typically disabled for exact lookup or operational questions, where explicit assertions are preferred.

This matters because many MLLO queries rely on subclass traversal across both MLLO and imported upper ontologies. In some cases the SPARQL already includes explicit `rdfs:subClassOf*` paths, which performs hierarchy traversal in the query itself. In other cases, GraphDB inference helps expose implicit type membership.

The system therefore uses two forms of semantic expansion:

- query-level expansion through SPARQL property paths,
- store-level expansion through GraphDB inference.

## 9. LLM-to-MCP Interaction

### 8.1 Current implementation reality

In the current codebase, the NLQ route does not call MCP. The interaction model is:

- FastAPI NLQ route -> LLM gateway -> GraphDB client
- external MCP client/agent -> MCP server -> tool functions -> GraphDB client

So MCP is not the orchestration substrate of the web NLQ pipeline. It is an alternate agent-facing interface.

### 8.2 What the MCP layer provides

The MCP server exposes two tool families:

#### Domain-specific MLLO tools

Examples:

- `find_datasets`
- `find_models`
- `find_pipelines`
- `compare_pipelines`
- `analyze_deployed_models`
- `get_artifact_details`
- `explore_category`
- `execute_sparql`

#### Graph-native semantic tools

Examples:

- `find_node_by_label`
- `describe_node`
- `find_surrounding_nodes`
- `get_class_schema`
- `get_class_hierarchy`
- `find_related_classes`
- `find_shortest_path`
- `trace_lineage`
- `count_by_type`

These tools are deterministic wrappers around SPARQL templates and graph operations.

### 8.3 Why MCP matters conceptually

Although the web NLQ path does not currently use MCP internally, MCP is still significant for the research architecture because it represents a stronger grounding mode for agent-based querying. In an MCP-based flow, an external LLM can reason by calling tools instead of directly generating the final SPARQL in one step.

That architecture can reduce hallucination further because:

- the LLM can inspect the schema incrementally,
- entity resolution can be delegated to tools,
- graph neighborhoods can be explored stepwise,
- final execution can be grounded in deterministic tool outputs.

In other words, the current codebase contains two complementary paradigms:

- direct ontology-constrained text-to-SPARQL inside the web backend,
- tool-mediated ontology exploration via MCP for external agent systems.

## 10. Can Strict Ontology Use Support Newly Loaded MLLO-Mapped Datasets?

### 9.1 Short answer

Yes, if the datasets are loaded into GraphDB as MLLO-aligned RDF and the mappings preserve the lifecycle relations expected by the query templates, the system should query them effectively and produce useful answers. In the concrete setup described here, this means the instance graph in `data.ttl` must connect correctly to classes and relations defined in `MLLO.rdf` and, where relevant, to imported ontologies such as BFO and IOF Core.

### 9.2 Why the system can generalize to new mapped data

The backend does not hardcode most instance identifiers. It queries by ontology structure. Therefore, if new datasets are mapped into MLLO using the same semantic patterns, the same SPARQL templates continue to work.

Examples of crucial patterns include:

- dataset linked to process via `ml:hasDataInput`,
- model linked to process via `ml:executes` or `bfo:BFO_0000057`,
- performance assessment connected through `ml:hasDataOutput` and relevant metric structures,
- pipeline composition represented through BFO process-composition properties,
- class typing and hierarchy links that remain consistent with MLLO, BFO, and IOF Core semantics.

If newly loaded data respects these patterns, the backend can retrieve it because the queries are relation-based rather than identifier-based.

### 9.3 How the system discovers those new data

There are two mechanisms:

#### Through deterministic queries

Structured queries over classes and relations automatically include any new individuals that satisfy the same graph patterns.

#### Through runtime ontology-context loading

The NLQ subsystem retrieves named individuals and ontology terms from the current repository at runtime. If the repository contains new MLLO-mapped entities and labels, those entities can appear in the prompt context and become available to LLM-generated queries as well.

### 9.4 When answer quality will be good

Answer quality will generally be good when:

- the RDF mapping is semantically faithful to MLLO,
- the imported ontology layer is present and consistent,
- labels are present and meaningful,
- model, dataset, process, metric, and pipeline relations are explicitly represented,
- type assertions and subclass links are present or inferable,
- performance values are stored in the patterns expected by the query templates.

### 9.5 When answer quality will degrade

The system will degrade when:

- the mapping uses ontology classes inconsistently,
- critical lifecycle links are missing,
- labels are absent or opaque,
- equivalent concepts are represented with nonstandard local modeling choices,
- question wording has poor lexical overlap with labels and local names,
- the needed answer depends on semantics not represented in MLLO or in the loaded instance graph.

Therefore, the limiting factor is not only the LLM. It is the quality and completeness of the ontology mapping.

## 11. Research Interpretation of the Architecture

From a research perspective, this backend is best characterized as a hybrid neuro-symbolic query system rather than a pure LLM QA system.

Its symbolic components are:

- RDF/OWL ontology and instance graph,
- handcrafted SPARQL templates,
- GraphDB reasoning,
- ontology-term validation,
- deterministic graph-native tools.

Its neural components are:

- LLM-based intent classification,
- LLM-based custom SPARQL synthesis,
- LLM-based repair,
- LLM-based answer verbalization.

The architecture delegates high-precision operations to symbolic infrastructure and reserves the LLM for tasks where linguistic flexibility is needed.

That division of labor is the main reason the system is more robust than a naive text-to-SPARQL prompt.

## 12. Limitations

Several limitations should be stated explicitly in a research paper.

### 11.1 No formal constrained decoding

The system constrains prompts and validates outputs, but it does not use grammar-constrained decoding, typed query synthesis, or theorem-backed semantic verification.

### 11.2 Lexical retrieval for ontology context

Relevant-subgraph selection is token-based, not embedding-based and not graph-theoretic in a strong sense. This is efficient but can miss semantically relevant concepts when lexical overlap is weak.

### 11.3 Limited semantic validation

Validation checks whether terms exist in the ontology context, but not whether all generated joins are semantically justified.

### 11.4 Dependence on ontology modeling conventions

Performance and generalization depend heavily on whether new data are mapped according to the same MLLO lifecycle patterns used in query templates and examples.

### 11.5 MCP not yet integrated into the web NLQ planner

The codebase already contains a rich MCP tool layer, but the web NLQ path does not yet use that layer as an internal reasoning substrate. Integrating tool-mediated planning could further improve reliability.

## 13. Suggested Figures for a Paper

### Figure 1. Overall backend architecture

Show five blocks from left to right:

1. User or frontend
2. FastAPI backend
3. LLM gateway
4. GraphDB repository
5. MCP server

Then show:

- NLQ flow from frontend to FastAPI to LLM gateway and GraphDB
- Structured query flow from frontend to FastAPI directly to GraphDB
- External agent flow from agent to MCP server to GraphDB

The key point of the figure should be that MCP is parallel to, not inside, the current FastAPI NLQ execution path.

### Figure 2. NLQ execution pipeline

Show a sequential diagram:

1. Question input
2. Intent classification
3. Query-path selection
4. Ontology context retrieval
5. SPARQL generation or deterministic query building
6. Validation and repair
7. GraphDB execution
8. Result summarization

Annotate the branches:

- structured route,
- performance-query route,
- custom SPARQL route.

### Figure 3. Hallucination-control stack

Use a layered figure with the LLM in the middle and constraints around it:

- deterministic routing before generation,
- ontology retrieval,
- few-shot MLLO query examples,
- zero-temperature decoding,
- vocabulary validation,
- repair loop,
- GraphDB execution grounding.

This figure should communicate that hallucination prevention is not one method, but a stack of safeguards.

### Figure 4. Data generalization to newly mapped datasets

Show how a newly loaded MLLO-mapped dataset enters GraphDB, becomes available through the same ontology relations, is retrieved by deterministic or generated SPARQL, and is finally summarized into an answer.

The emphasis should be that generalization occurs through shared ontology structure, not memorization of specific dataset names.

## 14. Concise Characterization for a Paper

If a short summary sentence is needed, the backend can be described as follows:

"MLLO-Web implements a hybrid ontology-grounded natural-language querying architecture in which an LLM performs intent classification, constrained SPARQL synthesis, repair, and answer verbalization, while GraphDB, SPARQL templates, and MLLO schema retrieval provide the symbolic grounding needed to reduce hallucination and preserve semantic fidelity."

## Appendix A. Literal Prompt Text

This appendix records the literal prompt text currently used in the backend implementation.

### A.1 Intent-selection system prompt (`INTENT_SYSTEM_PROMPT`)

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

### A.2 SPARQL-generation system prompt (`SYSTEM_MESSAGE`)

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

### A.3 Repair prompt (`REPAIR_MESSAGE`)

```text
The previous SPARQL was invalid for this ontology or could not be parsed. Fix it strictly using the provided ontology vocabulary and return ONLY corrected SPARQL.
```

### A.4 Answer-summarization system prompt

```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets or pipelines, use them directly and do not replace them with generic guesses.
```

## Appendix B. Three Real NLQ Tool Flows

This appendix records three live example runs captured from the backend against the local `mllo4` repository. Each example includes the user input, the LLM prompt/response at each step, the executed SPARQL, and the observed output pattern.

### B.1 Example 1: Deterministic tool path

User input:

```text
Show me models trained on MNIST
```

Step 1. Intent selection

System prompt used:

- `INTENT_SYSTEM_PROMPT` from Appendix A.1

User message:

```text
Show me models trained on MNIST
```

LLM response:

```json
{
  "tool": "find_models",
  "params": {
    "dataset": "MNIST"
  },
  "use_inference": false,
  "reasoning": "User asks for models trained on a specific dataset (MNIST), which is an exact lookup."
}
```

Step 2. Query execution

Execution path:

- deterministic `FindModelsQueryBuilder`
- no SPARQL-generation prompt
- no repair loop

Executed SPARQL excerpt:

```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT
    ?dataset
    ?dataset_used_as
    ?dataset_used_for
    ?dataset_characteristics
    ?ml_input_timestamp
    ?model_name
    ?model_performance_metric
    ?model_performance_value
FROM <http://www.ontotext.com/explicit>
WHERE {
    ?ml_process ml:hasDataInput/ml:informationContentEntityDerivedFrom* ?dataset .
    ?ml_process (bfo:BFO_0000057 | ml:executes) ?model_name .
    ...
}
```

Observed output:

- result count: `36`
- result shape: dataset IRI, dataset role label, usage purpose, dataset characteristics, timestamp, model IRI, performance metric, performance value

Observed result excerpt:

```json
{
  "dataset": "http://example.com/MNIST#PreprocessedDataset1",
  "dataset_used_as": "test data set",
  "dataset_used_for": "model evaluation",
  "dataset_characteristics": "gaussian noise;gaussian noise, has standard deviation value: 16",
  "ml_input_timestamp": "2024-01-15T08:00:00-04:00",
  "model_name": "http://example.com/MNIST#MLModel1",
  "model_performance_metric": "classification accuracy",
  "model_performance_value": "0.9789"
}
```

Step 3. Answer summarization

System prompt used:

- answer-summarization prompt from Appendix A.4

Observed behavior:

- the summarizer converted 36 rows into a readable table and narrative summary
- no ontology hallucination risk was introduced at query time because the SPARQL was fully deterministic

### B.2 Example 2: Performance-planner path

User input:

```text
Show me the best performing model and its test dataset
```

Step 1. Intent selection

System prompt used:

- `INTENT_SYSTEM_PROMPT`

User message:

```text
Show me the best performing model and its test dataset
```

LLM response:

```json
{
  "tool": "custom_sparql",
  "params": {
    "query": "SELECT ?model ?dataset ?accuracy WHERE { ?model a ml:Model ; ml:trainedOn ?dataset ; ml:testAccuracy ?accuracy . } ORDER BY DESC(?accuracy) LIMIT 1"
  },
  "use_inference": false,
  "reasoning": "Need to rank models by performance metric (test accuracy) and retrieve the top model and its test dataset, which requires a custom SPARQL query."
}
```

Important implementation detail:

- although the classifier chose `custom_sparql`, the backend did not execute that raw query string
- instead, the question matched the deterministic performance-analysis shortcut
- therefore the runtime path became a two-step handcrafted query plan

Step 2. Performance filter query

Execution path:

- deterministic performance query builder
- `use_inference=true`
- no SPARQL-generation prompt
- no repair loop

Executed SPARQL excerpt:

```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?model_name ?model_performance_metric ?model_performance_value WHERE {
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    ...
    FILTER(LCASE(STR(?model_performance_metric)) = "classification accuracy")
}
ORDER BY DESC(xsd:decimal(?model_performance_value))
LIMIT 1
```

Step 3. Follow-up test-dataset query

Executed SPARQL excerpt:

```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model_name ?dataset ?dataset_role WHERE {
    VALUES ?model_name { <http://example.com/MNIST#MLModel1> }
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?ml_process ml:hasDataInput ?dataset .
    ?dataset rdf:type ?dataset_type .
    ?dataset_type rdfs:subClassOf* ml:TestDataSet .
    OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
}
LIMIT 200
```

Observed output:

- result count: `1`
- output shape: best model IRI, performance metric, performance value, list of test dataset IRIs, list of dataset-role labels

Observed result excerpt:

```json
{
  "model_name": "http://example.com/MNIST#MLModel1",
  "model_performance_metric": "classification accuracy",
  "model_performance_value": "0.9807",
  "test_datasets": [
    "http://example.com/MNIST#PreprocessedDataset1",
    "http://example.com/MNIST#PreprocessedDataset2",
    "http://example.com/MNIST#PreprocessedDataset3",
    "http://example.com/MNIST#PreprocessedDataset4",
    "http://example.com/MNIST#PreprocessedDataset5",
    "http://example.com/MNIST#PreprocessedDataset6"
  ],
  "test_dataset_roles": [
    "test data set",
    "test data set",
    "test data set",
    "test data set",
    "test data set",
    "test data set"
  ]
}
```

Step 4. Answer summarization

System prompt used:

- answer-summarization prompt from Appendix A.4

Observed behavior:

- the summarizer reused the joined `test_datasets` field directly, as instructed by the system prompt
- no SPARQL repair or ontology-generation prompt was needed

### B.3 Example 3: Routed conceptual question overridden by the performance-planner path

User input:

```text
How do different hyperparameter configurations impact model performance?
```

Step 1. Intent selection

System prompt used:

- `INTENT_SYSTEM_PROMPT`

User message:

```text
How do different hyperparameter configurations impact model performance?
```

LLM response:

```json
{
  "tool": "explore_category",
  "params": {
    "category": "hyperparameter_configuration"
  },
  "use_inference": true,
  "reasoning": "The question asks conceptually how different hyperparameter settings affect model performance, requiring hierarchical/conceptual exploration."
}
```

Important implementation detail:

- even though the routed intent was `explore_category`, the backend first checks for performance-oriented language
- because the question contains the keyword `performance`, it matched the deterministic performance-analysis path before ordinary tool execution
- therefore the actual runtime query was again a handcrafted performance filter

Step 2. Performance filter query

Execution path:

- deterministic performance query builder
- `use_inference=true`
- no SPARQL-generation prompt
- no repair loop

Executed SPARQL excerpt:

```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?model_name ?model_performance_metric ?model_performance_value WHERE {
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    ...
    FILTER(LCASE(STR(?model_performance_metric)) = "classification accuracy")
}
ORDER BY DESC(xsd:decimal(?model_performance_value))
LIMIT 50
```

Observed output:

- result count: `18`
- output shape: repeated model-performance rows, one per matched performance observation

Observed result excerpt:

```json
[
  {
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9807"
  },
  {
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9803"
  },
  {
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9789"
  }
]
```

Step 3. Answer summarization

System prompt used:

- answer-summarization prompt from Appendix A.4

Observed behavior:

- the summarizer aggregated the repeated performance rows into a comparative narrative about model sensitivity to hyperparameter settings
- this example shows that conceptual intent selection can still be overridden by the deterministic performance planner when the question contains strong metric-related language

### B.4 Interpretation of the three examples

These live examples show three important properties of the current backend:

1. Intent selection is LLM-driven, but final execution is not determined by intent alone. The backend contains deterministic overrides, especially for performance questions.
2. Most successful runs do not require free-form SPARQL generation. Deterministic query builders cover a large share of practical questions.
3. The answer-summarization step is always LLM-based, but it operates on executed graph results rather than on the raw question alone.

## Appendix C. Live `custom_sparql` Path Trace

This appendix documents one live execution of the `custom_sparql` path, starting from the point where the backend has already routed a question to free-form SPARQL generation. Internally, this path is implemented through `_generate_sparql()`. The trace was captured by running the real backend code against the local `mllo4` GraphDB repository and the configured local LLM endpoint.

Trace artifact:

- [tmp/custom_sparql_trace.json](/Users/pnc12/Documents/GitHub/MLLO-Web-2/tmp/custom_sparql_trace.json)

Capture helper:

- [scripts/capture_custom_sparql_trace.py](/Users/pnc12/Documents/GitHub/MLLO-Web-2/scripts/capture_custom_sparql_trace.py)

### C.1 Entry point: `custom_sparql`

In the NLQ pipeline, `custom_sparql` is the fallback tool for questions that are too custom for the deterministic query builders. Once the router selects `custom_sparql`, the backend enters `_generate_sparql()` to construct ontology-grounded SPARQL.

### C.2 Input to `_generate_sparql()`

Observed input:

```text
question = "Which datasets are consumed by processes that execute a machine learning model?"
repo = "mllo4"
provider = lm_studio
model = openai/gpt-oss-120b
```

### C.3 Step 1: live schema retrieval from GraphDB

The backend first queried the live GraphDB repository for ontology/schema information before constructing the prompt. This step does not use one final answer query. Instead, it uses four separate schema/context retrieval queries:

- `ONTOLOGY_SCHEMA_QUERY`
- `PREFIX_QUERY`
- `SAMPLE_TRIPLES_QUERY`
- `NAMED_INDIVIDUALS_QUERY`

Their roles are:

- `ONTOLOGY_SCHEMA_QUERY`: returns classes, object properties, datatype properties, annotation properties, labels, domains, and ranges
- `PREFIX_QUERY`: returns namespace prefixes and namespace IRIs
- `SAMPLE_TRIPLES_QUERY`: returns a small sample of repository triples for context
- `NAMED_INDIVIDUALS_QUERY`: returns named individuals together with labels and types

Observed schema-fetch output:

- ontology schema rows: `679`
- prefix rows: `5`
- sample triples: `30`
- named individuals: `195`

Observed preview:

```json
{
  "type": "AnnotationProperty",
  "entity": "http://purl.org/dc/terms/abstract",
  "label": "abstract"
}
```

Interpretation:

- the schema fetch included MLLO, imported ontologies such as BFO and IOF Core, and additional annotations present in the loaded repository
- the backend therefore did not rely only on a hardcoded ontology snapshot

In other words, the live `custom_sparql` path first asks GraphDB what ontology terms and instance names exist, and only after that does it construct the LLM prompt.

### C.4 Step 2: internal ontology-context construction

The backend transformed the raw schema rows into its internal ontology object.

Observed output summary:

- prefixes: `7`
- classes: `285`
- object properties: `29`
- datatype properties: `11`
- annotation properties: `46`
- named individuals: `181`
- sample triples: `30`

Interpretation:

- these counts describe the full internal ontology context before question-specific pruning

### C.5 Step 3: relevant-subgraph selection

The backend then reduced the ontology to the part judged lexically relevant to the user question.

Observed reduced-context summary:

- prefixes: `7`
- classes: `80`
- object properties: `0`
- datatype properties: `0`
- annotation properties: `46`
- named individuals: `95`

Interpretation:

- for this particular question, lexical scoring selected many MLLO classes and individuals but no object or datatype properties
- despite that reduction, the later SPARQL generation still succeeded because the system prompt and example queries encode the core ML-process patterns explicitly
- this trace also reveals a limitation of the current lexical pruning method: relevant properties may be omitted from the reduced schema text even when the final query still needs them

How this step is implemented:

1. The backend tokenizes the user question with `_tokenize_query()`.
   - text is lowercased
   - alphanumeric tokens are extracted
   - short/common stopwords are removed

2. For each ontology item, the backend derives searchable terms with `_extract_terms()`.
   - terms come from the human-readable label when present
   - terms also come from the IRI local name
   - CamelCase local names are split into separate lexical terms

3. Classes are scored first.
   - score = overlap between question tokens and class terms
   - only classes with score greater than zero are retained
   - top-scoring classes are kept, up to the configured class limit

4. Object properties are scored next.
   - score starts as lexical overlap with the question
   - score is increased if the property domain or range matches an already selected class
   - only positive-scoring properties are kept

5. Datatype properties are scored similarly.
   - lexical overlap contributes to the score
   - score is increased when the property domain matches an already selected class

6. Named individuals are scored last.
   - lexical overlap contributes to the score
   - score is increased when the individual type matches an already selected class

7. A small relation-aware expansion step is applied.
   - if a selected property has a known domain or range class, those classes are added
   - if a selected class has a superclass, that superclass is also added

8. The reduced context is returned.
   - prefixes are preserved
   - selected classes, properties, and individuals are retained
   - annotation properties are passed through
   - sample triples are preserved

This means Step 3 is a lexical schema-retrieval heuristic with limited structural expansion. It is not vector retrieval, not graph embedding retrieval, and not full ontology reasoning.

### C.6 Step 4: prompt text construction

The backend serialized the reduced ontology context into prompt text and built the actual LLM message list.

Observed message sequence:

1. system message = `SYSTEM_MESSAGE`
2. user message = question + reduced ontology schema text + `EXAMPLE_QUERIES` + instruction to generate a SPARQL `SELECT`

Observed ontology-text prefix:

```text
=== PREFIXES ===
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
```

Observed class-section excerpt:

```text
ml:MachineLearningDataSet  # machine learning data set
ml:MachineLearningModel  # machine learning model
ml:MachineLearningTraining  # machine learning training
ml:ModelExecution  # model execution
ml:ModelPerformanceAssessment  # model performance assessment
```

Real prompt payload used in this live run:

System message sent to the LLM:

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

User message sent to the LLM in this live run:

```text
User question: Which datasets are consumed by processes that execute a machine learning model?

Ontology schema:
=== PREFIXES ===
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>

=== CLASSES ===
  bfo:IAO_0000027  # data item
  bfo:IAO_0000100  # data set
  ml:AssociationRuleLearningAlgorithm  # association rule learning algorithm
  ...
  ml:MachineLearningDataSet  # machine learning data set
  ml:MachineLearningModel  # machine learning model
  ml:MachineLearningTraining  # machine learning training
  ml:ModelExecution  # model execution
  ml:ModelPerformanceAssessment  # model performance assessment
  ...

=== OBJECT PROPERTIES ===

=== DATATYPE PROPERTIES ===

=== EXAMPLE QUERIES ===
-- Example 1: Find all ML models with their type, objective, dataset, and performance --
...
-- Example 4: Find all datasets used in ML processes with their role and model --
...

Generate a SPARQL SELECT query to answer the question. Use ONLY the listed classes, properties, individuals, and prefixes.
```

The complete captured prompt, including the full ontology text and full `EXAMPLE_QUERIES` block, is stored in:

- [tmp/custom_sparql_trace.json](/Users/pnc12/Documents/GitHub/MLLO-Web-2/tmp/custom_sparql_trace.json)

### C.7 Step 5: raw LLM output

The live LLM call returned:

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>

SELECT DISTINCT ?dataset
WHERE {
  ?ml_process (ml:executes|bfo:BFO_0000057) ?model .
  ?ml_process ml:hasDataInput ?dataset .
}
LIMIT 100
```

Interpretation:

- the model used the canonical ML-process pattern correctly
- it returned a compact query without extra explanation
- it did not emit `CANNOT_ANSWER_WITH_ONTOLOGY`

### C.8 Step 6: extraction and validation

The backend then:

1. extracted the SPARQL text from the raw model response
2. validated prefixes and ontology terms against the full fetched ontology context

Observed outputs:

- extracted SPARQL: successful
- validation errors: `[]`

Interpretation:

- no invented terms were detected
- no repair pass was required in this run

### C.9 Step 7: repair loop status

Observed repair status:

- `repair_trace = null`

Meaning:

- the backend did not need to send `REPAIR_MESSAGE`
- there was no validation-repair loop in this live execution

### C.10 Step 8: final prefix injection

The backend injected the required prefixes into the final executable form.

Observed final SPARQL:

```sparql
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?dataset
WHERE {
  ?ml_process (ml:executes|bfo:BFO_0000057) ?model .
  ?ml_process ml:hasDataInput ?dataset .
}
LIMIT 100
```

### C.11 Sequence summary: real input and output at each stage

1. Input question:

```text
Which datasets are consumed by processes that execute a machine learning model?
```

2. Schema-fetch output:

```text
679 schema rows, 5 prefix rows, 30 sample triples, 195 named individuals
```

3. Full ontology-context output:

```text
285 classes, 29 object properties, 11 datatype properties, 46 annotation properties, 181 individuals
```

4. Reduced prompt-context output:

```text
80 classes, 0 object properties, 0 datatype properties, 46 annotation properties, 95 individuals
```

5. Prompt output to LLM:

```text
SYSTEM_MESSAGE + question + reduced ontology text + EXAMPLE_QUERIES
```

6. Raw LLM output:

```sparql
SELECT DISTINCT ?dataset
WHERE {
  ?ml_process (ml:executes|bfo:BFO_0000057) ?model .
  ?ml_process ml:hasDataInput ?dataset .
}
LIMIT 100
```

7. Validation output:

```text
no validation errors
```

8. Repair-loop output:

```text
not triggered
```

9. Final function output:

```text
validated SPARQL string + ontology context object
```

### C.12 What this live trace shows

This live run makes the internal sequence explicit:

1. GraphDB schema is queried first.
2. The schema is converted into an internal ontology object.
3. A reduced subgraph is selected for prompting.
4. The LLM receives both schema context and MLLO-specific example queries.
5. The LLM returns SPARQL.
6. The backend validates that SPARQL against the ontology.
7. Only then is the SPARQL accepted for later execution.

This is therefore not a direct zero-context text-to-SPARQL call. It is a staged ontology-grounded generation pipeline.
