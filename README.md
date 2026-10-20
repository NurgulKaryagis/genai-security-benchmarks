# AI Security Benchmarks

Controlled, defensive security experiments. Each experiment takes one known attack class, measures how well a self-built target holds without defenses, adds a defense, and measures again, reporting both the drop in attack success and the utility the system retains.

All targets are built by me and attacked only in my own local environment. No third-party systems, no proprietary material, no personal data.

## Results Matrix

| Phase | Experiment | Defense | Attack class | ASR baseline → defended | Utility retained | Link |
|-------|------------|---------|--------------|-------------------------|------------------|------|
| 0 | Measuring attack success and utility together | none (measurement experiment) | Indirect prompt injection (AgentDojo `important_instructions`) | `gpt-6-luna` baseline: 0/120 attacked episodes (110 exposed) → n/a | n/a (no defense); utility under attack 98.3% | [README](phase-0-measurement/asr-and-utility-together/README.md) |

Each write-up lists the setup, the full results with variance, cost and latency, the caveats, and what is still open. Total API spend so far: $0.56.

## How experiments are run

- **Hypothesis first.** The prediction is written before anything runs and kept even when it turns out wrong.
- **Attack success never alone.** Attack-success rate (ASR) is always reported next to the utility the agent keeps, so a defense cannot "win" by breaking the agent.
- **Exposure is checked.** Each attacked run records whether the injected content actually reached the agent; a low ASR on runs that never saw the attack proves nothing.
- **Errors are not blocks.** A crashed or broken run is reported as an error, never counted as a blocked attack.
- **Static is not robust.** A defense measured only against a fixed attack set is reported as such; robustness claims need an adaptive attempt.
- **Known attacks only.** Attacks are reproduced from published sources, cited with exact versions, and run only against my own local targets.
- **Multiple runs, nothing hidden.** Mean and run-to-run spread are reported; failed and anomalous runs are kept; "no meaningful difference" is a valid result.
- **Reproducible.** Model IDs, API settings and source commits are recorded, and every write-up has the commands to rerun it.

## OWASP LLM Top 10 Coverage

OWASP list version: **OWASP Top 10 for LLM Applications 2026** (released 2026-08-04). IDs checked against the canonical source, `GenAI-Security-Project/GenAI-LLM-Top10`, `2026/final`.

| OWASP category | Experiment(s) |
|----------------|---------------|
| LLM01:2026 Prompt Injection | [Phase 0: ASR and utility together](phase-0-measurement/asr-and-utility-together/README.md) (baseline only); Phase 1, Phase 2 planned |
| LLM02:2026 Sensitive Information Disclosure | Phase 5 planned |
| LLM03:2026 Excessive Agency | Phase 3 planned |
| LLM04:2026 Supply Chain | Phase 4 planned |
| LLM05:2026 Data and Model Poisoning | Phase 2 planned |
| LLM06:2026 Unbounded Consumption | Phase 6 planned |
| LLM07:2026 Misinformation | Measured in [GenAI Engineering Benchmarks](https://github.com/NurgulKaryagis/genai-engineering-benchmarks) (faithfulness / hallucination); cross-referenced, not duplicated |
| LLM08:2026 Hidden Context Exposure | Phase 5 planned |
| LLM09:2026 Vector and Embedding Weaknesses | Phase 2 planned |
| LLM10:2026 Improper Output Handling | Phase 7 planned |

## Roadmap

| Phase | Topic | OWASP 2026 | Status |
| ----- | ----- | ---------- | ------ |
| 0 | Measurement: ASR with utility, static vs adaptive attacks, detector metrics | — | In progress (1 of 3 core experiments) |
| 1 | Prompt injection defenses: spotlighting, detectors, LLM guardrails, layering | LLM01 | Planned |
| 2 | Indirect injection and poisoning in RAG | LLM01, LLM05, LLM09 | Planned |
| 3 | Tools and excessive agency: approval gates, least privilege | LLM03 | Planned |
| 4 | Identity and supply chain: leaked credentials, sandbox boundaries | LLM04 | Planned |
| 5 | Sensitive information disclosure and hidden-context leakage | LLM02, LLM08 | Planned |
| 6 | Unbounded consumption: rate limits, budget caps, loop guards | LLM06 | Planned |
| 7 | Improper output handling: sanitizing LLM output before downstream sinks | LLM10 | Planned |
| 8 | Runtime detection of attack traffic and abnormal agent behavior | — | Planned |
| 9 | Governance and framework mapping (OWASP, MITRE ATLAS, NIST AI RMF, ISO/IEC 42001, EU AI Act) | — | Planned |

## Repository layout

```text
shared/harness/       measurement harness used by every experiment (ASR + utility scoring, LLM judge, API call logging)
shared/targets/       reusable targets (mock email + calendar workspace, undefended LLM agent)
phase-N-<topic>/      one folder per experiment: README, hypothesis, design, code, results
```

Raw episode logs are not committed: they contain attack text and full transcripts.

## Reproduce

Python 3.12 (standard library only, no packages to install) and an OpenAI API key:

```bash
echo "OPENAI_API_KEY=..." > .env
```

Then follow the "Reproduce" section of the experiment's README.

## Shared Harness Changes

Changes to `shared/harness/` are recorded here and flagged when they could affect earlier results.

- **2026-10-20 — Initial harness (Phase 0).** Episode runner scoring utility and ASR on the same episodes from the final environment state; exposure tracking; errors recorded and never counted as blocked attacks; free-text normalization rules for the code check; LLM judge; OpenAI Responses API client with per-call cost logging. No earlier results exist, so nothing is affected.

## License

[MIT](LICENSE). The injection template reproduced from AgentDojo keeps its own MIT notice in the file that contains it.
