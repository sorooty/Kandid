---
description: Start a feature the Kandid way (spec, plan, branch)
argument-hint: <short feature name>
---

Start the feature "$ARGUMENTS":

1. Check docs/specs for an existing spec. If none, draft `docs/specs/<kebab-name>.md` in English: problem, user story, scope (in/out), acceptance criteria, data touched, open questions. Keep it under one page and ask me to validate it before going further.
2. Once validated, propose an implementation plan: files to touch, `tools/kandid_tools` logic and its tests first, then skills, commands and UI. Flag anything needing an ADR.
3. After I approve the plan, create the branch `feat/<kebab-name>` from main and implement.
4. Finish with `pnpm check`, then run the code-reviewer agent and report its findings.
