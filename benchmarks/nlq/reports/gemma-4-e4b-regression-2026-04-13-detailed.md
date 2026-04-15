# Gemma 4 e4b Detailed Regression Trace
This report was generated from the saved NLQ trace logs for the successful `google/gemma-4-e4b` regression run on 2026-04-13.
## Run Summary
- Provider: `lm_studio`
- Base URL: `http://127.0.0.1:1234/v1`
- Model: `google/gemma-4-e4b`
- Regression result: `Ran 7 tests in 458.238s` and `OK`
- Trace entries included here: `15`

## Questions Covered
- 1. `Which kinds of datasets exist in MLLO?`
- 2. `Which datasets are consumed by processes that execute a machine learning model?`
- 3. `Which datasets are produced by processes that also use a model output?`
- 4. `Which models and pipelines share the same dataset?`
- 5. `Which model outputs are later used as inputs to another process?`
- 6. `Which pipelines share a dataset with a model?`
- 7. `What downstream artifacts use MnistG16?`
- 8. `What models use downstream artifacts of MnistG16?`
- 9. `Which models use downstream artifacts of MnistG16?`
- 10. `Show me models their test dataset, and their pipeline that has performance more than 0.9`
- 11. `What pipeline uses MnistG16?`
- 12. `What models use MnistG16 as test dataset?`
- 13. `What models use MnistG16 as training dataset?`
- 14. `What datasets are downstream of MnistG16?`
- 15. `Show me models with performance more than 0.95`

## 1. Which kinds of datasets exist in MLLO?
- Started: `2026-04-13T20:27:30.325390+00:00`
- Intent tool: `explore_category`
- Inference used: `True`
- Result count: `100`
- Intent reasoning: The user is asking for the types or categories of datasets, which requires conceptual exploration using explore_category. Since it's a 'what kinds of' question, inference must be enabled.
- Result keys: `entity, entity_type, label`

### Executed Steps

#### Step 1: `explore_category`
- Params: `{'category': 'dataset'}`
- Result count: `100`
- Reasoning: The user is asking for the types or categories of datasets, which requires conceptual exploration using explore_category. Since it's a 'what kinds of' question, inference must be enabled.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?entity ?entity_type ?label
WHERE {
    {
        ?entity rdfs:subClassOf+ ml:MachineLearningDataSet .
        BIND("Class" AS ?entity_type)
        OPTIONAL { ?entity rdfs:label ?label }
        FILTER(?entity != <http://www.w3.org/2002/07/owl#Nothing>)
    }
    UNION
    {
        ?entity rdf:type/rdfs:subClassOf* ml:MachineLearningDataSet .
        OPTIONAL { ?entity rdf:type/rdfs:label ?entity_type }
        OPTIONAL { ?entity rdfs:label ?label }
        FILTER(?entity != <http://www.w3.org/2002/07/owl#Nothing>)
    }
}
LIMIT 100

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1875`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
Which kinds of datasets exist in MLLO?
```

Response text:
```text
```json
{
  "tool": "explore_category",
  "params": {
    "category": "dataset"
  },
  "use_inference": true,
  "reasoning": "The user is asking for the types or categories of datasets, which requires conceptual exploration using explore_category. Since it's a 'what kinds of' question, inference must be enabled."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `3131`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: Which kinds of datasets exist in MLLO?

Filtered results:
[
  {
    "entity": "http://www.semanticweb.org/mnd14/ml/MachineLearningDataSet",
    "entity_type": "Class",
    "label": "machine learning data set"
  },
  {
    "entity": "http://www.semanticweb.org/mnd14/ml/TrainingDataSet",
    "entity_type": "Class",
    "label": "training data set"
  },
  {
    "entity": "http://www.semanticweb.org/mnd14/ml/TestDataSet",
    "entity_type": "Class",
    "label": "test data set"
  },
  {
    "entity": "http://www.semanticweb.org/mnd14/ml/ValidationDataSet",
    "entity_type": "Class",
    "label": "validation data set"
  },
  {
    "entity": "http://www.semanticweb.org/mnd14/ml/ProductionMachineLearningDataSet",
    "entity_type": "Class",
    "label": "production machine learning data set"
  },
  {
    "entity": "node2093",
    "entity_type": "Class",
    "label": null
  },
  {
    "entity": "node2157",
    "entity_type": "Class",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset1",
    "entity_type": "information content entity",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset1",
    "entity_type": "ICE",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset1",
    "entity_type": "Information",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset1",
    "entity_type": "data set",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset1",
    "entity_type": "machine learning data set",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset1",
    "entity_type": "test data set",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset10",
    "entity_type": "information content entity",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset10",
    "entity_type": "ICE",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset10",
    "entity_type": "Information",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset10",
    "entity_type": "data set",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset10",
    "entity_type": "machine learning data set",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset10",
    "entity_type": "test data set",
    "label": null
  },
  {
    "entity": "http://example.com/MNIST#PreprocessedDataset11",
    "entity_type": "information content entity",
    "label": null
  }
]

Planned steps:
[]

Execution steps:
[
  {
    "tool": "explore_category",
    "params": {
      "category": "dataset"
    },
    "result_count": 100
  }
]
```

Response text:
```text
Based on the ML Ontology Library (MLLO), several distinct types of datasets are defined:

*   **Machine Learning Data Set:** The general category for any dataset used in machine learning.
*   **Training Data Set:** Used to teach or train the model.
*   **Test Data Set:** Used to evaluate how well the trained model performs on unseen data.
*   **Validation Data Set:** Used during training to fine-tune the model's parameters and prevent overfitting.
*   **Production Machine Learning Data Set:** Datasets intended for use in a live, operational environment.
```

### Final SPARQL
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?entity ?entity_type ?label
WHERE {
    {
        ?entity rdfs:subClassOf+ ml:MachineLearningDataSet .
        BIND("Class" AS ?entity_type)
        OPTIONAL { ?entity rdfs:label ?label }
        FILTER(?entity != <http://www.w3.org/2002/07/owl#Nothing>)
    }
    UNION
    {
        ?entity rdf:type/rdfs:subClassOf* ml:MachineLearningDataSet .
        OPTIONAL { ?entity rdf:type/rdfs:label ?entity_type }
        OPTIONAL { ?entity rdfs:label ?label }
        FILTER(?entity != <http://www.w3.org/2002/07/owl#Nothing>)
    }
}
LIMIT 100

```

### Result Preview
```json
[{'entity': 'http://www.semanticweb.org/mnd14/ml/MachineLearningDataSet', 'entity_type': 'Class', 'label': 'machine learning data set'}, {'entity': 'http://www.semanticweb.org/mnd14/ml/TrainingDataSet', 'entity_type': 'Class', 'label': 'training data set'}, {'entity': 'http://www.semanticweb.org/mnd14/ml/TestDataSet', 'entity_type': 'Class', 'label': 'test data set'}, {'entity': 'http://www.semanticweb.org/mnd14/ml/ValidationDataSet', 'entity_type': 'Class', 'label': 'validation data set'}, {'entity': 'http://www.semanticweb.org/mnd14/ml/ProductionMachineLearningDataSet', 'entity_type': 'Class', 'label': 'production machine learning data set'}]
```

## 2. Which datasets are consumed by processes that execute a machine learning model?
- Started: `2026-04-13T20:27:46.459018+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `29`
- Intent reasoning: The question asks for a lineage or provenance relationship: identifying datasets that are consumed (used as input) by processes (pipelines/models). This requires tracing dependencies across the ML lifecycle, making custom_sparql the appropriate tool for lineage and source-of questions.
- Result keys: `dataset`

### Executed Steps

#### Step 1: `custom_sparql`
- Params: `{}`
- Result count: `29`
- Reasoning: The question asks for a lineage or provenance relationship: identifying datasets that are consumed (used as input) by processes (pipelines/models). This requires tracing dependencies across the ML lifecycle, making custom_sparql the appropriate tool for lineage and source-of questions.

SPARQL:
```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?dataset
WHERE {
  ?process ml:executes ?model .
  ?process ml:hasDataInput ?dataset .
}
LIMIT 100
```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1916`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
Which datasets are consumed by processes that execute a machine learning model?
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {},
  "use_inference": false,
  "reasoning": "The question asks for a lineage or provenance relationship: identifying datasets that are consumed (used as input) by processes (pipelines/models). This requires tracing dependencies across the ML lifecycle, making custom_sparql the appropriate tool for lineage and source-of questions."
}
```
```

#### LLM Call 2
- Purpose: `sparql_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `5893`

Message 1 `system`:
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

Message 2 `user`:
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
  ml:AssociationRuleModel  # association rule model
  ml:ClusteringModel  # clustering model
  ml:ConfigurationSetting  # configuration variable setting
  ml:ConfigurationVariable  # configuration variable
  ml:ConfigurationVariableSet  # configuration variable set
  ml:DataProcessingOperation  # data processing operation
  ml:DataProcessingPipeline  # data processing pipeline
  ml:DecisionTreeModel  # decision tree model
  ml:DeployedMachineLearningModelState  # deployed machine learning model state
  ml:DimensionalityReductionModel  # dimensionality reduction model
  ml:EncodedAlgorithmCharacteristic  # encoded algorithm characteristic
  ml:EncodedMachineLearningTrainingAlgorithm  # encoded machine learning training algorithm
  ml:GroupOfMachineLearningModels  # group of machine learning models
  ml:InitialMachineLearningParameterSetting  # initial machine learning parameter setting
  ml:InitialMachineLearningParameterSettingSet  # initial machine learning parameter setting set
  ml:InstanceBasedModel  # instance-based model
  ml:LinearModel  # linear model
  ml:MachineLearningDataPreparationPipeline  # machine learning data preparation pipeline
  ml:MachineLearningDataSet  # machine learning data set
  ml:MachineLearningDataSetPartitioning  # machine learning data set partitioning
  ml:MachineLearningFramework  # machine learning framework
  ml:MachineLearningModel  # machine learning model
  ml:MachineLearningModelAlgorithm  # machine learning model algorithm
  ml:MachineLearningModelComponent  # machine learning model component
  ml:MachineLearningModelDeploymentProcess  # machine learning model deployment process
  ml:MachineLearningModelDevelopmentPipeline  # machine learning model development pipeline
  ml:MachineLearningModelUpdate  # machine learning model update
  ml:MachineLearningParameter  # machine learning parameter
  ml:MachineLearningParameterInitialization  # machine learning parameter initialization
  ml:MachineLearningParameterSet  # machine learning parameter set
  ml:MachineLearningParameterSetting  # machine learning parameter setting
  ml:MachineLearningParameterSettingSet  # machine learning parameter setting set
  ml:MachineLearningSampleIdentifier  # feature vector identifier
  ml:MachineLearningTraining  # machine learning training
  ml:MachineLearningTrainingAlgorithm  # machine learning training algorithm
  ml:ModelAssumptions  # model assumptions
  ml:ModelCharacteristic  # model characteristic
  ml:ModelEvaluation  # model evaluation
  ml:ModelExecution  # model execution
  ml:ModelExecutionObjective  # model execution objective
  ml:ModelInputRequirementSpecification  # model input requirements
  ml:ModelOutput  # model output
  ml:ModelOutputDataSet  # model output data set
  ml:ModelOutputTransformationAlgorithm  # model output transformation algorithm
  ml:ModelOutputTransformationOperation  # model output transformation operation
  ml:ModelPerformanceAssessment  # model performance assessment
  ml:ModelPerformanceMonitoring  # model performance monitoring
  ml:ModelPerformanceResult  # model performance result
  ml:ModelSelection  # model selection
  ml:ModelValidation  # model validation
  ml:NonParametricModel  # non-parametric model
  ml:PolynomialModel  # polynomial model
  ml:PolynomialModelTrainingAlgorithm  # polynomial model training algorithm
  ml:ProductionMachineLearningDataSet  # production machine learning data set
  ml:ReinforcementLearning  # reinforcement learning
  ml:SemiSupervisedLearning  # semi supervised learning
  ml:SupervisedLearning  # supervised learning
  ml:SupportVectorMachine  # support vector machine
  ml:UnsupervisedLearning  # unsupervised learning

=== OBJECT PROPERTIES ===

=== DATATYPE PROPERTIES ===


=== EXAMPLE QUERIES ===

Generate a SPARQL SELECT query to answer the question. Use ONLY the listed classes, properties, individuals, and prefixes.
```

Response text:
```text
SELECT DISTINCT ?dataset
WHERE {
  ?process ml:executes ?model .
  ?process ml:hasDataInput ?dataset .
}
LIMIT 100
```

#### LLM Call 3
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `2024`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: Which datasets are consumed by processes that execute a machine learning model?

Filtered results:
[
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset1"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset10"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset11"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset12"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset13"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset14"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset15"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset2"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset20"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset21"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset22"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset23"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset24"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset25"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset3"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset4"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset5"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset6"
  },
  {
    "dataset": "http://example.com/BioOps#BatchReleaseProductionData_2025Q4"
  },
  {
    "dataset": "http://example.com/BioOps#BatchReleaseTestData"
  }
]

Planned steps:
[]

Execution steps:
[
  {
    "tool": "custom_sparql",
    "params": {},
    "result_count": 29
  }
]
```

Response text:
```text
The following datasets are consumed by processes that execute machine learning models:

**From the MNIST Domain:**
*   `http://example.com/MNIST#PreprocessedDataset1` through `http://example.com/MNIST#PreprocessedDataset6`
*   `http://example.com/MNIST#PreprocessedDataset2` through `http://example.com/MNIST#PreprocessedDataset5` (Note: This range includes the datasets listed above, but also covers 7-10)
*   `http://example.com/MNIST#PreprocessedDataset10`
*   `http://example.com/MNIST#PreprocessedDataset11`
*   `http://example.com/MNIST#PreprocessedDataset12`
*   `http://example.com/MNIST#PreprocessedDataset13`
*   `http://example.com/MNIST#PreprocessedDataset14`
*   `http://example.com/MNIST#PreprocessedDataset15`
*   `http://example.com/MNIST#PreprocessedDataset20` through `http://example.com/MNIST#PreprocessedDataset25`

**From the BioOps Domain:**
*   `http://example.com/BioOps#BatchReleaseProductionData_2025Q4`
*   `http://example.com/BioOps#BatchReleaseTestData`
```

### Final SPARQL
```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?dataset
WHERE {
  ?process ml:executes ?model .
  ?process ml:hasDataInput ?dataset .
}
LIMIT 100
```

### Result Preview
```json
[{'dataset': 'http://example.com/MNIST#PreprocessedDataset1'}, {'dataset': 'http://example.com/MNIST#PreprocessedDataset10'}, {'dataset': 'http://example.com/MNIST#PreprocessedDataset11'}, {'dataset': 'http://example.com/MNIST#PreprocessedDataset12'}, {'dataset': 'http://example.com/MNIST#PreprocessedDataset13'}]
```

## 3. Which datasets are produced by processes that also use a model output?
- Started: `2026-04-13T20:28:19.592311+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `80`
- Intent reasoning: This is a complex lineage and provenance question ('produced by processes that also use a model output'). Custom SPARQL is the designated tool for tracing dependencies (lineage/provenance), and setting use_inference=false ensures the query focuses on structured data relationships rather than conceptual interpretation.
- Result keys: `dataset`

### Executed Steps

#### Step 1: `custom_sparql`
- Params: `{}`
- Result count: `80`
- Reasoning: This is a complex lineage and provenance question ('produced by processes that also use a model output'). Custom SPARQL is the designated tool for tracing dependencies (lineage/provenance), and setting use_inference=false ensures the query focuses on structured data relationships rather than conceptual interpretation.

SPARQL:
```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?dataset
WHERE {
    # Find a Model Output that generates an input dataset
    ?modelOutput ml:hasDataOutput ?inputDataset .

    # Find an ML Process that consumes this model output data as input
    ?process ml:hasDataInput ?inputDataset .

    # Ensure the same process also produces a final dataset (the target)
    ?process ml:hasDataOutput ?dataset .
}
LIMIT 100
```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1907`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
Which datasets are produced by processes that also use a model output?
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {},
  "use_inference": false,
  "reasoning": "This is a complex lineage and provenance question ('produced by processes that also use a model output'). Custom SPARQL is the designated tool for tracing dependencies (lineage/provenance), and setting use_inference=false ensures the query focuses on structured data relationships rather than conceptual interpretation."
}
```
```

#### LLM Call 2
- Purpose: `sparql_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `4236`

Message 1 `system`:
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

Message 2 `user`:
```text
User question: Which datasets are produced by processes that also use a model output?

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
  ml:AssociationRuleModel  # association rule model
  ml:ClusteringModel  # clustering model
  ml:DataProcessingOperation  # data processing operation
  ml:DecisionTreeModel  # decision tree model
  ml:DeployedMachineLearningModelState  # deployed machine learning model state
  ml:DimensionalityReductionModel  # dimensionality reduction model
  ml:EncodedAlgorithmCharacteristic  # encoded algorithm characteristic
  ml:InstanceBasedModel  # instance-based model
  ml:LinearModel  # linear model
  ml:MachineLearningModel  # machine learning model
  ml:MachineLearningModelAlgorithm  # machine learning model algorithm
  ml:MachineLearningModelComponent  # machine learning model component
  ml:MachineLearningModelDeploymentProcess  # machine learning model deployment process
  ml:MachineLearningModelDevelopmentPipeline  # machine learning model development pipeline
  ml:MachineLearningModelUpdate  # machine learning model update
  ml:MachineLearningTraining  # machine learning training
  ml:MachineLearningTrainingAlgorithm  # machine learning training algorithm
  ml:ModelAssumptions  # model assumptions
  ml:ModelCharacteristic  # model characteristic
  ml:ModelEvaluation  # model evaluation
  ml:ModelExecution  # model execution
  ml:ModelExecutionObjective  # model execution objective
  ml:ModelInputRequirementSpecification  # model input requirements
  ml:ModelOutput  # model output
  ml:ModelOutputDataSet  # model output data set
  ml:ModelOutputTransformationAlgorithm  # model output transformation algorithm
  ml:ModelOutputTransformationOperation  # model output transformation operation
  ml:ModelPerformanceAssessment  # model performance assessment
  ml:ModelPerformanceMonitoring  # model performance monitoring
  ml:ModelPerformanceResult  # model performance result
  ml:ModelSelection  # model selection
  ml:ModelValidation  # model validation
  ml:NonParametricModel  # non-parametric model
  ml:PolynomialModel  # polynomial model
  ml:PolynomialModelTrainingAlgorithm  # polynomial model training algorithm

=== OBJECT PROPERTIES ===
  ml:dataOutputOf domain=<node1466>
  ml:hasDataOutput range=<node1472>

=== DATATYPE PROPERTIES ===


=== EXAMPLE QUERIES ===

Generate a SPARQL SELECT query to answer the question. Use ONLY the listed classes, properties, individuals, and prefixes.
```

Response text:
```text
SELECT DISTINCT ?dataset
WHERE {
    # Find a Model Output that generates an input dataset
    ?modelOutput ml:hasDataOutput ?inputDataset .

    # Find an ML Process that consumes this model output data as input
    ?process ml:hasDataInput ?inputDataset .

    # Ensure the same process also produces a final dataset (the target)
    ?process ml:hasDataOutput ?dataset .
}
LIMIT 100
```

#### LLM Call 3
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1945`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: Which datasets are produced by processes that also use a model output?

Filtered results:
[
  {
    "dataset": "http://example.com/MNIST#EvaluationResult1"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult10"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult11"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult12"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult13"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult14"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult15"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult2"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult20"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult21"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult22"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult23"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult24"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult25"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult3"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult4"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult5"
  },
  {
    "dataset": "http://example.com/MNIST#EvaluationResult6"
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset1"
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset10"
  }
]

Planned steps:
[]

Execution steps:
[
  {
    "tool": "custom_sparql",
    "params": {},
    "result_count": 80
  }
]
```

Response text:
```text
The datasets produced by processes that also use a model output are:

*   `http://example.com/MNIST#EvaluationResult1`
*   `http://example.com/MNIST#EvaluationResult2`
*   `http://example.com/MNIST#EvaluationResult3`
*   `http://example.com/MNIST#EvaluationResult4`
*   `http://example.com/MNIST#EvaluationResult5`
*   `http://example.com/MNIST#EvaluationResult6`
*   `http://example.com/MNIST#EvaluationResult10`
*   `http://example.com/MNIST#EvaluationResult11`
*   `http://example.com/MNIST#EvaluationResult12`
*   `http://example.com/MNIST#EvaluationResult13`
*   `http://example.com/MNIST#EvaluationResult14`
*   `http://example.com/MNIST#EvaluationResult15`
*   `http://example.com/MNIST#EvaluationResult20`
*   `http://example.com/MNIST#EvaluationResult21`
*   `http://example.com/MNIST#EvaluationResult22`
*   `http://example.com/MNIST#EvaluationResult23`
*   `http://example.com/MNIST#EvaluationResult24`
*   `http://example.com/MNIST#EvaluationResult25`
*   `http://example.com/MNIST#ModelOutputDataset1`
*   `http://example.com/MNIST#ModelOutputDataset10`
```

### Final SPARQL
```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?dataset
WHERE {
    # Find a Model Output that generates an input dataset
    ?modelOutput ml:hasDataOutput ?inputDataset .

    # Find an ML Process that consumes this model output data as input
    ?process ml:hasDataInput ?inputDataset .

    # Ensure the same process also produces a final dataset (the target)
    ?process ml:hasDataOutput ?dataset .
}
LIMIT 100
```

### Result Preview
```json
[{'dataset': 'http://example.com/MNIST#EvaluationResult1'}, {'dataset': 'http://example.com/MNIST#EvaluationResult10'}, {'dataset': 'http://example.com/MNIST#EvaluationResult11'}, {'dataset': 'http://example.com/MNIST#EvaluationResult12'}, {'dataset': 'http://example.com/MNIST#EvaluationResult13'}]
```

## 4. Which models and pipelines share the same dataset?
- Started: `2026-04-13T20:28:56.889259+00:00`
- Intent tool: `custom_sparql`
- Inference used: `True`
- Result count: `100`
- Intent reasoning: The user is asking for a complex relationship query: finding common datasets shared by two distinct types of assets (models and pipelines). This requires traversing the graph structure to identify co-occurring resources, which is best handled by custom SPARQL queries designed for lineage and relationship discovery.
- Result keys: `dataset, model, pipeline`

### Executed Steps

#### Step 1: `custom_sparql`
- Params: `{}`
- Result count: `100`
- Reasoning: The user is asking for a complex relationship query: finding common datasets shared by two distinct types of assets (models and pipelines). This requires traversing the graph structure to identify co-occurring resources, which is best handled by custom SPARQL queries designed for lineage and relationship discovery.

SPARQL:
```sparql
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?dataset ?model ?pipeline
WHERE {
    # 1. Find an ML Process using a specific Dataset (D)
    ?process ml:hasDataInput | ml:hasDataOutput ?dataset .

    # 2. Link this process to an associated Model (M)
    ?process ml:executes | bfo:BFO_0000057 ?model .

    # 3. Optionally link the same Dataset (D) usage to a Pipeline (PL) via a component (C)
    OPTIONAL {
        ?pipeline bfo:BFO_0000117 ?component .
        # Check if the component uses the shared dataset D
        ?component ml:hasDataInput | ml:hasDataOutput ?dataset .
    }

    # Ensure that at least one model or pipeline was successfully linked to this dataset usage.
    FILTER(BOUND(?model) || BOUND(?pipeline))
}
LIMIT 100
```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1887`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
Which models and pipelines share the same dataset?
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {},
  "use_inference": true,
  "reasoning": "The user is asking for a complex relationship query: finding common datasets shared by two distinct types of assets (models and pipelines). This requires traversing the graph structure to identify co-occurring resources, which is best handled by custom SPARQL queries designed for lineage and relationship discovery."
}
```
```

#### LLM Call 2
- Purpose: `sparql_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `2672`

Message 1 `system`:
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

Message 2 `user`:
```text
User question: Which models and pipelines share the same dataset?

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
  ml:GroupOfMachineLearningModels  # group of machine learning models

=== OBJECT PROPERTIES ===

=== DATATYPE PROPERTIES ===

=== NAMED INDIVIDUALS ===
  <http://example.com/BioOps#BatchReleaseCandidateModels> type=ml:GroupOfMachineLearningModels
  <http://example.com/MNIST#DatasetCharacteristic1> type=ml:GaussianNoise
  <http://example.com/MNIST#DatasetCharacteristic2> type=ml:GaussianNoise
  <http://example.com/MNIST#DatasetCharacteristic3> type=ml:GaussianNoise
  <http://example.com/MNIST#DatasetCharacteristic5> type=ml:PoissonNoise
  <http://example.com/MNIST#DatasetCharacteristic6> type=ml:PoissonNoise
  <http://example.com/MNIST#DatasetCharacteristic7> type=ml:GaussianNoise

=== EXAMPLE QUERIES ===

Generate a SPARQL SELECT query to answer the question. Use ONLY the listed classes, properties, individuals, and prefixes.
```

Response text:
```text
SELECT DISTINCT ?dataset ?model ?pipeline
WHERE {
    # 1. Find an ML Process using a specific Dataset (D)
    ?process ml:hasDataInput | ml:hasDataOutput ?dataset .

    # 2. Link this process to an associated Model (M)
    ?process ml:executes | bfo:BFO_0000057 ?model .

    # 3. Optionally link the same Dataset (D) usage to a Pipeline (PL) via a component (C)
    OPTIONAL {
        ?pipeline bfo:BFO_0000117 ?component .
        # Check if the component uses the shared dataset D
        ?component ml:hasDataInput | ml:hasDataOutput ?dataset .
    }

    # Ensure we only return results where at least one model or pipeline was successfully linked to this dataset usage.
    FILTER(BOUND(?model)) || FILTER(BOUND(?pipeline))
}
LIMIT 100
```

#### LLM Call 3
- Purpose: `sparql_repair_execution`
- Model: `google/gemma-4-e4b`
- Prompt chars: `3163`

Message 1 `system`:
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

Message 2 `assistant`:
```text
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?dataset ?model ?pipeline
WHERE {
    # 1. Find an ML Process using a specific Dataset (D)
    ?process ml:hasDataInput | ml:hasDataOutput ?dataset .

    # 2. Link this process to an associated Model (M)
    ?process ml:executes | bfo:BFO_0000057 ?model .

    # 3. Optionally link the same Dataset (D) usage to a Pipeline (PL) via a component (C)
    OPTIONAL {
        ?pipeline bfo:BFO_0000117 ?component .
        # Check if the component uses the shared dataset D
        ?component ml:hasDataInput | ml:hasDataOutput ?dataset .
    }

    # Ensure we only return results where at least one model or pipeline was successfully linked to this dataset usage.
    FILTER(BOUND(?model)) || FILTER(BOUND(?pipeline))
}
LIMIT 100
```

Message 3 `user`:
```text
The previous SPARQL was invalid for this ontology or could not be parsed. Fix it strictly using the provided ontology vocabulary and return ONLY corrected SPARQL.

Execution error:
GraphDB Error 400: MALFORMED QUERY: Encountered " "||" "|| "" at line 19, column 27.
Was expecting one of:
    "(" ...
    "{" ...
    "}" ...
    "[" ...
    "." ...
    <NIL> ...
    <ANON> ...
    "optional" ...
    "graph" ...
    "minus" ...
    "filter" ...
    "true" ...
    "false" ...
    "bind" ...
    "service" ...
    "values" ...
    <Q_IRI_REF> ...
    <PNAME_NS> ...
    <PNAME_LN> ...
    <BLANK_NODE_LABEL> ...
    <VAR1> ...
    <VAR2> ...
    <INTEGER> ...
    <INTEGER_POSITIVE> ...
    <INTEGER_NEGATIVE> ...
    <DECIMAL> ...
    <DECIMAL_POSITIVE> ...
    <DECIMAL_NEGATIVE> ...
    <DOUBLE> ...
    <DOUBLE_POSITIVE> ...
    <DOUBLE_NEGATIVE> ...
    <STRING_LITERAL1> ...
    <STRING_LITERAL2> ...
    <STRING_LITERAL_LONG1> ...
    <STRING_LITERAL_LONG2> ...
    "<<" ...
    
```

Response text:
```text
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?dataset ?model ?pipeline
WHERE {
    # 1. Find an ML Process using a specific Dataset (D)
    ?process ml:hasDataInput | ml:hasDataOutput ?dataset .

    # 2. Link this process to an associated Model (M)
    ?process ml:executes | bfo:BFO_0000057 ?model .

    # 3. Optionally link the same Dataset (D) usage to a Pipeline (PL) via a component (C)
    OPTIONAL {
        ?pipeline bfo:BFO_0000117 ?component .
        # Check if the component uses the shared dataset D
        ?component ml:hasDataInput | ml:hasDataOutput ?dataset .
    }

    # Ensure that at least one model or pipeline was successfully linked to this dataset usage.
    FILTER(BOUND(?model) || BOUND(?pipeline))
}
LIMIT 100
```

#### LLM Call 4
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `3527`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: Which models and pipelines share the same dataset?

Filtered results:
[
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "model": "http://example.com/MNIST#MLModel1",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset1",
    "model": "http://example.com/MNIST#MLModel1",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset10",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": "http://example.com/MNIST-lifecycle#MNISTModelSelection2025"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset11",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset11",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset12",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset12",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset13",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset13",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset14",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset14",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset15",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset15",
    "model": "http://example.com/MNIST#MLModel2",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset2",
    "model": "http://example.com/MNIST#MLModel1",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset2",
    "model": "http://example.com/MNIST#MLModel1",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "model": "http://example.com/MNIST#MLModel3",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset20",
    "model": "http://example.com/MNIST#MLModel3",
    "pipeline": "http://example.com/MNIST-lifecycle#MNISTModelSelection2025"
  },
  {
    "dataset": "http://example.com/MNIST#PreprocessedDataset21",
    "model": "http://example.com/MNIST#MLModel3",
    "pipeline": null
  },
  {
    "dataset": "http://example.com/MNIST#ModelOutputDataset21",
    "model": "http://example.com/MNIST#MLModel3",
    "pipeline": null
  }
]

Planned steps:
[]

Execution steps:
[
  {
    "tool": "custom_sparql",
    "params": {},
    "result_count": 100
  }
]
```

Response text:
```text
The following table summarizes which models and pipelines are associated with specific datasets:

| Dataset URI | Associated Model | Associated Pipeline |
| :--- | :--- | :--- |
| `http://example.com/MNIST#PreprocessedDataset1` | `http://example.com/MNIST#MLModel1` | None |
| `http://example.com/MNIST#ModelOutputDataset1` | `http://example.com/MNIST#MLModel1` | None |
| `http://example.com/MNIST#PreprocessedDataset10` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#ModelOutputDataset10` | `http://example.com/MNIST#MLModel2` | `http://example.com/MNIST-lifecycle#MNISTModelSelection2025` |
| `http://example.com/MNIST#PreprocessedDataset11` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#ModelOutputDataset11` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#PreprocessedDataset12` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#ModelOutputDataset12` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#PreprocessedDataset13` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#ModelOutputDataset13` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#PreprocessedDataset14` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#ModelOutputDataset14` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#PreprocessedDataset15` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#ModelOutputDataset15` | `http://example.com/MNIST#MLModel2` | None |
| `http://example.com/MNIST#PreprocessedDataset2` | `http://example.com/MNIST#MLModel1` | None |
| `http://example.com/MNIST#ModelOutputDataset2` | `http://example.com/MNIST#MLModel1` | None |
| `http://example.com/MNIST#PreprocessedDataset20` | `http://example.com/MNIST#MLModel3` | None |
| `http://example.com/MNIST#ModelOutputDataset20` | `http://example.com/MNIST#MLModel3` | `http://example.com/MNIST-lifecycle#MNISTModelSelection2025` |
| `http://example.com/MNIST#PreprocessedDataset21` | `http://example.com/MNIST#MLModel3` | None |
| `http://example.com/MNIST#ModelOutputDataset21` | `http://example.com/MNIST#MLModel3` | None |

***

**Summary of Shared Components:**

*   **Models:** The models (`http://example.com/MNIST#MLModel1`, `http://example.com/MNIST#MLModel2`, and `http://example.com/MNIST#MLModel3`) are used across multiple datasets.
*   **Pipelines:** The pipeline `http://example.com/MNIST-lifecycle#MNISTModelSelection2025` is associated with two different output datasets (`...Dataset10` and `...Dataset20`).
```

### Final SPARQL
```sparql
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?dataset ?model ?pipeline
WHERE {
    # 1. Find an ML Process using a specific Dataset (D)
    ?process ml:hasDataInput | ml:hasDataOutput ?dataset .

    # 2. Link this process to an associated Model (M)
    ?process ml:executes | bfo:BFO_0000057 ?model .

    # 3. Optionally link the same Dataset (D) usage to a Pipeline (PL) via a component (C)
    OPTIONAL {
        ?pipeline bfo:BFO_0000117 ?component .
        # Check if the component uses the shared dataset D
        ?component ml:hasDataInput | ml:hasDataOutput ?dataset .
    }

    # Ensure that at least one model or pipeline was successfully linked to this dataset usage.
    FILTER(BOUND(?model) || BOUND(?pipeline))
}
LIMIT 100
```

### Result Preview
```json
[{'dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'model': 'http://example.com/MNIST#MLModel1', 'pipeline': None}, {'dataset': 'http://example.com/MNIST#ModelOutputDataset1', 'model': 'http://example.com/MNIST#MLModel1', 'pipeline': None}, {'dataset': 'http://example.com/MNIST#PreprocessedDataset10', 'model': 'http://example.com/MNIST#MLModel2', 'pipeline': None}, {'dataset': 'http://example.com/MNIST#ModelOutputDataset10', 'model': 'http://example.com/MNIST#MLModel2', 'pipeline': 'http://example.com/MNIST-lifecycle#MNISTModelSelection2025'}, {'dataset': 'http://example.com/MNIST#PreprocessedDataset11', 'model': 'http://example.com/MNIST#MLModel2', 'pipeline': None}]
```

## 5. Which model outputs are later used as inputs to another process?
- Started: `2026-04-13T20:30:38.172968+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `74`
- Intent reasoning: This is a lineage/provenance question asking how the output of one component (model) serves as the input for another process. Custom SPARQL is best suited for tracing data flow and relationships like 'used to make' or 'derived from', which describes model outputs feeding into subsequent processes.
- Result keys: `output_dataset`

### Executed Steps

#### Step 1: `custom_sparql`
- Params: `{}`
- Result count: `74`
- Reasoning: This is a lineage/provenance question asking how the output of one component (model) serves as the input for another process. Custom SPARQL is best suited for tracing data flow and relationships like 'used to make' or 'derived from', which describes model outputs feeding into subsequent processes.

SPARQL:
```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?output_dataset
WHERE {
    # Find a dataset (?output_dataset) that is used as an input for some subsequent ML process.
    ?next_process ml:hasDataInput ?output_dataset .

    # Ensure this same dataset was generated as the output of a previous ML process/model execution.
    ?source_process ml:hasDataOutput ?output_dataset .
}
LIMIT 100
```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1901`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
Which model outputs are later used as inputs to another process?
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {},
  "use_inference": false,
  "reasoning": "This is a lineage/provenance question asking how the output of one component (model) serves as the input for another process. Custom SPARQL is best suited for tracing data flow and relationships like 'used to make' or 'derived from', which describes model outputs feeding into subsequent processes."
}
```
```

#### LLM Call 2
- Purpose: `sparql_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `4220`

Message 1 `system`:
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

Message 2 `user`:
```text
User question: Which model outputs are later used as inputs to another process?

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
  ml:AssociationRuleModel  # association rule model
  ml:ClusteringModel  # clustering model
  ml:DataProcessingOperation  # data processing operation
  ml:DecisionTreeModel  # decision tree model
  ml:DeployedMachineLearningModelState  # deployed machine learning model state
  ml:DimensionalityReductionModel  # dimensionality reduction model
  ml:EncodedAlgorithmCharacteristic  # encoded algorithm characteristic
  ml:GaussianProcessRegression  # gaussian process regression
  ml:InstanceBasedModel  # instance-based model
  ml:LinearModel  # linear model
  ml:MachineLearningModel  # machine learning model
  ml:MachineLearningModelAlgorithm  # machine learning model algorithm
  ml:MachineLearningModelComponent  # machine learning model component
  ml:MachineLearningModelDeploymentProcess  # machine learning model deployment process
  ml:MachineLearningModelDevelopmentPipeline  # machine learning model development pipeline
  ml:MachineLearningModelUpdate  # machine learning model update
  ml:MachineLearningTraining  # machine learning training
  ml:MachineLearningTrainingAlgorithm  # machine learning training algorithm
  ml:ModelAssumptions  # model assumptions
  ml:ModelCharacteristic  # model characteristic
  ml:ModelEvaluation  # model evaluation
  ml:ModelExecution  # model execution
  ml:ModelExecutionObjective  # model execution objective
  ml:ModelInputRequirementSpecification  # model input requirements
  ml:ModelOutput  # model output
  ml:ModelOutputDataSet  # model output data set
  ml:ModelOutputTransformationAlgorithm  # model output transformation algorithm
  ml:ModelOutputTransformationOperation  # model output transformation operation
  ml:ModelPerformanceAssessment  # model performance assessment
  ml:ModelPerformanceMonitoring  # model performance monitoring
  ml:ModelPerformanceResult  # model performance result
  ml:ModelSelection  # model selection
  ml:ModelValidation  # model validation
  ml:NonParametricModel  # non-parametric model
  ml:PolynomialModel  # polynomial model
  ml:PolynomialModelTrainingAlgorithm  # polynomial model training algorithm

=== OBJECT PROPERTIES ===

=== DATATYPE PROPERTIES ===


=== EXAMPLE QUERIES ===

Generate a SPARQL SELECT query to answer the question. Use ONLY the listed classes, properties, individuals, and prefixes.
```

Response text:
```text
SELECT DISTINCT ?output_dataset
WHERE {
    # Find a dataset (?output_dataset) that is used as an input for some subsequent ML process.
    ?next_process ml:hasDataInput ?output_dataset .

    # Ensure this same dataset was generated as the output of a previous ML process/model execution.
    ?source_process ml:hasDataOutput ?output_dataset .
}
LIMIT 100
```

#### LLM Call 3
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `2117`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: Which model outputs are later used as inputs to another process?

Filtered results:
[
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset1"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset10"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset11"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset12"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset13"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset14"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset15"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset2"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset20"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset21"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset22"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset23"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset24"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset25"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset3"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset4"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset5"
  },
  {
    "output_dataset": "http://example.com/MNIST#ModelOutputDataset6"
  },
  {
    "output_dataset": "http://example.com/MNIST#PreprocessedDataset1"
  },
  {
    "output_dataset": "http://example.com/MNIST#PreprocessedDataset10"
  }
]

Planned steps:
[]

Execution steps:
[
  {
    "tool": "custom_sparql",
    "params": {},
    "result_count": 74
  }
]
```

Response text:
```text
Multiple model outputs were found that are subsequently used as inputs for other processes. These include:

*   **Model Outputs:** A large number of specific model output datasets, such as `http://example.com/MNIST#ModelOutputDataset1`, `...#ModelOutputDataset25`, and others (e.g., Dataset 10, 11, 12, etc.).
*   **Preprocessed Data:** Outputs that have undergone preprocessing steps, including `http://example.com/MNIST#PreprocessedDataset1` and `...#PreprocessedDataset10`.

In total, the query identified connections involving at least 25 distinct model output datasets.
```

### Final SPARQL
```sparql
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT ?output_dataset
WHERE {
    # Find a dataset (?output_dataset) that is used as an input for some subsequent ML process.
    ?next_process ml:hasDataInput ?output_dataset .

    # Ensure this same dataset was generated as the output of a previous ML process/model execution.
    ?source_process ml:hasDataOutput ?output_dataset .
}
LIMIT 100
```

### Result Preview
```json
[{'output_dataset': 'http://example.com/MNIST#ModelOutputDataset1'}, {'output_dataset': 'http://example.com/MNIST#ModelOutputDataset10'}, {'output_dataset': 'http://example.com/MNIST#ModelOutputDataset11'}, {'output_dataset': 'http://example.com/MNIST#ModelOutputDataset12'}, {'output_dataset': 'http://example.com/MNIST#ModelOutputDataset13'}]
```

## 6. Which pipelines share a dataset with a model?
- Started: `2026-04-13T20:31:12.491247+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `0`
- Intent reasoning: This is a structural query requiring the traversal of multiple relationships (Pipeline -> Dataset and Model -> Dataset) to find pipelines that share a dataset with any model. Custom SPARQL is necessary for defining this specific graph pattern.

### Executed Steps

#### Step 1: `custom_sparql`
- Params: `{'query': 'SELECT DISTINCT ?pipelineName WHERE { \n  ?pipeline a :Pipeline ; \n            rdfs:label ?pipelineName . \n  ?pipeline :usesDataset ?dataset . \n  ?model a :Model ; \n         :usesDataset ?dataset . \n} LIMIT 10'}`
- Result count: `0`
- Reasoning: This is a structural query requiring the traversal of multiple relationships (Pipeline -> Dataset and Model -> Dataset) to find pipelines that share a dataset with any model. Custom SPARQL is necessary for defining this specific graph pattern.

SPARQL:
```sparql
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?pipeline ?dataset ?model
WHERE {
  # 1. Identify the Model (must be part of a Pipeline)
  ?pipeline bfo:BFO_0000117 ?component .
  ?component rdf:type ml:MachineLearningModel ;
             rdfs:label ?modelLabel .
  BIND(?component AS ?model)

  # 2. Identify the ML Process that uses this Model
  ?mlProcess (ml:executes | bfo:BFO_0000057) ?model .

  # 3. Link the ML Process to a Dataset Input or Output
  ?mlProcess (ml:hasDataInput | ml:hasDataOutput) ?dataset .
}
LIMIT 100
```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1882`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
Which pipelines share a dataset with a model?
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {
    "query": "SELECT DISTINCT ?pipelineName WHERE { \n  ?pipeline a :Pipeline ; \n            rdfs:label ?pipelineName . \n  ?pipeline :usesDataset ?dataset . \n  ?model a :Model ; \n         :usesDataset ?dataset . \n} LIMIT 10"
  },
  "use_inference": false,
  "reasoning": "This is a structural query requiring the traversal of multiple relationships (Pipeline -> Dataset and Model -> Dataset) to find pipelines that share a dataset with any model. Custom SPARQL is necessary for defining this specific graph pattern."
}
```
```

#### LLM Call 2
- Purpose: `sparql_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `4139`

Message 1 `system`:
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

Message 2 `user`:
```text
User question: Which pipelines share a dataset with a model?

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
  ml:AssociationRuleModel  # association rule model
  ml:ClusteringModel  # clustering model
  ml:DataProcessingOperation  # data processing operation
  ml:DecisionTreeModel  # decision tree model
  ml:DeployedMachineLearningModelState  # deployed machine learning model state
  ml:DimensionalityReductionModel  # dimensionality reduction model
  ml:EncodedAlgorithmCharacteristic  # encoded algorithm characteristic
  ml:InstanceBasedModel  # instance-based model
  ml:LinearModel  # linear model
  ml:MachineLearningModel  # machine learning model
  ml:MachineLearningModelAlgorithm  # machine learning model algorithm
  ml:MachineLearningModelComponent  # machine learning model component
  ml:MachineLearningModelDeploymentProcess  # machine learning model deployment process
  ml:MachineLearningModelDevelopmentPipeline  # machine learning model development pipeline
  ml:MachineLearningModelUpdate  # machine learning model update
  ml:MachineLearningTraining  # machine learning training
  ml:MachineLearningTrainingAlgorithm  # machine learning training algorithm
  ml:ModelAssumptions  # model assumptions
  ml:ModelCharacteristic  # model characteristic
  ml:ModelEvaluation  # model evaluation
  ml:ModelExecution  # model execution
  ml:ModelExecutionObjective  # model execution objective
  ml:ModelInputRequirementSpecification  # model input requirements
  ml:ModelOutput  # model output
  ml:ModelOutputDataSet  # model output data set
  ml:ModelOutputTransformationAlgorithm  # model output transformation algorithm
  ml:ModelOutputTransformationOperation  # model output transformation operation
  ml:ModelPerformanceAssessment  # model performance assessment
  ml:ModelPerformanceMonitoring  # model performance monitoring
  ml:ModelPerformanceResult  # model performance result
  ml:ModelSelection  # model selection
  ml:ModelValidation  # model validation
  ml:NonParametricModel  # non-parametric model
  ml:PolynomialModel  # polynomial model
  ml:PolynomialModelTrainingAlgorithm  # polynomial model training algorithm

=== OBJECT PROPERTIES ===

=== DATATYPE PROPERTIES ===


=== EXAMPLE QUERIES ===

Generate a SPARQL SELECT query to answer the question. Use ONLY the listed classes, properties, individuals, and prefixes.
```

Response text:
```text
SELECT DISTINCT ?pipeline ?dataset ?model
WHERE {
  # 1. Identify the Model (must be part of a Pipeline)
  ?pipeline bfo:BFO_0000117 ?component .
  ?component rdf:type ml:MachineLearningModel ;
             rdfs:label ?modelLabel .
  BIND(?component AS ?model)

  # 2. Identify the ML Process that uses this Model
  ?mlProcess (ml:executes | bfo:BFO_0000057) ?model .

  # 3. Link the ML Process to a Dataset Input or Output
  ?mlProcess (ml:hasDataInput | ml:hasDataOutput) ?dataset .
}
LIMIT 100
```

### Final SPARQL
```sparql
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?pipeline ?dataset ?model
WHERE {
  # 1. Identify the Model (must be part of a Pipeline)
  ?pipeline bfo:BFO_0000117 ?component .
  ?component rdf:type ml:MachineLearningModel ;
             rdfs:label ?modelLabel .
  BIND(?component AS ?model)

  # 2. Identify the ML Process that uses this Model
  ?mlProcess (ml:executes | bfo:BFO_0000057) ?model .

  # 3. Link the ML Process to a Dataset Input or Output
  ?mlProcess (ml:hasDataInput | ml:hasDataOutput) ?dataset .
}
LIMIT 100
```

## 7. What downstream artifacts use MnistG16?
- Started: `2026-04-13T20:31:47.733453+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `6`
- Intent reasoning: The question asks for 'downstream artifacts' using a specific artifact ('MnistG16'). This is a lineage/provenance tracing query, which requires custom_sparql and should use inference=false as it involves specific names.
- Result keys: `artifact, artifact_label, artifact_types, downstream_dataset, downstream_dataset_type, downstream_process, downstream_process_type`

### Planned Steps
- `resolve_artifact` with params `{'artifact_name': 'MnistG16'}`
  Reasoning: Resolve the named artifact to a graph node before tracing lineage.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 1, 'frontier': ['http://example.com/MNIST#MnistG16']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 2, 'frontier': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 3, 'frontier': ['http://example.com/MNIST#ModelOutputDataset1', 'http://example.com/MNIST#ModelOutputDataset10', 'http://example.com/MNIST#ModelOutputDataset20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 4, 'frontier': ['http://example.com/MNIST#EvaluationResult1', 'http://example.com/MNIST#EvaluationResult10', 'http://example.com/MNIST#EvaluationResult20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

### Executed Steps

#### Step 1: `resolve_artifact`
- Params: `{'artifact_name': 'MnistG16'}`
- Result count: `2`
- Reasoning: Resolve the named artifact to a graph node before tracing lineage.

SPARQL:
```sparql

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?node ?label ?type ?type_label WHERE {
  {
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    FILTER(LCASE(STR(?label)) = LCASE("MnistG16"))
  } UNION {
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("MnistG16"))
    BIND(STRAFTER(STR(?node), "#") AS ?label)
  }
  OPTIONAL {
    ?node rdf:type ?type .
    FILTER(!isBlank(?type))
    OPTIONAL { ?type rdfs:label ?type_label }
  }
  FILTER(!isBlank(?node))
}
LIMIT 50

```

#### Step 2: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 1, 'frontier': ['http://example.com/MNIST#MnistG16']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#MnistG16> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 3: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 2, 'frontier': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 4: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 3, 'frontier': ['http://example.com/MNIST#ModelOutputDataset1', 'http://example.com/MNIST#ModelOutputDataset10', 'http://example.com/MNIST#ModelOutputDataset20']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#ModelOutputDataset1> <http://example.com/MNIST#ModelOutputDataset10> <http://example.com/MNIST#ModelOutputDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 5: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 4, 'frontier': ['http://example.com/MNIST#EvaluationResult1', 'http://example.com/MNIST#EvaluationResult10', 'http://example.com/MNIST#EvaluationResult20']}`
- Result count: `0`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#EvaluationResult1> <http://example.com/MNIST#EvaluationResult10> <http://example.com/MNIST#EvaluationResult20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1876`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
What downstream artifacts use MnistG16?
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {
    "query": "Find all artifacts (models, pipelines, etc.) that use MnistG16 as an input or component.",
    "artifact_name": "MnistG16"
  },
  "use_inference": false,
  "reasoning": "The question asks for 'downstream artifacts' using a specific artifact ('MnistG16'). This is a lineage/provenance tracing query, which requires custom_sparql and should use inference=false as it involves specific names."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `5729`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: What downstream artifacts use MnistG16?

Filtered results:
[
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": "test data set"
  }
]

Planned steps:
[
  {
    "tool": "resolve_artifact",
    "params": {
      "artifact_name": "MnistG16"
    },
    "reasoning": "Resolve the named artifact to a graph node before tracing lineage."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 1,
      "frontier": [
        "http://example.com/MNIST#MnistG16"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 2,
      "frontier": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 3,
      "frontier": [
        "http://example.com/MNIST#ModelOutputDataset1",
        "http://example.com/MNIST#ModelOutputDataset10",
        "http://example.com/MNIST#ModelOutputDataset20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 4,
      "frontier": [
        "http://example.com/MNIST#EvaluationResult1",
        "http://example.com/MNIST#EvaluationResult10",
        "http://example.com/MNIST#EvaluationResult20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  }
]

Execution steps:
[
  {
    "tool": "resolve_artifact",
    "params": {
      "artifact_name": "MnistG16"
    },
    "result_count": 2
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 1,
      "frontier": [
        "http://example.com/MNIST#MnistG16"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 2,
      "frontier": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 3,
      "frontier": [
        "http://example.com/MNIST#ModelOutputDataset1",
        "http://example.com/MNIST#ModelOutputDataset10",
        "http://example.com/MNIST#ModelOutputDataset20"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 4,
      "frontier": [
        "http://example.com/MNIST#EvaluationResult1",
        "http://example.com/MNIST#EvaluationResult10",
        "http://example.com/MNIST#EvaluationResult20"
      ]
    },
    "result_count": 0
  }
]
```

Response text:
```text
The artifact **MnistG16** is used as input for three distinct preprocessing pipelines, resulting in several downstream datasets:

*   **Pipeline 1:**
    *   Uses `http://example.com/MNIST#PreprocessingPipeline1` to create two versions of the dataset: a full set (`http://example.com/MNIST#PreprocessedDataset1`) and a test set (also named `http://example.com/MNIST#PreprocessedDataset1`).

*   **Pipeline 2:**
    *   Uses `http://example.com/MNIST#PreprocessingPipeline10` to create two versions of the dataset: a full set (`http://example.com/MNIST#PreprocessedDataset10`) and a test set (also named `http://example.com/MNIST#PreprocessedDataset10`).

*   **Pipeline 3:**
    *   Uses `http://example.com/MNIST#PreprocessingPipeline20` to create two versions of the dataset: a full set (`http://example.com/MNIST#PreprocessedDataset20`) and a test set (also named `http://example.com/MNIST#PreprocessedDataset20`).
```

### Final SPARQL
```sparql
-- Step 1: resolve artifact

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?node ?label ?type ?type_label WHERE {
  {
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    FILTER(LCASE(STR(?label)) = LCASE("MnistG16"))
  } UNION {
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("MnistG16"))
    BIND(STRAFTER(STR(?node), "#") AS ?label)
  }
  OPTIONAL {
    ?node rdf:type ?type .
    FILTER(!isBlank(?type))
    OPTIONAL { ?type rdfs:label ?type_label }
  }
  FILTER(!isBlank(?node))
}
LIMIT 50


-- Step 2: lineage hop 1

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#MnistG16> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 3: lineage hop 2

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 4: lineage hop 3

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#ModelOutputDataset1> <http://example.com/MNIST#ModelOutputDataset10> <http://example.com/MNIST#ModelOutputDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 5: lineage hop 4

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#EvaluationResult1> <http://example.com/MNIST#EvaluationResult10> <http://example.com/MNIST#EvaluationResult20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

### Result Preview
```json
[{'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': None}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': 'test data set'}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline10', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset10', 'downstream_dataset_type': None}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline10', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset10', 'downstream_dataset_type': 'test data set'}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline20', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset20', 'downstream_dataset_type': None}]
```

## 8. What models use downstream artifacts of MnistG16?
- Started: `2026-04-13T20:32:11.554329+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `12`
- Intent reasoning: The question asks for models that use 'downstream artifacts' from a specific source ('MnistG16'). This is a classic lineage or provenance tracing query (source -> downstream consumer), which requires custom SPARQL and should be executed with inference disabled.
- Result keys: `artifact, artifact_label, artifact_types, downstream_dataset, downstream_dataset_type, downstream_process, downstream_process_type, model_dataset_role, model_name`

### Planned Steps
- `resolve_artifact` with params `{'artifact_name': 'MnistG16'}`
  Reasoning: Resolve the named artifact to a graph node before tracing lineage.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 1, 'frontier': ['http://example.com/MNIST#MnistG16']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 2, 'frontier': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 3, 'frontier': ['http://example.com/MNIST#ModelOutputDataset1', 'http://example.com/MNIST#ModelOutputDataset10', 'http://example.com/MNIST#ModelOutputDataset20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 4, 'frontier': ['http://example.com/MNIST#EvaluationResult1', 'http://example.com/MNIST#EvaluationResult10', 'http://example.com/MNIST#EvaluationResult20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `find_models_for_lineage_datasets` with params `{'dataset_kind': 'any'}`
  Reasoning: The question asks which models use the traced downstream datasets.

### Executed Steps

#### Step 1: `resolve_artifact`
- Params: `{'artifact_name': 'MnistG16'}`
- Result count: `2`
- Reasoning: Resolve the named artifact to a graph node before tracing lineage.

SPARQL:
```sparql

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?node ?label ?type ?type_label WHERE {
  {
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    FILTER(LCASE(STR(?label)) = LCASE("MnistG16"))
  } UNION {
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("MnistG16"))
    BIND(STRAFTER(STR(?node), "#") AS ?label)
  }
  OPTIONAL {
    ?node rdf:type ?type .
    FILTER(!isBlank(?type))
    OPTIONAL { ?type rdfs:label ?type_label }
  }
  FILTER(!isBlank(?node))
}
LIMIT 50

```

#### Step 2: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 1, 'frontier': ['http://example.com/MNIST#MnistG16']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#MnistG16> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 3: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 2, 'frontier': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 4: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 3, 'frontier': ['http://example.com/MNIST#ModelOutputDataset1', 'http://example.com/MNIST#ModelOutputDataset10', 'http://example.com/MNIST#ModelOutputDataset20']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#ModelOutputDataset1> <http://example.com/MNIST#ModelOutputDataset10> <http://example.com/MNIST#ModelOutputDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 5: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 4, 'frontier': ['http://example.com/MNIST#EvaluationResult1', 'http://example.com/MNIST#EvaluationResult10', 'http://example.com/MNIST#EvaluationResult20']}`
- Result count: `0`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#EvaluationResult1> <http://example.com/MNIST#EvaluationResult10> <http://example.com/MNIST#EvaluationResult20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 6: `find_models_for_lineage_datasets`
- Params: `{'datasets': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20'], 'dataset_kind': 'any'}`
- Result count: `6`
- Reasoning: The question asks which models use the traced downstream datasets.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?dataset ?dataset_role ?model_name WHERE {
    VALUES ?dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
    ?ml_process ml:hasDataInput ?dataset .
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    
    OPTIONAL {
        ?dataset rdf:type ?dataset_type .
        OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
    }

}
LIMIT 200

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1886`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
What models use downstream artifacts of MnistG16?
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {},
  "use_inference": false,
  "reasoning": "The question asks for models that use 'downstream artifacts' from a specific source ('MnistG16'). This is a classic lineage or provenance tracing query (source -> downstream consumer), which requires custom SPARQL and should be executed with inference disabled."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `9653`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: What models use downstream artifacts of MnistG16?

Filtered results:
[
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel3",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel3",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel3",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel3",
    "model_dataset_role": "test data set"
  }
]

Planned steps:
[
  {
    "tool": "resolve_artifact",
    "params": {
      "artifact_name": "MnistG16"
    },
    "reasoning": "Resolve the named artifact to a graph node before tracing lineage."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 1,
      "frontier": [
        "http://example.com/MNIST#MnistG16"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 2,
      "frontier": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 3,
      "frontier": [
        "http://example.com/MNIST#ModelOutputDataset1",
        "http://example.com/MNIST#ModelOutputDataset10",
        "http://example.com/MNIST#ModelOutputDataset20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 4,
      "frontier": [
        "http://example.com/MNIST#EvaluationResult1",
        "http://example.com/MNIST#EvaluationResult10",
        "http://example.com/MNIST#EvaluationResult20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "find_models_for_lineage_datasets",
    "params": {
      "dataset_kind": "any"
    },
    "reasoning": "The question asks which models use the traced downstream datasets."
  }
]

Execution steps:
[
  {
    "tool": "resolve_artifact",
    "params": {
      "artifact_name": "MnistG16"
    },
    "result_count": 2
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 1,
      "frontier": [
        "http://example.com/MNIST#MnistG16"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 2,
      "frontier": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 3,
      "frontier": [
        "http://example.com/MNIST#ModelOutputDataset1",
        "http://example.com/MNIST#ModelOutputDataset10",
        "http://example.com/MNIST#ModelOutputDataset20"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 4,
      "frontier": [
        "http://example.com/MNIST#EvaluationResult1",
        "http://example.com/MNIST#EvaluationResult10",
        "http://example.com/MNIST#EvaluationResult20"
      ]
    },
    "result_count": 0
  },
  {
    "tool": "find_models_for_lineage_datasets",
    "params": {
      "datasets": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ],
      "dataset_kind": "any"
    },
    "result_count": 6
  }
]
```

Response text:
```text
The following three models use `MnistG16` as an input artifact:

1.  **http://example.com/MNIST#MLModel1**
2.  **http://example.com/MNIST#MLModel2**
3.  **http://example.com/MNIST#MLModel3**
```

### Final SPARQL
```sparql
-- Step 1: resolve artifact

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?node ?label ?type ?type_label WHERE {
  {
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    FILTER(LCASE(STR(?label)) = LCASE("MnistG16"))
  } UNION {
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("MnistG16"))
    BIND(STRAFTER(STR(?node), "#") AS ?label)
  }
  OPTIONAL {
    ?node rdf:type ?type .
    FILTER(!isBlank(?type))
    OPTIONAL { ?type rdfs:label ?type_label }
  }
  FILTER(!isBlank(?node))
}
LIMIT 50


-- Step 2: lineage hop 1

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#MnistG16> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 3: lineage hop 2

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 4: lineage hop 3

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#ModelOutputDataset1> <http://example.com/MNIST#ModelOutputDataset10> <http://example.com/MNIST#ModelOutputDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 5: lineage hop 4

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#EvaluationResult1> <http://example.com/MNIST#EvaluationResult10> <http://example.com/MNIST#EvaluationResult20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 6: models for traced datasets

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?dataset ?dataset_role ?model_name WHERE {
    VALUES ?dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
    ?ml_process ml:hasDataInput ?dataset .
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    
    OPTIONAL {
        ?dataset rdf:type ?dataset_type .
        OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
    }

}
LIMIT 200

```

### Result Preview
```json
[{'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': None, 'model_name': 'http://example.com/MNIST#MLModel1', 'model_dataset_role': None}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': None, 'model_name': 'http://example.com/MNIST#MLModel1', 'model_dataset_role': 'test data set'}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': 'test data set', 'model_name': 'http://example.com/MNIST#MLModel1', 'model_dataset_role': None}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': 'test data set', 'model_name': 'http://example.com/MNIST#MLModel1', 'model_dataset_role': 'test data set'}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline10', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset10', 'downstream_dataset_type': None, 'model_name': 'http://example.com/MNIST#MLModel2', 'model_dataset_role': None}]
```

## 9. Which models use downstream artifacts of MnistG16?
- Started: `2026-04-13T20:32:34.085041+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `12`
- Intent reasoning: The question asks for models that use 'downstream artifacts' of a specific dataset/artifact (MnistG16). This is a classic lineage or provenance tracing query, which requires custom SPARQL and should not use inference.
- Result keys: `artifact, artifact_label, artifact_types, downstream_dataset, downstream_dataset_type, downstream_process, downstream_process_type, model_dataset_role, model_name`

### Planned Steps
- `resolve_artifact` with params `{'artifact_name': 'MnistG16'}`
  Reasoning: Resolve the named artifact to a graph node before tracing lineage.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 1, 'frontier': ['http://example.com/MNIST#MnistG16']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 2, 'frontier': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 3, 'frontier': ['http://example.com/MNIST#ModelOutputDataset1', 'http://example.com/MNIST#ModelOutputDataset10', 'http://example.com/MNIST#ModelOutputDataset20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 4, 'frontier': ['http://example.com/MNIST#EvaluationResult1', 'http://example.com/MNIST#EvaluationResult10', 'http://example.com/MNIST#EvaluationResult20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `find_models_for_lineage_datasets` with params `{'dataset_kind': 'any'}`
  Reasoning: The question asks which models use the traced downstream datasets.

### Executed Steps

#### Step 1: `resolve_artifact`
- Params: `{'artifact_name': 'MnistG16'}`
- Result count: `2`
- Reasoning: Resolve the named artifact to a graph node before tracing lineage.

SPARQL:
```sparql

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?node ?label ?type ?type_label WHERE {
  {
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    FILTER(LCASE(STR(?label)) = LCASE("MnistG16"))
  } UNION {
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("MnistG16"))
    BIND(STRAFTER(STR(?node), "#") AS ?label)
  }
  OPTIONAL {
    ?node rdf:type ?type .
    FILTER(!isBlank(?type))
    OPTIONAL { ?type rdfs:label ?type_label }
  }
  FILTER(!isBlank(?node))
}
LIMIT 50

```

#### Step 2: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 1, 'frontier': ['http://example.com/MNIST#MnistG16']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#MnistG16> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 3: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 2, 'frontier': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 4: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 3, 'frontier': ['http://example.com/MNIST#ModelOutputDataset1', 'http://example.com/MNIST#ModelOutputDataset10', 'http://example.com/MNIST#ModelOutputDataset20']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#ModelOutputDataset1> <http://example.com/MNIST#ModelOutputDataset10> <http://example.com/MNIST#ModelOutputDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 5: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 4, 'frontier': ['http://example.com/MNIST#EvaluationResult1', 'http://example.com/MNIST#EvaluationResult10', 'http://example.com/MNIST#EvaluationResult20']}`
- Result count: `0`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#EvaluationResult1> <http://example.com/MNIST#EvaluationResult10> <http://example.com/MNIST#EvaluationResult20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 6: `find_models_for_lineage_datasets`
- Params: `{'datasets': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20'], 'dataset_kind': 'any'}`
- Result count: `6`
- Reasoning: The question asks which models use the traced downstream datasets.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?dataset ?dataset_role ?model_name WHERE {
    VALUES ?dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
    ?ml_process ml:hasDataInput ?dataset .
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    
    OPTIONAL {
        ?dataset rdf:type ?dataset_type .
        OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
    }

}
LIMIT 200

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1887`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
Which models use downstream artifacts of MnistG16?
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {},
  "use_inference": false,
  "reasoning": "The question asks for models that use 'downstream artifacts' of a specific dataset/artifact (MnistG16). This is a classic lineage or provenance tracing query, which requires custom SPARQL and should not use inference."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `9654`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: Which models use downstream artifacts of MnistG16?

Filtered results:
[
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel3",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": null,
    "model_name": "http://example.com/MNIST#MLModel3",
    "model_dataset_role": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel3",
    "model_dataset_role": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": "test data set",
    "model_name": "http://example.com/MNIST#MLModel3",
    "model_dataset_role": "test data set"
  }
]

Planned steps:
[
  {
    "tool": "resolve_artifact",
    "params": {
      "artifact_name": "MnistG16"
    },
    "reasoning": "Resolve the named artifact to a graph node before tracing lineage."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 1,
      "frontier": [
        "http://example.com/MNIST#MnistG16"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 2,
      "frontier": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 3,
      "frontier": [
        "http://example.com/MNIST#ModelOutputDataset1",
        "http://example.com/MNIST#ModelOutputDataset10",
        "http://example.com/MNIST#ModelOutputDataset20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 4,
      "frontier": [
        "http://example.com/MNIST#EvaluationResult1",
        "http://example.com/MNIST#EvaluationResult10",
        "http://example.com/MNIST#EvaluationResult20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "find_models_for_lineage_datasets",
    "params": {
      "dataset_kind": "any"
    },
    "reasoning": "The question asks which models use the traced downstream datasets."
  }
]

Execution steps:
[
  {
    "tool": "resolve_artifact",
    "params": {
      "artifact_name": "MnistG16"
    },
    "result_count": 2
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 1,
      "frontier": [
        "http://example.com/MNIST#MnistG16"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 2,
      "frontier": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 3,
      "frontier": [
        "http://example.com/MNIST#ModelOutputDataset1",
        "http://example.com/MNIST#ModelOutputDataset10",
        "http://example.com/MNIST#ModelOutputDataset20"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 4,
      "frontier": [
        "http://example.com/MNIST#EvaluationResult1",
        "http://example.com/MNIST#EvaluationResult10",
        "http://example.com/MNIST#EvaluationResult20"
      ]
    },
    "result_count": 0
  },
  {
    "tool": "find_models_for_lineage_datasets",
    "params": {
      "datasets": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ],
      "dataset_kind": "any"
    },
    "result_count": 6
  }
]
```

Response text:
```text
The following models use downstream artifacts derived from **MnistG16**:

*   http://example.com/MNIST#MLModel1
*   http://example.com/MNIST#MLModel2
*   http://example.com/MNIST#MLModel3
```

### Final SPARQL
```sparql
-- Step 1: resolve artifact

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?node ?label ?type ?type_label WHERE {
  {
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    FILTER(LCASE(STR(?label)) = LCASE("MnistG16"))
  } UNION {
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("MnistG16"))
    BIND(STRAFTER(STR(?node), "#") AS ?label)
  }
  OPTIONAL {
    ?node rdf:type ?type .
    FILTER(!isBlank(?type))
    OPTIONAL { ?type rdfs:label ?type_label }
  }
  FILTER(!isBlank(?node))
}
LIMIT 50


-- Step 2: lineage hop 1

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#MnistG16> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 3: lineage hop 2

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 4: lineage hop 3

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#ModelOutputDataset1> <http://example.com/MNIST#ModelOutputDataset10> <http://example.com/MNIST#ModelOutputDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 5: lineage hop 4

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#EvaluationResult1> <http://example.com/MNIST#EvaluationResult10> <http://example.com/MNIST#EvaluationResult20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 6: models for traced datasets

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?dataset ?dataset_role ?model_name WHERE {
    VALUES ?dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
    ?ml_process ml:hasDataInput ?dataset .
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    
    OPTIONAL {
        ?dataset rdf:type ?dataset_type .
        OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
    }

}
LIMIT 200

```

### Result Preview
```json
[{'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': None, 'model_name': 'http://example.com/MNIST#MLModel1', 'model_dataset_role': None}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': None, 'model_name': 'http://example.com/MNIST#MLModel1', 'model_dataset_role': 'test data set'}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': 'test data set', 'model_name': 'http://example.com/MNIST#MLModel1', 'model_dataset_role': None}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': 'test data set', 'model_name': 'http://example.com/MNIST#MLModel1', 'model_dataset_role': 'test data set'}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline10', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset10', 'downstream_dataset_type': None, 'model_name': 'http://example.com/MNIST#MLModel2', 'model_dataset_role': None}]
```

## 10. Show me models their test dataset, and their pipeline that has performance more than 0.9
- Started: `2026-04-13T20:32:53.903148+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `6`
- Intent reasoning: The request requires filtering across multiple components (models, datasets, pipelines) based on a quantitative metric ('performance more than 0.9'). This involves complex lineage tracing and aggregation/metric-based querying, which necessitates the use of custom SPARQL.
- Result keys: `model_name, model_performance_metric, model_performance_value, pipelines, test_dataset_roles, test_datasets`

### Planned Steps
- `find_test_datasets_for_models` with params `{'dataset_kind': 'test'}`
  Reasoning: The question asks for related test-dataset context.
- `find_pipelines_for_models` with params `{}`
  Reasoning: The question asks for related pipeline context.

### Executed Steps

#### Step 1: `performance_filter`
- Params: `{'metric_label': 'classification accuracy', 'limit': 50, 'order': 'DESC', 'threshold_op': '>', 'threshold_value': '0.9'}`
- Result count: `21`
- Reasoning: Deterministic performance filter query.

SPARQL:
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
    ?model_performance_assessment ml:hasDataInput ?model_output .
    ?ml_process ml:hasDataOutput ?model_output .
    ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
    ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment .
    ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
    ?model_performance_metric_type rdfs:subClassOf* ml:PerformanceMetric .
    ?model_performance_metric_type rdfs:label ?model_performance_metric .
    ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
    FILTER(LCASE(STR(?model_performance_metric)) = "classification accuracy")
    FILTER(xsd:decimal(?model_performance_value) > 0.9)
    
}
ORDER BY DESC(xsd:decimal(?model_performance_value))
LIMIT 50

```

#### Step 2: `find_test_datasets_for_models`
- Params: `{'model_iris': ['http://example.com/BioOps#BatchReleaseLogReg', 'http://example.com/BioOps#BatchReleaseMLP', 'http://example.com/BioOps#BatchReleaseSVM', 'http://example.com/MNIST#MLModel1', 'http://example.com/MNIST#MLModel2', 'http://example.com/MNIST#MLModel3'], 'dataset_kind': 'test'}`
- Result count: `31`
- Reasoning: The question asks for related test-dataset context.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model_name ?dataset ?dataset_role WHERE {
    VALUES ?model_name { <http://example.com/BioOps#BatchReleaseLogReg> <http://example.com/BioOps#BatchReleaseMLP> <http://example.com/BioOps#BatchReleaseSVM> <http://example.com/MNIST#MLModel1> <http://example.com/MNIST#MLModel2> <http://example.com/MNIST#MLModel3> }
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?ml_process ml:hasDataInput ?dataset .
    ?dataset rdf:type ?dataset_type .
    ?dataset_type rdfs:subClassOf* ml:TestDataSet .
    OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
}
LIMIT 200

```

#### Step 3: `find_pipelines_for_models`
- Params: `{'model_iris': ['http://example.com/BioOps#BatchReleaseLogReg', 'http://example.com/BioOps#BatchReleaseMLP', 'http://example.com/BioOps#BatchReleaseSVM', 'http://example.com/MNIST#MLModel1', 'http://example.com/MNIST#MLModel2', 'http://example.com/MNIST#MLModel3']}`
- Result count: `50`
- Reasoning: The question asks for related pipeline context.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model_name ?pipeline WHERE {
    VALUES ?model_name { <http://example.com/BioOps#BatchReleaseLogReg> <http://example.com/BioOps#BatchReleaseMLP> <http://example.com/BioOps#BatchReleaseSVM> <http://example.com/MNIST#MLModel1> <http://example.com/MNIST#MLModel2> <http://example.com/MNIST#MLModel3> }
    ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?model_name .
}
LIMIT 200

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1925`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
Show me models their test dataset, and their pipeline that has performance more than 0.9
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {},
  "use_inference": false,
  "reasoning": "The request requires filtering across multiple components (models, datasets, pipelines) based on a quantitative metric ('performance more than 0.9'). This involves complex lineage tracing and aggregation/metric-based querying, which necessitates the use of custom SPARQL."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `8832`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: Show me models their test dataset, and their pipeline that has performance more than 0.9

Filtered results:
[
  {
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9832",
    "test_datasets": [
      "http://example.com/MNIST#PreprocessedDataset1",
      "http://example.com/MNIST#PreprocessedDataset2",
      "http://example.com/MNIST#PreprocessedDataset3",
      "http://example.com/MNIST#PreprocessedDataset4",
      "http://example.com/MNIST#PreprocessedDataset5",
      "http://example.com/MNIST#PreprocessedDataset6",
      "http://example.com/MNIST-lifecycle#MNISTTestPrepared2025"
    ],
    "test_dataset_roles": [
      "test data set",
      "test data set",
      "test data set",
      "test data set",
      "test data set",
      "test data set",
      "test data set"
    ],
    "pipelines": [
      "http://example.com/MNIST#ModelTraining1",
      "http://example.com/MNIST-lifecycle#MNISTTrainingRun",
      "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
      "http://example.com/MNIST-lifecycle#MNISTModelUpdate2025Q3",
      "http://example.com/MNIST#ModelExecution1",
      "http://example.com/MNIST#ModelExecution2",
      "http://example.com/MNIST#ModelExecution3",
      "http://example.com/MNIST#ModelExecution4",
      "http://example.com/MNIST#ModelExecution5",
      "http://example.com/MNIST#ModelExecution6",
      "http://example.com/MNIST-lifecycle#MNISTProductionExecutionQ3",
      "http://example.com/MNIST-lifecycle#MNISTInitialDeployedState",
      "http://example.com/MNIST-lifecycle#MNISTProductionExecutionQ4",
      "http://example.com/MNIST-lifecycle#MNISTUpdatedDeployedState",
      "http://example.com/MNIST-lifecycle#MNISTOfflineExecution"
    ]
  },
  {
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9671",
    "test_datasets": [
      "http://example.com/MNIST#PreprocessedDataset10",
      "http://example.com/MNIST#PreprocessedDataset11",
      "http://example.com/MNIST#PreprocessedDataset12",
      "http://example.com/MNIST#PreprocessedDataset13",
      "http://example.com/MNIST#PreprocessedDataset14",
      "http://example.com/MNIST#PreprocessedDataset15"
    ],
    "test_dataset_roles": [
      "test data set",
      "test data set",
      "test data set",
      "test data set",
      "test data set",
      "test data set"
    ],
    "pipelines": [
      "http://example.com/MNIST#ModelTraining2",
      "http://example.com/MNIST#ModelExecution10",
      "http://example.com/MNIST#ModelExecution11",
      "http://example.com/MNIST#ModelExecution12",
      "http://example.com/MNIST#ModelExecution13",
      "http://example.com/MNIST#ModelExecution14",
      "http://example.com/MNIST#ModelExecution15"
    ]
  },
  {
    "model_name": "http://example.com/BioOps#BatchReleaseMLP",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.941",
    "test_datasets": [
      "http://example.com/BioOps#BatchReleaseTestData",
      "http://example.com/BioOps#BatchReleaseTestData_MissingSensors",
      "http://example.com/BioOps#BatchReleaseTestData_Drift",
      "http://example.com/BioOps#BatchReleaseTestData_Noise"
    ],
    "test_dataset_roles": [
      "test data set",
      "test data set",
      "test data set",
      "test data set"
    ],
    "pipelines": [
      "http://example.com/BioOps#BatchReleaseModelUpdate_v2",
      "http://example.com/BioOps#BatchReleaseLifecyclePipeline",
      "http://example.com/BioOps#Training_MLP_20251006",
      "http://example.com/BioOps#BatchReleaseProductionExecution_v1",
      "http://example.com/BioOps#BatchReleaseDeployedState_v1",
      "http://example.com/BioOps#BatchReleaseProductionExecution_v2",
      "http://example.com/BioOps#BatchReleaseDeployedState_v2",
      "http://example.com/BioOps#Execution_MLP_Test",
      "http://example.com/BioOps#Execution_MLP_Missing",
      "http://example.com/BioOps#Execution_MLP_Drift",
      "http://example.com/BioOps#Execution_MLP_Noise"
    ]
  },
  {
    "model_name": "http://example.com/MNIST#MLModel3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9236",
    "test_datasets": [
      "http://example.com/MNIST#PreprocessedDataset20",
      "http://example.com/MNIST#PreprocessedDataset21",
      "http://example.com/MNIST#PreprocessedDataset22",
      "http://example.com/MNIST#PreprocessedDataset23",
      "http://example.com/MNIST#PreprocessedDataset24",
      "http://example.com/MNIST#PreprocessedDataset25"
    ],
    "test_dataset_roles": [
      "test data set",
      "test data set",
      "test data set",
      "test data set",
      "test data set",
      "test data set"
    ],
    "pipelines": [
      "http://example.com/MNIST#ModelTraining3",
      "http://example.com/MNIST#ModelExecution20",
      "http://example.com/MNIST#ModelExecution21",
      "http://example.com/MNIST#ModelExecution22",
      "http://example.com/MNIST#ModelExecution23",
      "http://example.com/MNIST#ModelExecution24",
      "http://example.com/MNIST#ModelExecution25"
    ]
  },
  {
    "model_name": "http://example.com/BioOps#BatchReleaseSVM",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.917",
    "test_datasets": [
      "http://example.com/BioOps#BatchReleaseTestData",
      "http://example.com/BioOps#BatchReleaseTestData_MissingSensors",
      "http://example.com/BioOps#BatchReleaseTestData_Drift",
      "http://example.com/BioOps#BatchReleaseTestData_Noise"
    ],
    "test_dataset_roles": [
      "test data set",
      "test data set",
      "test data set",
      "test data set"
    ],
    "pipelines": [
      "http://example.com/BioOps#Training_SVM_20251006",
      "http://example.com/BioOps#Execution_SVM_Test",
      "http://example.com/BioOps#Execution_SVM_Missing",
      "http://example.com/BioOps#Execution_SVM_Drift",
      "http://example.com/BioOps#Execution_SVM_Noise"
    ]
  },
  {
    "model_name": "http://example.com/BioOps#BatchReleaseLogReg",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.904",
    "test_datasets": [
      "http://example.com/BioOps#BatchReleaseTestData",
      "http://example.com/BioOps#BatchReleaseTestData_MissingSensors",
      "http://example.com/BioOps#BatchReleaseTestData_Drift",
      "http://example.com/BioOps#BatchReleaseTestData_Noise"
    ],
    "test_dataset_roles": [
      "test data set",
      "test data set",
      "test data set",
      "test data set"
    ],
    "pipelines": [
      "http://example.com/BioOps#Training_LogReg_20251006",
      "http://example.com/BioOps#Execution_LogReg_Test",
      "http://example.com/BioOps#Execution_LogReg_Missing",
      "http://example.com/BioOps#Execution_LogReg_Drift",
      "http://example.com/BioOps#Execution_LogReg_Noise"
    ]
  }
]

Planned steps:
[
  {
    "tool": "find_test_datasets_for_models",
    "params": {
      "dataset_kind": "test"
    },
    "reasoning": "The question asks for related test-dataset context."
  },
  {
    "tool": "find_pipelines_for_models",
    "params": {},
    "reasoning": "The question asks for related pipeline context."
  }
]

Execution steps:
[
  {
    "tool": "performance_filter",
    "params": {
      "metric_label": "classification accuracy",
      "limit": 50,
      "order": "DESC",
      "threshold_op": ">",
      "threshold_value": "0.9"
    },
    "result_count": 21
  },
  {
    "tool": "find_test_datasets_for_models",
    "params": {
      "model_iris": [
        "http://example.com/BioOps#BatchReleaseLogReg",
        "http://example.com/BioOps#BatchReleaseMLP",
        "http://example.com/BioOps#BatchReleaseSVM",
        "http://example.com/MNIST#MLModel1",
        "http://example.com/MNIST#MLModel2",
        "http://example.com/MNIST#MLModel3"
      ],
      "dataset_kind": "test"
    },
    "result_count": 31
  },
  {
    "tool": "find_pipelines_for_models",
    "params": {
      "model_iris": [
        "http://example.com/BioOps#BatchReleaseLogReg",
        "http://example.com/BioOps#BatchReleaseMLP",
        "http://example.com/BioOps#BatchReleaseSVM",
        "http://example.com/MNIST#MLModel1",
        "http://example.com/MNIST#MLModel2",
        "http://example.com/MNIST#MLModel3"
      ]
    },
    "result_count": 50
  }
]
```

Response text:
```text
Based on your criteria (classification accuracy > 0.9), here are the models, their associated test datasets, and pipelines:

**1. MNIST Model 1**
*   **Performance:** 0.9832 classification accuracy
*   **Test Datasets:** Includes preprocessed datasets like `http://example.com/MNIST#PreprocessedDataset1` through `...#PreprocessedDataset6`, and a specific test dataset: `http://example.com/MNIST-lifecycle#MNISTTestPrepared2025`.
*   **Pipelines:** Associated with multiple execution and lifecycle stages, including training runs (`http://example.com/MNIST#ModelTraining1`), operational lifecycles (`...#MNISTOperationalLifecycle2025`), and various production executions (e.g., `...#MNISTProductionExecutionQ3`, `...#MNISTInitialDeployedState`).

**2. MNIST Model 2**
*   **Performance:** 0.9671 classification accuracy
*   **Test Datasets:** Includes preprocessed datasets from `http://example.com/MNIST#PreprocessedDataset10` through `...#PreprocessedDataset15`.
*   **Pipelines:** Associated with model training and multiple execution steps, such as `http://example.com/MNIST#ModelTraining2`, `http://example.com/MNIST#ModelExecution10`, up to `...#ModelExecution15`.

**3. BioOps BatchRelease MLP Model**
*   **Performance:** 0.941 classification accuracy
*   **Test Datasets:** Includes specific test datasets for various scenarios: `http://example.com/BioOps#BatchReleaseTestData`, `...#MissingSensors`, `...#Drift`, and `...#Noise`.
*   **Pipelines:** Associated with model updates, lifecycle management (`...#BatchReleaseLifecyclePipeline`), training runs (e.g., `...#Training_MLP_20251006`), and multiple production/test executions for different scenarios.

**4. MNIST Model 3**
*   **Performance:** 0.9236 classification accuracy
*   **Test Datasets:** Includes preprocessed datasets from `http://example.com/MNIST#PreprocessedDataset20` through `...#PreprocessedDataset25`.
*   **Pipelines:** Associated with model training and multiple execution steps, such as `http://example.com/MNIST#ModelTraining3`, `http://example.com/MNIST#ModelExecution20`, up to `...#ModelExecution25`.

**5. BioOps BatchRelease SVM Model**
*   **Performance:** 0.917 classification accuracy
*   **Test Datasets:** Includes specific test datasets for various scenarios: `http://example.com/BioOps#BatchReleaseTestData`, `...#MissingSensors`, `...#Drift`, and `...#Noise`.
*   **Pipelines:** Associated with training runs (e.g., `...#Training_SVM_20251006`) and specific execution steps for testing different scenarios (`...#Execution_SVM_Test`, `...#Execution_SVM_Missing`, etc.).

**6. BioOps BatchRelease LogReg Model**
*   **Performance:** 0.904 classification accuracy
*   **Test Datasets:** Includes specific test datasets for various scenarios: `http://example.com/BioOps#BatchReleaseTestData`, `...#MissingSensors`, `...#Drift`, and `...#Noise`.
*   **Pipelines:** Associated with training runs (e.g., `...#Training_LogReg_20251006`) and specific execution steps for testing different scenarios (`...#Execution_LogReg_Test`, `...#Execution_LogReg_Missing`, etc.).
```

### Final SPARQL
```sparql
-- Step 1: performance filter

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?model_name ?model_performance_metric ?model_performance_value WHERE {
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    ?model_performance_assessment ml:hasDataInput ?model_output .
    ?ml_process ml:hasDataOutput ?model_output .
    ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
    ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment .
    ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
    ?model_performance_metric_type rdfs:subClassOf* ml:PerformanceMetric .
    ?model_performance_metric_type rdfs:label ?model_performance_metric .
    ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
    FILTER(LCASE(STR(?model_performance_metric)) = "classification accuracy")
    FILTER(xsd:decimal(?model_performance_value) > 0.9)
    
}
ORDER BY DESC(xsd:decimal(?model_performance_value))
LIMIT 50


-- Step 2: model test datasets

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model_name ?dataset ?dataset_role WHERE {
    VALUES ?model_name { <http://example.com/BioOps#BatchReleaseLogReg> <http://example.com/BioOps#BatchReleaseMLP> <http://example.com/BioOps#BatchReleaseSVM> <http://example.com/MNIST#MLModel1> <http://example.com/MNIST#MLModel2> <http://example.com/MNIST#MLModel3> }
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?ml_process ml:hasDataInput ?dataset .
    ?dataset rdf:type ?dataset_type .
    ?dataset_type rdfs:subClassOf* ml:TestDataSet .
    OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
}
LIMIT 200


-- Step 3: model pipelines

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model_name ?pipeline WHERE {
    VALUES ?model_name { <http://example.com/BioOps#BatchReleaseLogReg> <http://example.com/BioOps#BatchReleaseMLP> <http://example.com/BioOps#BatchReleaseSVM> <http://example.com/MNIST#MLModel1> <http://example.com/MNIST#MLModel2> <http://example.com/MNIST#MLModel3> }
    ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?model_name .
}
LIMIT 200

```

### Result Preview
```json
[{'model_name': 'http://example.com/MNIST#MLModel1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9832', 'test_datasets': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset2', 'http://example.com/MNIST#PreprocessedDataset3', 'http://example.com/MNIST#PreprocessedDataset4', 'http://example.com/MNIST#PreprocessedDataset5', 'http://example.com/MNIST#PreprocessedDataset6', 'http://example.com/MNIST-lifecycle#MNISTTestPrepared2025'], 'test_dataset_roles': ['test data set', 'test data set', 'test data set', 'test data set', 'test data set', 'test data set', 'test data set'], 'pipelines': ['http://example.com/MNIST#ModelTraining1', 'http://example.com/MNIST-lifecycle#MNISTTrainingRun', 'http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025', 'http://example.com/MNIST-lifecycle#MNISTModelUpdate2025Q3', 'http://example.com/MNIST#ModelExecution1', 'http://example.com/MNIST#ModelExecution2', 'http://example.com/MNIST#ModelExecution3', 'http://example.com/MNIST#ModelExecution4', 'http://example.com/MNIST#ModelExecution5', 'http://example.com/MNIST#ModelExecution6', 'http://example.com/MNIST-lifecycle#MNISTProductionExecutionQ3', 'http://example.com/MNIST-lifecycle#MNISTInitialDeployedState', 'http://example.com/MNIST-lifecycle#MNISTProductionExecutionQ4', 'http://example.com/MNIST-lifecycle#MNISTUpdatedDeployedState', 'http://example.com/MNIST-lifecycle#MNISTOfflineExecution']}, {'model_name': 'http://example.com/MNIST#MLModel2', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9671', 'test_datasets': ['http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset11', 'http://example.com/MNIST#PreprocessedDataset12', 'http://example.com/MNIST#PreprocessedDataset13', 'http://example.com/MNIST#PreprocessedDataset14', 'http://example.com/MNIST#PreprocessedDataset15'], 'test_dataset_roles': ['test data set', 'test data set', 'test data set', 'test data set', 'test data set', 'test data set'], 'pipelines': ['http://example.com/MNIST#ModelTraining2', 'http://example.com/MNIST#ModelExecution10', 'http://example.com/MNIST#ModelExecution11', 'http://example.com/MNIST#ModelExecution12', 'http://example.com/MNIST#ModelExecution13', 'http://example.com/MNIST#ModelExecution14', 'http://example.com/MNIST#ModelExecution15']}, {'model_name': 'http://example.com/BioOps#BatchReleaseMLP', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.941', 'test_datasets': ['http://example.com/BioOps#BatchReleaseTestData', 'http://example.com/BioOps#BatchReleaseTestData_MissingSensors', 'http://example.com/BioOps#BatchReleaseTestData_Drift', 'http://example.com/BioOps#BatchReleaseTestData_Noise'], 'test_dataset_roles': ['test data set', 'test data set', 'test data set', 'test data set'], 'pipelines': ['http://example.com/BioOps#BatchReleaseModelUpdate_v2', 'http://example.com/BioOps#BatchReleaseLifecyclePipeline', 'http://example.com/BioOps#Training_MLP_20251006', 'http://example.com/BioOps#BatchReleaseProductionExecution_v1', 'http://example.com/BioOps#BatchReleaseDeployedState_v1', 'http://example.com/BioOps#BatchReleaseProductionExecution_v2', 'http://example.com/BioOps#BatchReleaseDeployedState_v2', 'http://example.com/BioOps#Execution_MLP_Test', 'http://example.com/BioOps#Execution_MLP_Missing', 'http://example.com/BioOps#Execution_MLP_Drift', 'http://example.com/BioOps#Execution_MLP_Noise']}, {'model_name': 'http://example.com/MNIST#MLModel3', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9236', 'test_datasets': ['http://example.com/MNIST#PreprocessedDataset20', 'http://example.com/MNIST#PreprocessedDataset21', 'http://example.com/MNIST#PreprocessedDataset22', 'http://example.com/MNIST#PreprocessedDataset23', 'http://example.com/MNIST#PreprocessedDataset24', 'http://example.com/MNIST#PreprocessedDataset25'], 'test_dataset_roles': ['test data set', 'test data set', 'test data set', 'test data set', 'test data set', 'test data set'], 'pipelines': ['http://example.com/MNIST#ModelTraining3', 'http://example.com/MNIST#ModelExecution20', 'http://example.com/MNIST#ModelExecution21', 'http://example.com/MNIST#ModelExecution22', 'http://example.com/MNIST#ModelExecution23', 'http://example.com/MNIST#ModelExecution24', 'http://example.com/MNIST#ModelExecution25']}, {'model_name': 'http://example.com/BioOps#BatchReleaseSVM', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.917', 'test_datasets': ['http://example.com/BioOps#BatchReleaseTestData', 'http://example.com/BioOps#BatchReleaseTestData_MissingSensors', 'http://example.com/BioOps#BatchReleaseTestData_Drift', 'http://example.com/BioOps#BatchReleaseTestData_Noise'], 'test_dataset_roles': ['test data set', 'test data set', 'test data set', 'test data set'], 'pipelines': ['http://example.com/BioOps#Training_SVM_20251006', 'http://example.com/BioOps#Execution_SVM_Test', 'http://example.com/BioOps#Execution_SVM_Missing', 'http://example.com/BioOps#Execution_SVM_Drift', 'http://example.com/BioOps#Execution_SVM_Noise']}]
```

## 11. What pipeline uses MnistG16?
- Started: `2026-04-13T20:33:24.755125+00:00`
- Intent tool: `find_pipelines`
- Inference used: `False`
- Result count: `20`
- Intent reasoning: The user is asking for a specific association (which pipeline uses which dataset). find_pipelines allows searching by associated dataset to retrieve relevant pipelines.
- Result keys: `pipeline_associated_model, pipeline_components, pipeline_data_input, pipeline_data_output, pipeline_name, pipeline_type`

### Executed Steps

#### Step 1: `find_pipelines`
- Params: `{'associated_dataset': 'MnistG16'}`
- Result count: `20`
- Reasoning: The user is asking for a specific association (which pipeline uses which dataset). find_pipelines allows searching by associated dataset to retrieve relevant pipelines.

SPARQL:
```sparql

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    (STRAFTER(STR(?pipeline), "#") AS ?pipeline_name)
    ?pipeline_type
    ?pipeline_components
    (STRAFTER(STR(?pipeline_data_input_iri), "#") AS ?pipeline_data_input)
    (STRAFTER(STR(?pipeline_data_output_iri), "#") AS ?pipeline_data_output)
    (STRAFTER(STR(?pipeline_associated_model_iri), "#") AS ?pipeline_associated_model)

FROM <http://www.ontotext.com/explicit>
WHERE {
    {
        SELECT
            ?pipeline
            ?pipeline_type
            (GROUP_CONCAT(DISTINCT ?pipeline_component_label; separator=";") AS ?pipeline_components)
        WHERE {
            ?pipeline rdf:type ?pipeline_type_iri.
            ?pipeline_type_iri rdfs:label ?pipeline_type .
            
            {
                ?pipeline_type_iri rdfs:subClassOf+ ml:DataProcessingPipeline.
                ?pipeline_type_iri rdfs:label ?pipeline_type
            }
            UNION
            {
                VALUES ?pipeline_type_iri { ml:MachineLearningModelDevelopmentPipeline }
                ?pipeline rdf:type ?pipeline_type_iri.
                ?pipeline_type_iri rdfs:label ?pipeline_type
            }
            {?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?model}
UNION
{?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?model}
?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel.

            ?pipeline bfo:BFO_0000117 ?pipeline_component.
            ?pipeline_component rdf:type ?pipeline_component_type.
            ?pipeline_component_type rdfs:subClassOf+ iof-core:PlannedProcess.
            ?pipeline_component_type rdfs:label ?pipeline_component_label
        }
        GROUP BY
            ?pipeline ?pipeline_type
    }
    OPTIONAL { ?pipeline ml:hasDataInput ?pipeline_data_input_iri }
    OPTIONAL { ?pipeline ml:hasDataOutput ?pipeline_data_output_iri }
    OPTIONAL {
        {
            ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }
        UNION
        {
            ?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }
        ?pipeline_associated_model_iri rdf:type/rdfs:subClassOf* ml:MachineLearningModel
    }
}

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1865`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
What pipeline uses MnistG16?
```

Response text:
```text
```json
{
  "tool": "find_pipelines",
  "params": {
    "associated_dataset": "MnistG16"
  },
  "use_inference": false,
  "reasoning": "The user is asking for a specific association (which pipeline uses which dataset). find_pipelines allows searching by associated dataset to retrieve relevant pipelines."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `8004`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: What pipeline uses MnistG16?

Filtered results:
[
  {
    "pipeline_name": "PreprocessingPipeline1",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistG16",
    "pipeline_data_output": "PreprocessedDataset1",
    "pipeline_associated_model": "MLModel1"
  },
  {
    "pipeline_name": "PreprocessingPipeline2",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistG48",
    "pipeline_data_output": "PreprocessedDataset2",
    "pipeline_associated_model": "MLModel1"
  },
  {
    "pipeline_name": "PreprocessingPipeline3",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistG96",
    "pipeline_data_output": "PreprocessedDataset3",
    "pipeline_associated_model": "MLModel1"
  },
  {
    "pipeline_name": "PreprocessingPipeline4",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistNoNoise",
    "pipeline_data_output": "PreprocessedDataset4",
    "pipeline_associated_model": "MLModel1"
  },
  {
    "pipeline_name": "PreprocessingPipeline5",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistP",
    "pipeline_data_output": "PreprocessedDataset5",
    "pipeline_associated_model": "MLModel1"
  },
  {
    "pipeline_name": "PreprocessingPipeline6",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistG48P",
    "pipeline_data_output": "PreprocessedDataset6",
    "pipeline_associated_model": "MLModel1"
  },
  {
    "pipeline_name": "PreprocessingPipeline10",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistG16",
    "pipeline_data_output": "PreprocessedDataset10",
    "pipeline_associated_model": "MLModel2"
  },
  {
    "pipeline_name": "PreprocessingPipeline11",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistG48",
    "pipeline_data_output": "PreprocessedDataset11",
    "pipeline_associated_model": "MLModel2"
  },
  {
    "pipeline_name": "PreprocessingPipeline12",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistG96",
    "pipeline_data_output": "PreprocessedDataset12",
    "pipeline_associated_model": "MLModel2"
  },
  {
    "pipeline_name": "PreprocessingPipeline13",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistNoNoise",
    "pipeline_data_output": "PreprocessedDataset13",
    "pipeline_associated_model": "MLModel2"
  },
  {
    "pipeline_name": "PreprocessingPipeline14",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistP",
    "pipeline_data_output": "PreprocessedDataset14",
    "pipeline_associated_model": "MLModel2"
  },
  {
    "pipeline_name": "PreprocessingPipeline15",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "data reshaping operation;feature scaling operation;type casting operation",
    "pipeline_data_input": "MnistG48P",
    "pipeline_data_output": "PreprocessedDataset15",
    "pipeline_associated_model": "MLModel2"
  },
  {
    "pipeline_name": "PreprocessingPipeline20",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "feature scaling operation",
    "pipeline_data_input": "MnistG16",
    "pipeline_data_output": "PreprocessedDataset20",
    "pipeline_associated_model": "MLModel3"
  },
  {
    "pipeline_name": "PreprocessingPipeline21",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "feature scaling operation",
    "pipeline_data_input": "MnistG48",
    "pipeline_data_output": "PreprocessedDataset21",
    "pipeline_associated_model": "MLModel3"
  },
  {
    "pipeline_name": "PreprocessingPipeline22",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "feature scaling operation",
    "pipeline_data_input": "MnistG96",
    "pipeline_data_output": "PreprocessedDataset22",
    "pipeline_associated_model": "MLModel3"
  },
  {
    "pipeline_name": "PreprocessingPipeline23",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "feature scaling operation",
    "pipeline_data_input": "MnistP",
    "pipeline_data_output": "PreprocessedDataset23",
    "pipeline_associated_model": "MLModel3"
  },
  {
    "pipeline_name": "PreprocessingPipeline24",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "feature scaling operation",
    "pipeline_data_input": "MnistG48P",
    "pipeline_data_output": "PreprocessedDataset24",
    "pipeline_associated_model": "MLModel3"
  },
  {
    "pipeline_name": "PreprocessingPipeline25",
    "pipeline_type": "machine learning data preparation pipeline",
    "pipeline_components": "feature scaling operation",
    "pipeline_data_input": "MnistNoNoise",
    "pipeline_data_output": "PreprocessedDataset25",
    "pipeline_associated_model": "MLModel3"
  },
  {
    "pipeline_name": "MNISTOperationalLifecycle2025",
    "pipeline_type": "machine learning model development pipeline",
    "pipeline_components": "machine learning data set partitioning;machine learning data preparation pipeline;model selection;machine learning training;supervised learning;model evaluation;model performance assessment;machine learning model deployment process;model execution;model performance monitoring;data quality monitoring;machine learning model update",
    "pipeline_data_input": "MNIST2025Raw",
    "pipeline_data_output": null,
    "pipeline_associated_model": "MLModel1"
  },
  {
    "pipeline_name": "BatchReleaseLifecyclePipeline",
    "pipeline_type": "machine learning model development pipeline",
    "pipeline_components": "data cleaning pipeline;feature engineering pipeline;machine learning data set partitioning;hyperparameter tuning;model selection;machine learning model deployment process;model execution;model performance monitoring;data quality monitoring;machine learning model update",
    "pipeline_data_input": "BatchReleaseRawData",
    "pipeline_data_output": "BatchReleaseMLP",
    "pipeline_associated_model": "BatchReleaseMLP"
  }
]

Planned steps:
[]

Execution steps:
[
  {
    "tool": "find_pipelines",
    "params": {
      "associated_dataset": "MnistG16"
    },
    "result_count": 20
  }
]
```

Response text:
```text
The dataset **MnistG16** is used as input for two different data preparation pipelines:

1.  **PreprocessingPipeline10:** This pipeline prepares the data and is associated with model **MLModel2**.
2.  **PreprocessingPipeline20:** This pipeline performs feature scaling on the data and is associated with model **MLModel3**.
```

### Final SPARQL
```sparql

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    (STRAFTER(STR(?pipeline), "#") AS ?pipeline_name)
    ?pipeline_type
    ?pipeline_components
    (STRAFTER(STR(?pipeline_data_input_iri), "#") AS ?pipeline_data_input)
    (STRAFTER(STR(?pipeline_data_output_iri), "#") AS ?pipeline_data_output)
    (STRAFTER(STR(?pipeline_associated_model_iri), "#") AS ?pipeline_associated_model)

FROM <http://www.ontotext.com/explicit>
WHERE {
    {
        SELECT
            ?pipeline
            ?pipeline_type
            (GROUP_CONCAT(DISTINCT ?pipeline_component_label; separator=";") AS ?pipeline_components)
        WHERE {
            ?pipeline rdf:type ?pipeline_type_iri.
            ?pipeline_type_iri rdfs:label ?pipeline_type .
            
            {
                ?pipeline_type_iri rdfs:subClassOf+ ml:DataProcessingPipeline.
                ?pipeline_type_iri rdfs:label ?pipeline_type
            }
            UNION
            {
                VALUES ?pipeline_type_iri { ml:MachineLearningModelDevelopmentPipeline }
                ?pipeline rdf:type ?pipeline_type_iri.
                ?pipeline_type_iri rdfs:label ?pipeline_type
            }
            {?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?model}
UNION
{?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?model}
?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel.

            ?pipeline bfo:BFO_0000117 ?pipeline_component.
            ?pipeline_component rdf:type ?pipeline_component_type.
            ?pipeline_component_type rdfs:subClassOf+ iof-core:PlannedProcess.
            ?pipeline_component_type rdfs:label ?pipeline_component_label
        }
        GROUP BY
            ?pipeline ?pipeline_type
    }
    OPTIONAL { ?pipeline ml:hasDataInput ?pipeline_data_input_iri }
    OPTIONAL { ?pipeline ml:hasDataOutput ?pipeline_data_output_iri }
    OPTIONAL {
        {
            ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }
        UNION
        {
            ?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }
        ?pipeline_associated_model_iri rdf:type/rdfs:subClassOf* ml:MachineLearningModel
    }
}

```

### Result Preview
```json
[{'pipeline_name': 'PreprocessingPipeline1', 'pipeline_type': 'machine learning data preparation pipeline', 'pipeline_components': 'data reshaping operation;feature scaling operation;type casting operation', 'pipeline_data_input': 'MnistG16', 'pipeline_data_output': 'PreprocessedDataset1', 'pipeline_associated_model': 'MLModel1'}, {'pipeline_name': 'PreprocessingPipeline2', 'pipeline_type': 'machine learning data preparation pipeline', 'pipeline_components': 'data reshaping operation;feature scaling operation;type casting operation', 'pipeline_data_input': 'MnistG48', 'pipeline_data_output': 'PreprocessedDataset2', 'pipeline_associated_model': 'MLModel1'}, {'pipeline_name': 'PreprocessingPipeline3', 'pipeline_type': 'machine learning data preparation pipeline', 'pipeline_components': 'data reshaping operation;feature scaling operation;type casting operation', 'pipeline_data_input': 'MnistG96', 'pipeline_data_output': 'PreprocessedDataset3', 'pipeline_associated_model': 'MLModel1'}, {'pipeline_name': 'PreprocessingPipeline4', 'pipeline_type': 'machine learning data preparation pipeline', 'pipeline_components': 'data reshaping operation;feature scaling operation;type casting operation', 'pipeline_data_input': 'MnistNoNoise', 'pipeline_data_output': 'PreprocessedDataset4', 'pipeline_associated_model': 'MLModel1'}, {'pipeline_name': 'PreprocessingPipeline5', 'pipeline_type': 'machine learning data preparation pipeline', 'pipeline_components': 'data reshaping operation;feature scaling operation;type casting operation', 'pipeline_data_input': 'MnistP', 'pipeline_data_output': 'PreprocessedDataset5', 'pipeline_associated_model': 'MLModel1'}]
```

## 12. What models use MnistG16 as test dataset?
- Started: `2026-04-13T20:33:38.427367+00:00`
- Intent tool: `find_models`
- Inference used: `False`
- Result count: `125`
- Intent reasoning: The user is asking for a direct lookup of models associated with a specific dataset ('MnistG16'). The find_models tool allows searching by dataset.
- Result keys: `deployed_on_system, deployment_status, last_model_execution, last_model_update, linked_dataset, linked_dataset_type, linked_pipeline, model, model_objective, model_output_utilization, model_performance_metric, model_performance_value, model_type`

### Executed Steps

#### Step 1: `find_models`
- Params: `{'dataset': 'MnistG16'}`
- Result count: `125`
- Reasoning: The user is asking for a direct lookup of models associated with a specific dataset ('MnistG16'). The find_models tool allows searching by dataset.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    ?model
    ?model_type
    ?model_objective
    ?deployment_status
    ?linked_dataset
    ?linked_dataset_type
    ?linked_pipeline
    ?deployed_on_system
    ?last_model_update
    ?last_model_execution
    ?model_output_utilization
    ?model_performance_metric
    ?model_performance_value

FROM <http://www.ontotext.com/explicit>
WHERE {
    ?model rdf:type ?model_type_iri .
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel .
    ?model_type_iri rdfs:label ?model_type .
    OPTIONAL { ?model rdfs:label ?model_label . }
    OPTIONAL {
        ?model bfo:BFO_0000178 ?model_objective_iri .
        ?model_objective_iri rdf:type/rdfs:label ?model_objective .
    }
    OPTIONAL {
        ?process (ml:executes | bfo:BFO_0000057) ?model .
        OPTIONAL {
            ?process ml:hasDataInput ?input_dataset .
            ?input_dataset ml:informationContentEntityDerivedFrom* ?linked_dataset .
            ?linked_dataset rdf:type ?linked_dataset_type_iri .
            ?linked_dataset_type_iri rdfs:subClassOf* ml:MachineLearningDataSet .
            ?linked_dataset_type_iri rdfs:label ?linked_dataset_type .
        }
        OPTIONAL {
            ?linked_pipeline bfo:BFO_0000117* ?process .
            ?linked_pipeline rdf:type/rdfs:subClassOf* ml:MachineLearningModelDevelopmentPipeline .
        }
        OPTIONAL {
            ?process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?process_timestamp .
        }
        OPTIONAL {
            ?process ml:hasDataOutput ?process_output .
            OPTIONAL { ?model_output_utilization ml:hasDataInput ?process_output . }
            OPTIONAL {
                ?model_performance_assessment ml:hasDataInput ?process_output .
                ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
                ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment .
                ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
                ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric .
                ?model_performance_metric_type rdfs:label ?model_performance_metric .
                ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
            }
        }
    }
    OPTIONAL {
        ?deployed_state bfo:BFO_0000167 ?model .
        ?deployed_state bfo:BFO_0000167 ?deployed_on_system .
        ?deployed_on_system rdf:type/rdfs:subClassOf* iof-core:EngineeredSystem .
        ?deployed_state bfo:BFO_0000117 ?model_execution .
        ?model_execution rdf:type/rdfs:subClassOf* ml:ModelExecution .
        OPTIONAL {
            ?model_execution bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?execution_timestamp .
        }
        OPTIONAL {
            ?ml_training ^bfo:BFO_0000117*/bfo:BFO_0000063 ?model_execution .
            ?ml_training rdf:type/rdfs:subClassOf* ml:MachineLearningTraining .
            OPTIONAL {
                ?ml_training bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?training_timestamp .
            }
        }
    }
    BIND(IF(BOUND(?deployed_on_system), "Deployed", "Undeployed") AS ?deployment_status)
    BIND(COALESCE(?training_timestamp, ?process_timestamp) AS ?last_model_update)
    BIND(?execution_timestamp AS ?last_model_execution)
    
    
    
}

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1878`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
What models use MnistG16 as test dataset?
```

Response text:
```text
```json
{
  "tool": "find_models",
  "params": {
    "dataset": "MnistG16"
  },
  "use_inference": false,
  "reasoning": "The user is asking for a direct lookup of models associated with a specific dataset ('MnistG16'). The find_models tool allows searching by dataset."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `15871`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: What models use MnistG16 as test dataset?

Filtered results:
[
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-01-15T08:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9789"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-01-15T08:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9789"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset2",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-02-20T09:30:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation2",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9671"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset2",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-02-20T09:30:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation2",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9671"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset3",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-05-25T11:15:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.8118"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset3",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-05-25T11:15:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.8118"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset4",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-04-05T16:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation4",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9807"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset4",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-04-05T16:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation4",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9807"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset5",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-03-10T14:45:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation5",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9803"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset5",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-03-10T14:45:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation5",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9803"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset6",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-06-30T13:30:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation6",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9675"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset6",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-06-30T13:30:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation6",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9675"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionPrepared_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTProductionEvaluationQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionPrepared_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTProductionEvaluationQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionPrepared_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTModelPerformanceMonitoringQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionPrepared_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTModelPerformanceMonitoringQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionBatch_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTProductionEvaluationQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionBatch_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTProductionEvaluationQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionBatch_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTModelPerformanceMonitoringQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionBatch_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTModelPerformanceMonitoringQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  }
]

Planned steps:
[]

Execution steps:
[
  {
    "tool": "find_models",
    "params": {
      "dataset": "MnistG16"
    },
    "result_count": 125
  }
]
```

Response text:
```text
The results indicate that a single model, identified as `http://example.com/MNIST#MLModel1`, is used for classification objectives. This Convolutional Neural Network model is currently deployed in a live environment (`MNISTEdgeVisionService`).

This model has been tested against multiple different datasets (including various preprocessed test data sets and production machine learning data sets). The reported performance varies depending on the dataset, with classification accuracy scores ranging from approximately 0.81 to 0.98.
```

### Final SPARQL
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    ?model
    ?model_type
    ?model_objective
    ?deployment_status
    ?linked_dataset
    ?linked_dataset_type
    ?linked_pipeline
    ?deployed_on_system
    ?last_model_update
    ?last_model_execution
    ?model_output_utilization
    ?model_performance_metric
    ?model_performance_value

FROM <http://www.ontotext.com/explicit>
WHERE {
    ?model rdf:type ?model_type_iri .
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel .
    ?model_type_iri rdfs:label ?model_type .
    OPTIONAL { ?model rdfs:label ?model_label . }
    OPTIONAL {
        ?model bfo:BFO_0000178 ?model_objective_iri .
        ?model_objective_iri rdf:type/rdfs:label ?model_objective .
    }
    OPTIONAL {
        ?process (ml:executes | bfo:BFO_0000057) ?model .
        OPTIONAL {
            ?process ml:hasDataInput ?input_dataset .
            ?input_dataset ml:informationContentEntityDerivedFrom* ?linked_dataset .
            ?linked_dataset rdf:type ?linked_dataset_type_iri .
            ?linked_dataset_type_iri rdfs:subClassOf* ml:MachineLearningDataSet .
            ?linked_dataset_type_iri rdfs:label ?linked_dataset_type .
        }
        OPTIONAL {
            ?linked_pipeline bfo:BFO_0000117* ?process .
            ?linked_pipeline rdf:type/rdfs:subClassOf* ml:MachineLearningModelDevelopmentPipeline .
        }
        OPTIONAL {
            ?process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?process_timestamp .
        }
        OPTIONAL {
            ?process ml:hasDataOutput ?process_output .
            OPTIONAL { ?model_output_utilization ml:hasDataInput ?process_output . }
            OPTIONAL {
                ?model_performance_assessment ml:hasDataInput ?process_output .
                ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
                ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment .
                ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
                ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric .
                ?model_performance_metric_type rdfs:label ?model_performance_metric .
                ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
            }
        }
    }
    OPTIONAL {
        ?deployed_state bfo:BFO_0000167 ?model .
        ?deployed_state bfo:BFO_0000167 ?deployed_on_system .
        ?deployed_on_system rdf:type/rdfs:subClassOf* iof-core:EngineeredSystem .
        ?deployed_state bfo:BFO_0000117 ?model_execution .
        ?model_execution rdf:type/rdfs:subClassOf* ml:ModelExecution .
        OPTIONAL {
            ?model_execution bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?execution_timestamp .
        }
        OPTIONAL {
            ?ml_training ^bfo:BFO_0000117*/bfo:BFO_0000063 ?model_execution .
            ?ml_training rdf:type/rdfs:subClassOf* ml:MachineLearningTraining .
            OPTIONAL {
                ?ml_training bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?training_timestamp .
            }
        }
    }
    BIND(IF(BOUND(?deployed_on_system), "Deployed", "Undeployed") AS ?deployment_status)
    BIND(COALESCE(?training_timestamp, ?process_timestamp) AS ?last_model_update)
    BIND(?execution_timestamp AS ?last_model_execution)
    
    
    
}

```

### Result Preview
```json
[{'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-01-15T08:00:00-04:00', 'last_model_execution': '2025-07-15T10:00:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9789'}, {'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-01-15T08:00:00-04:00', 'last_model_execution': '2025-10-10T09:15:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9789'}, {'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset2', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-02-20T09:30:00-04:00', 'last_model_execution': '2025-07-15T10:00:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation2', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9671'}, {'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset2', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-02-20T09:30:00-04:00', 'last_model_execution': '2025-10-10T09:15:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation2', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9671'}, {'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset3', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-05-25T11:15:00-04:00', 'last_model_execution': '2025-07-15T10:00:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation3', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.8118'}]
```

## 13. What models use MnistG16 as training dataset?
- Started: `2026-04-13T20:34:05.171516+00:00`
- Intent tool: `find_models`
- Inference used: `False`
- Result count: `125`
- Intent reasoning: The user is asking for a list of models associated with a specific dataset ('MnistG16'). The find_models tool allows searching for models based on the dataset they were trained on.
- Result keys: `deployed_on_system, deployment_status, last_model_execution, last_model_update, linked_dataset, linked_dataset_type, linked_pipeline, model, model_objective, model_output_utilization, model_performance_metric, model_performance_value, model_type`

### Executed Steps

#### Step 1: `find_models`
- Params: `{'dataset': 'MnistG16'}`
- Result count: `125`
- Reasoning: The user is asking for a list of models associated with a specific dataset ('MnistG16'). The find_models tool allows searching for models based on the dataset they were trained on.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    ?model
    ?model_type
    ?model_objective
    ?deployment_status
    ?linked_dataset
    ?linked_dataset_type
    ?linked_pipeline
    ?deployed_on_system
    ?last_model_update
    ?last_model_execution
    ?model_output_utilization
    ?model_performance_metric
    ?model_performance_value

FROM <http://www.ontotext.com/explicit>
WHERE {
    ?model rdf:type ?model_type_iri .
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel .
    ?model_type_iri rdfs:label ?model_type .
    OPTIONAL { ?model rdfs:label ?model_label . }
    OPTIONAL {
        ?model bfo:BFO_0000178 ?model_objective_iri .
        ?model_objective_iri rdf:type/rdfs:label ?model_objective .
    }
    OPTIONAL {
        ?process (ml:executes | bfo:BFO_0000057) ?model .
        OPTIONAL {
            ?process ml:hasDataInput ?input_dataset .
            ?input_dataset ml:informationContentEntityDerivedFrom* ?linked_dataset .
            ?linked_dataset rdf:type ?linked_dataset_type_iri .
            ?linked_dataset_type_iri rdfs:subClassOf* ml:MachineLearningDataSet .
            ?linked_dataset_type_iri rdfs:label ?linked_dataset_type .
        }
        OPTIONAL {
            ?linked_pipeline bfo:BFO_0000117* ?process .
            ?linked_pipeline rdf:type/rdfs:subClassOf* ml:MachineLearningModelDevelopmentPipeline .
        }
        OPTIONAL {
            ?process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?process_timestamp .
        }
        OPTIONAL {
            ?process ml:hasDataOutput ?process_output .
            OPTIONAL { ?model_output_utilization ml:hasDataInput ?process_output . }
            OPTIONAL {
                ?model_performance_assessment ml:hasDataInput ?process_output .
                ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
                ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment .
                ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
                ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric .
                ?model_performance_metric_type rdfs:label ?model_performance_metric .
                ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
            }
        }
    }
    OPTIONAL {
        ?deployed_state bfo:BFO_0000167 ?model .
        ?deployed_state bfo:BFO_0000167 ?deployed_on_system .
        ?deployed_on_system rdf:type/rdfs:subClassOf* iof-core:EngineeredSystem .
        ?deployed_state bfo:BFO_0000117 ?model_execution .
        ?model_execution rdf:type/rdfs:subClassOf* ml:ModelExecution .
        OPTIONAL {
            ?model_execution bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?execution_timestamp .
        }
        OPTIONAL {
            ?ml_training ^bfo:BFO_0000117*/bfo:BFO_0000063 ?model_execution .
            ?ml_training rdf:type/rdfs:subClassOf* ml:MachineLearningTraining .
            OPTIONAL {
                ?ml_training bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?training_timestamp .
            }
        }
    }
    BIND(IF(BOUND(?deployed_on_system), "Deployed", "Undeployed") AS ?deployment_status)
    BIND(COALESCE(?training_timestamp, ?process_timestamp) AS ?last_model_update)
    BIND(?execution_timestamp AS ?last_model_execution)
    
    
    
}

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1882`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
What models use MnistG16 as training dataset?
```

Response text:
```text
```json
{
  "tool": "find_models",
  "params": {
    "dataset": "MnistG16"
  },
  "use_inference": false,
  "reasoning": "The user is asking for a list of models associated with a specific dataset ('MnistG16'). The find_models tool allows searching for models based on the dataset they were trained on."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `15875`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: What models use MnistG16 as training dataset?

Filtered results:
[
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-01-15T08:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9789"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-01-15T08:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9789"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset2",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-02-20T09:30:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation2",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9671"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset2",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-02-20T09:30:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation2",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9671"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset3",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-05-25T11:15:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.8118"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset3",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-05-25T11:15:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.8118"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset4",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-04-05T16:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation4",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9807"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset4",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-04-05T16:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation4",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9807"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset5",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-03-10T14:45:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation5",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9803"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset5",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-03-10T14:45:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation5",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9803"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset6",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-06-30T13:30:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation6",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9675"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST#PreprocessedDataset6",
    "linked_dataset_type": "test data set",
    "linked_pipeline": null,
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2024-06-30T13:30:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST#ModelEvaluation6",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9675"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionPrepared_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTProductionEvaluationQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionPrepared_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTProductionEvaluationQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionPrepared_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTModelPerformanceMonitoringQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionPrepared_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTModelPerformanceMonitoringQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionBatch_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTProductionEvaluationQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionBatch_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTProductionEvaluationQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionBatch_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-07-15T10:00:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTModelPerformanceMonitoringQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  },
  {
    "model": "http://example.com/MNIST#MLModel1",
    "model_type": "convolutional neural network",
    "model_objective": "classification objective",
    "deployment_status": "Deployed",
    "linked_dataset": "http://example.com/MNIST-lifecycle#MNISTProductionBatch_2025Q3",
    "linked_dataset_type": "production machine learning data set",
    "linked_pipeline": "http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025",
    "deployed_on_system": "http://example.com/MNIST-lifecycle#MNISTEdgeVisionService",
    "last_model_update": "2025-07-15T10:00:00-04:00",
    "last_model_execution": "2025-10-10T09:15:00-04:00",
    "model_output_utilization": "http://example.com/MNIST-lifecycle#MNISTModelPerformanceMonitoringQ3",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9470"
  }
]

Planned steps:
[]

Execution steps:
[
  {
    "tool": "find_models",
    "params": {
      "dataset": "MnistG16"
    },
    "result_count": 125
  }
]
```

Response text:
```text
The query identifies a single Convolutional Neural Network (CNN) model, `http://example.com/MNIST#MLModel1`, which is designed for image classification. This model is currently **Deployed** and has been updated multiple times using various datasets (including test data sets and production machine learning data sets).

Key details about the model include:

*   **Model Type:** Convolutional Neural Network
*   **Objective:** Classification objective
*   **Deployment Status:** Deployed
*   **Performance:** The model consistently achieves high classification accuracy, with reported values ranging from **0.8118 to 0.9807**, depending on the specific dataset used for testing or monitoring.
*   **Pipelines/Usage:** The model is associated with several operational pipelines, including:
    *   `http://example.com/MNIST-lifecycle#MNISTOperationalLifecycle2025` (linked to `linked_pipeline`)
    *   It utilizes various evaluation and monitoring processes such as `http://example.com/MNIST#ModelEvaluation1`, `http://example.com/MNIST#ModelEvaluation2`, etc., depending on the data source.
```

### Final SPARQL
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    ?model
    ?model_type
    ?model_objective
    ?deployment_status
    ?linked_dataset
    ?linked_dataset_type
    ?linked_pipeline
    ?deployed_on_system
    ?last_model_update
    ?last_model_execution
    ?model_output_utilization
    ?model_performance_metric
    ?model_performance_value

FROM <http://www.ontotext.com/explicit>
WHERE {
    ?model rdf:type ?model_type_iri .
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel .
    ?model_type_iri rdfs:label ?model_type .
    OPTIONAL { ?model rdfs:label ?model_label . }
    OPTIONAL {
        ?model bfo:BFO_0000178 ?model_objective_iri .
        ?model_objective_iri rdf:type/rdfs:label ?model_objective .
    }
    OPTIONAL {
        ?process (ml:executes | bfo:BFO_0000057) ?model .
        OPTIONAL {
            ?process ml:hasDataInput ?input_dataset .
            ?input_dataset ml:informationContentEntityDerivedFrom* ?linked_dataset .
            ?linked_dataset rdf:type ?linked_dataset_type_iri .
            ?linked_dataset_type_iri rdfs:subClassOf* ml:MachineLearningDataSet .
            ?linked_dataset_type_iri rdfs:label ?linked_dataset_type .
        }
        OPTIONAL {
            ?linked_pipeline bfo:BFO_0000117* ?process .
            ?linked_pipeline rdf:type/rdfs:subClassOf* ml:MachineLearningModelDevelopmentPipeline .
        }
        OPTIONAL {
            ?process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?process_timestamp .
        }
        OPTIONAL {
            ?process ml:hasDataOutput ?process_output .
            OPTIONAL { ?model_output_utilization ml:hasDataInput ?process_output . }
            OPTIONAL {
                ?model_performance_assessment ml:hasDataInput ?process_output .
                ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
                ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment .
                ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
                ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric .
                ?model_performance_metric_type rdfs:label ?model_performance_metric .
                ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
            }
        }
    }
    OPTIONAL {
        ?deployed_state bfo:BFO_0000167 ?model .
        ?deployed_state bfo:BFO_0000167 ?deployed_on_system .
        ?deployed_on_system rdf:type/rdfs:subClassOf* iof-core:EngineeredSystem .
        ?deployed_state bfo:BFO_0000117 ?model_execution .
        ?model_execution rdf:type/rdfs:subClassOf* ml:ModelExecution .
        OPTIONAL {
            ?model_execution bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?execution_timestamp .
        }
        OPTIONAL {
            ?ml_training ^bfo:BFO_0000117*/bfo:BFO_0000063 ?model_execution .
            ?ml_training rdf:type/rdfs:subClassOf* ml:MachineLearningTraining .
            OPTIONAL {
                ?ml_training bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?training_timestamp .
            }
        }
    }
    BIND(IF(BOUND(?deployed_on_system), "Deployed", "Undeployed") AS ?deployment_status)
    BIND(COALESCE(?training_timestamp, ?process_timestamp) AS ?last_model_update)
    BIND(?execution_timestamp AS ?last_model_execution)
    
    
    
}

```

### Result Preview
```json
[{'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-01-15T08:00:00-04:00', 'last_model_execution': '2025-07-15T10:00:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9789'}, {'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-01-15T08:00:00-04:00', 'last_model_execution': '2025-10-10T09:15:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9789'}, {'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset2', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-02-20T09:30:00-04:00', 'last_model_execution': '2025-07-15T10:00:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation2', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9671'}, {'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset2', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-02-20T09:30:00-04:00', 'last_model_execution': '2025-10-10T09:15:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation2', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9671'}, {'model': 'http://example.com/MNIST#MLModel1', 'model_type': 'convolutional neural network', 'model_objective': 'classification objective', 'deployment_status': 'Deployed', 'linked_dataset': 'http://example.com/MNIST#PreprocessedDataset3', 'linked_dataset_type': 'test data set', 'linked_pipeline': None, 'deployed_on_system': 'http://example.com/MNIST-lifecycle#MNISTEdgeVisionService', 'last_model_update': '2024-05-25T11:15:00-04:00', 'last_model_execution': '2025-07-15T10:00:00-04:00', 'model_output_utilization': 'http://example.com/MNIST#ModelEvaluation3', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.8118'}]
```

## 14. What datasets are downstream of MnistG16?
- Started: `2026-04-13T20:34:30.725084+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `6`
- Intent reasoning: The question asks for datasets 'downstream of' a specific model (MnistG16), which is a lineage or provenance tracing query. Custom SPARQL with use_inference=false is required for such questions.
- Result keys: `artifact, artifact_label, artifact_types, downstream_dataset, downstream_dataset_type, downstream_process, downstream_process_type`

### Planned Steps
- `resolve_artifact` with params `{'artifact_name': 'MnistG16'}`
  Reasoning: Resolve the named artifact to a graph node before tracing lineage.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 1, 'frontier': ['http://example.com/MNIST#MnistG16']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 2, 'frontier': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 3, 'frontier': ['http://example.com/MNIST#ModelOutputDataset1', 'http://example.com/MNIST#ModelOutputDataset10', 'http://example.com/MNIST#ModelOutputDataset20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.
- `trace_lineage_step` with params `{'direction': 'downstream', 'hop': 4, 'frontier': ['http://example.com/MNIST#EvaluationResult1', 'http://example.com/MNIST#EvaluationResult10', 'http://example.com/MNIST#EvaluationResult20']}`
  Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

### Executed Steps

#### Step 1: `resolve_artifact`
- Params: `{'artifact_name': 'MnistG16'}`
- Result count: `2`
- Reasoning: Resolve the named artifact to a graph node before tracing lineage.

SPARQL:
```sparql

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?node ?label ?type ?type_label WHERE {
  {
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    FILTER(LCASE(STR(?label)) = LCASE("MnistG16"))
  } UNION {
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("MnistG16"))
    BIND(STRAFTER(STR(?node), "#") AS ?label)
  }
  OPTIONAL {
    ?node rdf:type ?type .
    FILTER(!isBlank(?type))
    OPTIONAL { ?type rdfs:label ?type_label }
  }
  FILTER(!isBlank(?node))
}
LIMIT 50

```

#### Step 2: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 1, 'frontier': ['http://example.com/MNIST#MnistG16']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#MnistG16> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 3: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 2, 'frontier': ['http://example.com/MNIST#PreprocessedDataset1', 'http://example.com/MNIST#PreprocessedDataset10', 'http://example.com/MNIST#PreprocessedDataset20']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 4: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 3, 'frontier': ['http://example.com/MNIST#ModelOutputDataset1', 'http://example.com/MNIST#ModelOutputDataset10', 'http://example.com/MNIST#ModelOutputDataset20']}`
- Result count: `6`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#ModelOutputDataset1> <http://example.com/MNIST#ModelOutputDataset10> <http://example.com/MNIST#ModelOutputDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

#### Step 5: `trace_lineage_step`
- Params: `{'direction': 'downstream', 'hop': 4, 'frontier': ['http://example.com/MNIST#EvaluationResult1', 'http://example.com/MNIST#EvaluationResult10', 'http://example.com/MNIST#EvaluationResult20']}`
- Result count: `0`
- Reasoning: Trace downstream one hop through MLLO data-input/data-output process links.

SPARQL:
```sparql

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#EvaluationResult1> <http://example.com/MNIST#EvaluationResult10> <http://example.com/MNIST#EvaluationResult20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1878`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
What datasets are downstream of MnistG16?
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {},
  "use_inference": false,
  "reasoning": "The question asks for datasets 'downstream of' a specific model (MnistG16), which is a lineage or provenance tracing query. Custom SPARQL with use_inference=false is required for such questions."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `5731`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: What datasets are downstream of MnistG16?

Filtered results:
[
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline1",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset1",
    "downstream_dataset_type": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline10",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset10",
    "downstream_dataset_type": "test data set"
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": null
  },
  {
    "artifact": "http://example.com/MNIST#MnistG16",
    "artifact_label": "MnistG16",
    "artifact_types": [
      "raw data set"
    ],
    "downstream_process": "http://example.com/MNIST#PreprocessingPipeline20",
    "downstream_process_type": null,
    "downstream_dataset": "http://example.com/MNIST#PreprocessedDataset20",
    "downstream_dataset_type": "test data set"
  }
]

Planned steps:
[
  {
    "tool": "resolve_artifact",
    "params": {
      "artifact_name": "MnistG16"
    },
    "reasoning": "Resolve the named artifact to a graph node before tracing lineage."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 1,
      "frontier": [
        "http://example.com/MNIST#MnistG16"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 2,
      "frontier": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 3,
      "frontier": [
        "http://example.com/MNIST#ModelOutputDataset1",
        "http://example.com/MNIST#ModelOutputDataset10",
        "http://example.com/MNIST#ModelOutputDataset20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 4,
      "frontier": [
        "http://example.com/MNIST#EvaluationResult1",
        "http://example.com/MNIST#EvaluationResult10",
        "http://example.com/MNIST#EvaluationResult20"
      ]
    },
    "reasoning": "Trace downstream one hop through MLLO data-input/data-output process links."
  }
]

Execution steps:
[
  {
    "tool": "resolve_artifact",
    "params": {
      "artifact_name": "MnistG16"
    },
    "result_count": 2
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 1,
      "frontier": [
        "http://example.com/MNIST#MnistG16"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 2,
      "frontier": [
        "http://example.com/MNIST#PreprocessedDataset1",
        "http://example.com/MNIST#PreprocessedDataset10",
        "http://example.com/MNIST#PreprocessedDataset20"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 3,
      "frontier": [
        "http://example.com/MNIST#ModelOutputDataset1",
        "http://example.com/MNIST#ModelOutputDataset10",
        "http://example.com/MNIST#ModelOutputDataset20"
      ]
    },
    "result_count": 6
  },
  {
    "tool": "trace_lineage_step",
    "params": {
      "direction": "downstream",
      "hop": 4,
      "frontier": [
        "http://example.com/MNIST#EvaluationResult1",
        "http://example.com/MNIST#EvaluationResult10",
        "http://example.com/MNIST#EvaluationResult20"
      ]
    },
    "result_count": 0
  }
]
```

Response text:
```text
The dataset MnistG16 leads to three distinct sets of preprocessed data, depending on which preprocessing pipeline was used:

1.  **PreprocessedDataset1:** Created using the `PreprocessingPipeline1`.
2.  **PreprocessedDataset10:** Created using the `PreprocessingPipeline10`.
3.  **PreprocessedDataset20:** Created using the `PreprocessingPipeline20`.

*Note: For each preprocessed dataset, there are records indicating both the main data set and a corresponding test data set.*
```

### Final SPARQL
```sparql
-- Step 1: resolve artifact

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?node ?label ?type ?type_label WHERE {
  {
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    FILTER(LCASE(STR(?label)) = LCASE("MnistG16"))
  } UNION {
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("MnistG16"))
    BIND(STRAFTER(STR(?node), "#") AS ?label)
  }
  OPTIONAL {
    ?node rdf:type ?type .
    FILTER(!isBlank(?type))
    OPTIONAL { ?type rdfs:label ?type_label }
  }
  FILTER(!isBlank(?node))
}
LIMIT 50


-- Step 2: lineage hop 1

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#MnistG16> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 3: lineage hop 2

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#PreprocessedDataset1> <http://example.com/MNIST#PreprocessedDataset10> <http://example.com/MNIST#PreprocessedDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 4: lineage hop 3

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#ModelOutputDataset1> <http://example.com/MNIST#ModelOutputDataset10> <http://example.com/MNIST#ModelOutputDataset20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500


-- Step 5: lineage hop 4

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {
  VALUES ?current_dataset { <http://example.com/MNIST#EvaluationResult1> <http://example.com/MNIST#EvaluationResult10> <http://example.com/MNIST#EvaluationResult20> }
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {
    ?process rdf:type ?process_type .
    OPTIONAL { ?process_type rdfs:label ?process_type_label }
  }
  OPTIONAL {
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL { ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }
  }
}
LIMIT 500

```

### Result Preview
```json
[{'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': None}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline1', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset1', 'downstream_dataset_type': 'test data set'}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline10', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset10', 'downstream_dataset_type': None}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline10', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset10', 'downstream_dataset_type': 'test data set'}, {'artifact': 'http://example.com/MNIST#MnistG16', 'artifact_label': 'MnistG16', 'artifact_types': ['raw data set'], 'downstream_process': 'http://example.com/MNIST#PreprocessingPipeline20', 'downstream_process_type': None, 'downstream_dataset': 'http://example.com/MNIST#PreprocessedDataset20', 'downstream_dataset_type': None}]
```

## 15. Show me models with performance more than 0.95
- Started: `2026-04-13T20:34:46.865701+00:00`
- Intent tool: `custom_sparql`
- Inference used: `False`
- Result count: `8`
- Intent reasoning: The request asks to filter models based on a quantitative performance metric ('more than 0.95'). According to the guidelines, ranking, aggregation, or metric-based questions must use custom_sparql with use_inference=false.
- Result keys: `model_name, model_performance_metric, model_performance_value`

### Executed Steps

#### Step 1: `performance_filter`
- Params: `{'metric_label': 'classification accuracy', 'limit': 50, 'order': 'DESC', 'threshold_op': '>', 'threshold_value': '0.95'}`
- Result count: `8`
- Reasoning: Deterministic performance filter query.

SPARQL:
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
    ?model_performance_assessment ml:hasDataInput ?model_output .
    ?ml_process ml:hasDataOutput ?model_output .
    ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
    ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment .
    ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
    ?model_performance_metric_type rdfs:subClassOf* ml:PerformanceMetric .
    ?model_performance_metric_type rdfs:label ?model_performance_metric .
    ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
    FILTER(LCASE(STR(?model_performance_metric)) = "classification accuracy")
    FILTER(xsd:decimal(?model_performance_value) > 0.95)
    
}
ORDER BY DESC(xsd:decimal(?model_performance_value))
LIMIT 50

```

### LLM Calls

#### LLM Call 1
- Purpose: `intent_classification`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1883`

Message 1 `system`:
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

Use custom_sparql with use_inference=false for provenance, lineage, and chain-tracing questions, especially when the question includes:
"used to make", "used to create", "made from", "derived from", "source of", "upstream", "downstream", "lineage", "provenance", "trace"

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

Message 2 `user`:
```text
Show me models with performance more than 0.95
```

Response text:
```text
```json
{
  "tool": "custom_sparql",
  "params": {},
  "use_inference": false,
  "reasoning": "The request asks to filter models based on a quantitative performance metric ('more than 0.95'). According to the guidelines, ranking, aggregation, or metric-based questions must use custom_sparql with use_inference=false."
}
```
```

#### LLM Call 2
- Purpose: `answer_generation`
- Model: `google/gemma-4-e4b`
- Prompt chars: `1987`

Message 1 `system`:
```text
Summarize ML ontology query results for a non-technical practitioner. Be concise and factual. If the results already include joined fields such as test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, downstream_process, or model_name, use them directly and do not replace them with generic guesses.
```

Message 2 `user`:
```text
Question: Show me models with performance more than 0.95

Filtered results:
[
  {
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9832"
  },
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
  },
  {
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9718"
  },
  {
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9675"
  },
  {
    "model_name": "http://example.com/MNIST#MLModel2",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9671"
  },
  {
    "model_name": "http://example.com/MNIST#MLModel1",
    "model_performance_metric": "classification accuracy",
    "model_performance_value": "0.9671"
  }
]

Planned steps:
[]

Execution steps:
[
  {
    "tool": "performance_filter",
    "params": {
      "metric_label": "classification accuracy",
      "limit": 50,
      "order": "DESC",
      "threshold_op": ">",
      "threshold_value": "0.95"
    },
    "result_count": 8
  }
]
```

Response text:
```text
The following models were found to have a classification accuracy greater than 0.95:

*   **http://example.com/MNIST#MLModel1:** This model showed several high-performing runs, with recorded accuracies ranging from **0.9675** up to **0.9832**.
*   **http://example.com/MNIST#MLModel2:** This model achieved a classification accuracy of **0.9671**.
```

### Final SPARQL
```sparql
-- Step 1: performance filter

PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?model_name ?model_performance_metric ?model_performance_value WHERE {
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    ?model_performance_assessment ml:hasDataInput ?model_output .
    ?ml_process ml:hasDataOutput ?model_output .
    ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
    ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment .
    ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
    ?model_performance_metric_type rdfs:subClassOf* ml:PerformanceMetric .
    ?model_performance_metric_type rdfs:label ?model_performance_metric .
    ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
    FILTER(LCASE(STR(?model_performance_metric)) = "classification accuracy")
    FILTER(xsd:decimal(?model_performance_value) > 0.95)
    
}
ORDER BY DESC(xsd:decimal(?model_performance_value))
LIMIT 50

```

### Result Preview
```json
[{'model_name': 'http://example.com/MNIST#MLModel1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9832'}, {'model_name': 'http://example.com/MNIST#MLModel1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9807'}, {'model_name': 'http://example.com/MNIST#MLModel1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9803'}, {'model_name': 'http://example.com/MNIST#MLModel1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9789'}, {'model_name': 'http://example.com/MNIST#MLModel1', 'model_performance_metric': 'classification accuracy', 'model_performance_value': '0.9718'}]
```
