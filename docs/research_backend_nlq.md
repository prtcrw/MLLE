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

## 4. Ontology Grounding Strategy

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

## 5. Prompting Technique: Zero-shot or Not?

The SPARQL generation stage is not zero-shot.

It is better described as ontology-grounded few-shot constrained generation:

- ontology-grounded, because the current repository schema is injected into the prompt;
- few-shot, because multiple MLLO-specific SPARQL examples are included;
- constrained, because the prompt explicitly forbids invented terms and requires rejection if the ontology is insufficient.

The intent-classification stage is closer to schema-guided zero-shot classification, since it relies on instructions rather than query examples. But the actual text-to-SPARQL stage is clearly not zero-shot.

## 6. Hallucination Mitigation

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

## 7. Use of GraphDB Reasoning

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

## 8. LLM-to-MCP Interaction

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

## 9. Can Strict Ontology Use Support Newly Loaded MLLO-Mapped Datasets?

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

## 10. Research Interpretation of the Architecture

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

## 11. Limitations

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

## 12. Suggested Figures for a Paper

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

## 13. Concise Characterization for a Paper

If a short summary sentence is needed, the backend can be described as follows:

"MLLO-Web implements a hybrid ontology-grounded natural-language querying architecture in which an LLM performs intent classification, constrained SPARQL synthesis, repair, and answer verbalization, while GraphDB, SPARQL templates, and MLLO schema retrieval provide the symbolic grounding needed to reduce hallucination and preserve semantic fidelity."
