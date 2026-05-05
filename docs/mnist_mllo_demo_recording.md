# MNIST MLLO Demo Recording

Title: MLLE in Action: Turning Fragmented MNIST Metadata into Traceable Evidence

Primary recording link: `http://127.0.0.1:5173/`

Use the real MLLE application. The static MNIST storyboard page has been removed.

Replay link: `http://127.0.0.1:5173/?replay=mnist`

The replay link animates a visible cursor and uses real MLLE controls: clicks, typed searches, scrolling, navigation, and Chat with MLLO.

Demo automation landing page: `http://127.0.0.1:5173/demos`

Replay controls:

- `Pause` freezes the current replay action.
- `Resume` continues from the paused point.
- `Stop` exits replay mode.
- Seek buttons restart the replay from `Home`, `Models`, `Dataset Usages`, `Pipelines`, or `Chat`.

Recommended MLLE screen-capture flow:

1. Overview
   - Say: "We just saw that lifecycle metadata exists, but it is scattered. This demo shows how MLLE makes MNIST lifecycle fragments connected, queryable, and traceable."
   - Point at the audit question.

2. Find Datasets
   - Say: "MLLE captures lifecycle objects: the MNIST dataset, preprocessing, training run, model artifact, evaluation result, and deployment record."

3. Find Models
   - Say: "The important part is not just each object, but how MLLO represents the relationships among them."

4. Dataset Usages
   - Say: "This gives us a defensible record: which data, which preprocessing, which model version, which evaluation, and which deployment."

5. Pipelines
   - Say: "The pipeline view shows how data and model-development steps are connected."

6. Chat with MLLO
   - Say: "The same pattern extends to LLM-agent deployments: prompts, context sources, model versions, tool contracts, traces, evaluations, and approvals."

Note: the current GraphDB content has MNIST datasets, models, evaluations, and pipelines, but no deployed-model records in `/models/analyze-models` yet. For this capture, describe the final state as deployment-readiness evidence unless you add deployment-state triples before recording.

Controls:

- Start recording before the browser automation begins.
- The automation should visibly click, type, scroll, and navigate through the app.
- Good search terms for the current GraphDB data: `MNIST`, `MLModel1`, and `PreprocessedDataset1`.

To customize future replays with your own script, use [demo_replay_prompt_template.md](/Users/pnc12/Documents/GitHub/MLLO-Web-2/docs/demo_replay_prompt_template.md).
