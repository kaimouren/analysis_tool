# Interview story

## Two-to-three-minute version

I built Data QA Agent because I wanted to understand how to make a data agent's work checkable, beyond whether its answer sounded convincing.

I started with a Streamlit app that checks CSV quality using deterministic Python. Then I added baseline comparisons for things like missingness and distribution drift. The next step was an investigation mode where a model could decide which analyses to run.

I kept a clear boundary: Python calculates the statistics, and the model chooses from eight registered tools. The controller limits steps, calls, and errors. The model returns actions and evidence references, while code writes the factual answer. Users can inspect the actual arguments and evidence.

The interesting challenge was evaluation. All 36 scripted investigation regressions passed. But those tests controlled the planner's decisions. They showed that the controller and tools behaved as expected, not that a real model would consistently make good choices.

So I built a second evaluation layer with 36 synthetic tasks and three runs per task. With the tested GPT-4o-mini configuration, only 21 of 108 runs succeeded: 19.44%. Recorded claims had 100% evidence grounding, but many investigations still failed.

The main failures were not unsupported numbers. They were premature stopping, missing evidence, and wrong analysis paths. For example, an agent could compare periods and finish without collecting all the requested segment evidence. A grounded answer could still be incomplete.

To detect that, the evaluator replays tools against fixed fixtures and checks the required evidence, scope, tool choices, errors, and stopping behavior. It doesn't use an LLM judge. I also made the saved trajectories replayable in normal CI without paid model calls.

One prompt experiment made the value of that clear. Golden success went from eight to eleven out of 36 runs, but a critical conversion scenario dropped from two successful repeats to one. The regression gate rejected the candidate, so I kept the existing prompt.

My main lesson was that grounding, task completion, and planning quality are different properties. The project doesn't show a highly reliable general-purpose agent. It shows how to expose reliability failures and make changes accountable to explicit evidence. With only three repeats and synthetic tasks, I also have to be careful about how far I generalize the results.

## Thirty-second version

I built a data investigation agent where Python computes the statistics and an LLM chooses bounded tools. All 36 scripted regressions passed, but repeated GPT-4o-mini evaluation achieved only 19.44% task success. The failures were mostly premature stopping and missing evidence, even though recorded claims were grounded. I added trajectory replay and regression CI, which rejected a prompt that improved aggregate results but broke a critical scenario.

Source: [recorded experiments and limitations](AGENT_RELIABILITY_CASE_STUDY.md). The long version is approximately 2–3 minutes at a conversational pace; timing varies by speaker.
