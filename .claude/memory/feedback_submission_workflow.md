---
name: submission_workflow
description: User wants submission-ready files whenever a strategy meets PnL goals
type: feedback
---

Whenever a strategy meets the stated PnL goal during backtesting, immediately produce a submission-ready standalone Python file in `submissions/`. The file must be self-contained (include datamodel types) with a `Trader` class matching the Prosperity API signature. The user uploads it directly to the IMC platform.

**Why:** User wants to test on the official platform as soon as possible, not wait for more optimization.

**How to apply:** After any successful backtest that meets the goal, create `submissions/<strategy_name>.py` and tell the user it's ready to upload.
