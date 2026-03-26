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
