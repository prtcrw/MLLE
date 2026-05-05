# Demo Replay Prompt Template

Use this when you want Codex to turn your narration into a replayable MLLE walkthrough.

```text
Build or update an MLLE replay for a screen-capture demo.

Replay URL:
http://127.0.0.1:5173/?replay=<demo-name>

Audience:
<who is watching, e.g. thesis committee, conference audience, ML governance team>

Goal:
<what the demo should prove>

Dataset / ontology context:
<e.g. MLLO + MNIST in GraphDB repo mllo4>

Recording style:
- Use real MLLE pages only.
- Show visible mouse movement.
- Click actual buttons and links.
- Type into actual search/chat fields.
- Scroll to reveal evidence.
- Pause long enough for narration.
- Do not use a static storyboard or fake result page.

My narration script:
0:00-0:40
<paste narration>

0:40-1:30
<paste narration>

1:30-2:45
<paste narration>

2:45-4:00
<paste narration>

4:00-5:15
<paste narration>

5:15-6:15
<paste narration>

6:15-7:00
<paste narration>

Required UI actions:
1. <page/action/search term/click target>
2. <page/action/search term/click target>
3. <page/action/search term/click target>

Important terms to type:
- <term 1>
- <term 2>
- <term 3>

Evidence to highlight:
- <dataset/version>
- <preprocessing step>
- <model/version>
- <evaluation metric>
- <pipeline>
- <deployment or deployment-readiness evidence>

Constraints:
- Keep GraphDB/backend/frontend assumptions explicit.
- If deployed-model records are missing, say deployment-readiness evidence instead of claiming deployment.
- Verify with npm run build.
```
