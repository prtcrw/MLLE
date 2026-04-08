# MLLO-Web Architecture Visualization

## Overall System Flow

```mermaid
flowchart TB
    U["User"] --> FE["Frontend / Web UI"]
    FE --> API["FastAPI Backend"]
    API --> NLQ["NLQ Router"]

    NLQ --> INTENT["Intent Selection<br/>LLM-based"]

    INTENT --> D1["Deterministic Tool Path"]
    INTENT --> P1["Performance Planner Path"]
    INTENT --> C1["custom_sparql Path"]

    D1 --> QB["Deterministic SPARQL Query Builders<br/>find_datasets / find_models / find_pipelines<br/>analyze_deployed_models / compare_pipelines<br/>get_artifact_details / explore_category"]
    QB --> GDB["GraphDB Repository"]

    P1 --> PERF["Performance Query Planner<br/>ranking / threshold / best-model logic"]
    PERF --> FOLLOW["Optional Follow-up Queries<br/>test datasets / pipelines"]
    FOLLOW --> GDB

    C1 --> SCHEMA["Schema Retrieval from GraphDB<br/>ONTOLOGY_SCHEMA_QUERY<br/>PREFIX_QUERY<br/>SAMPLE_TRIPLES_QUERY<br/>NAMED_INDIVIDUALS_QUERY"]
    SCHEMA --> SUBGRAPH["Relevant-Subgraph Selection<br/>deterministic lexical ontology pruning"]
    SUBGRAPH --> PROMPT["Prompt Assembly<br/>system prompt + reduced ontology + example queries"]
    PROMPT --> LLM["LLM Gateway"]
    LLM --> RAW["Generated SPARQL"]
    RAW --> VALIDATE["SPARQL Validation<br/>prefix + ontology term checks"]
    VALIDATE -->|invalid| REPAIR["Repair Loop<br/>REPAIR_MESSAGE"]
    REPAIR --> LLM
    VALIDATE -->|valid| EXEC["Execute Final SPARQL"]
    EXEC --> GDB

    GDB --> RES["SPARQL Results"]
    RES --> SUM["Answer Summarization<br/>LLM-based"]
    SUM --> OUT["Answer + SPARQL + Results"]

    API --> MCPNOTE["MCP is parallel to web NLQ path"]

    AGENT["External Agent"] --> MCP["MCP Server"]
    MCP --> TOOLS["Graph / Ontology Tools<br/>find_datasets / find_models / execute_sparql<br/>describe_node / get_class_hierarchy / find_shortest_path"]
    TOOLS --> GDB

    subgraph KB["Knowledge Layer"]
        GDB
        ONT["MLLO.rdf"]
        BFO["BFO"]
        IOF["IOF Core"]
        DATA["data.ttl"]
    end

    ONT --> GDB
    BFO --> GDB
    IOF --> GDB
    DATA --> GDB
```

## NLQ Decision Flow

```mermaid
flowchart LR
    Q["Natural-language question"] --> I["Intent Selection<br/>LLM-based"]

    I --> T["Structured tool intent?<br/>find_datasets / find_models / ..."]
    I --> M["Performance / ranking question?"]
    I --> C["Too custom for fixed tools?"]

    T --> DT["Deterministic query builder"]
    M --> PP["Deterministic performance planner"]
    C --> CS["custom_sparql generation"]

    DT --> X["Execute in GraphDB"]
    PP --> X
    CS --> X

    X --> S["Summarize result with LLM"]
```

## Detailed `custom_sparql` Flow

```mermaid
flowchart TB
    Q["Question routed to custom_sparql"] --> L1["Load ontology context from GraphDB"]

    L1 --> Q1["ONTOLOGY_SCHEMA_QUERY"]
    L1 --> Q2["PREFIX_QUERY"]
    L1 --> Q3["SAMPLE_TRIPLES_QUERY"]
    L1 --> Q4["NAMED_INDIVIDUALS_QUERY"]

    Q1 --> CTX["Full ontology context"]
    Q2 --> CTX
    Q3 --> CTX
    Q4 --> CTX

    CTX --> RS["Relevant-subgraph selection<br/>deterministic, non-LLM"]
    RS --> PT["Ontology text serialization"]
    PT --> PM["Prompt assembly<br/>SYSTEM_MESSAGE + ontology text + EXAMPLE_QUERIES"]
    PM --> LLM["LLM Gateway"]
    LLM --> RSP["Raw model output"]
    RSP --> EX["Extract SPARQL"]
    EX --> V["Validate SPARQL against ontology context"]

    V -->|errors| RP["Repair prompt<br/>REPAIR_MESSAGE + validation errors"]
    RP --> LLM

    V -->|valid| PX["Inject missing prefixes"]
    PX --> RUN["Execute SPARQL in GraphDB"]
    RUN --> RES["Results"]
    RES --> AS["Answer summarization prompt"]
    AS --> FINAL["Final answer"]
```

## Figure Notes

- The deterministic tool path covers most standard user questions and does not require live schema retrieval for prompting.
- The performance planner path can override the original routed intent if the question contains ranking or metric language.
- The `custom_sparql` path is the only path that first queries GraphDB for ontology schema context before asking the LLM to generate SPARQL.
- Relevant-subgraph selection is deterministic code, not an LLM step.
- MCP is a parallel agent-facing interface to the same GraphDB-backed functionality, not an internal step in the FastAPI NLQ pipeline.
