# Ab3P project kickoff: choose the phase

Use separate sessions so corpus preparation can finish before C++ results are
available. The previous single end-to-end goal is replaced by these instructions.

1. **[Prepare the representative set](PHASE_1_PREPARE_CORPUS.md).** Complete
   instructions and a paste-ready goal prompt. Finishes with frozen inputs and
   `evaluation/representative_v1.input.tar.gz`; no C++ execution required.
2. **[Run Ab3P on Linux](PHASE_2_LINUX_REFERENCE.md).** Input locations, commands
   and return contract. Copy the resulting `reference_cpp/` tree back into
   `evaluation/representative_v1/`.
3. **[Complete repair and evaluation](PHASE_3_COMPLETE_REPAIR.md).** Complete
   instructions and a separate goal prompt using the returned reference evidence.
   This phase carries the 99.9% prediction-agreement and occurrence-recovery gates.

Select **GPT-6 Sol, High reasoning effort**, open this repository's workspace and
paste the appropriate phase's `/goal` block into a new session. That model choice
is an engineering recommendation, not a guarantee of completion. OpenAI documents
[Sol's High effort support](https://developers.openai.com/api/docs/models/gpt-6-sol)
and [starting goals with `/goal`](https://learn.chatgpt.com/docs/long-running-work).

The [project plan](PROJECT_PLAN.md) retains the shared technical requirements and
evaluation contract. The corpus paths above are planned destinations until phase
1 actually creates and validates them.
