Mean ± sample std across repetitions. Errors are counted, never treated as blocked attacks.

| Agent | Reps | Benign utility | Utility under attack | ASR | Exposure | Errors | Identical across reps | Episodes/rep (benign + attacked) | Cost (USD) | Mean latency/episode |
|---|---|---|---|---|---|---|---|---|---|---|
| `do_nothing` | 3 | 0.0% ± 0.0% | 0.0% ± 0.0% | 0.0% ± 0.0% | 0.0% ± 0.0% | 0 | yes | 12 + 24 | 0.0000 | 0.0 s |
| `llm_agent` | 5 | 100.0% ± 0.0% | 98.3% ± 2.3% | 0.0% ± 0.0% | 91.7% ± 0.0% | 0 | no | 12 + 24 | 0.0627 | 7.778 s |
| `obey_all` | 3 | 100.0% ± 0.0% | 100.0% ± 0.0% | 100.0% ± 0.0% | 100.0% ± 0.0% | 0 | yes | 12 + 24 | 0.0000 | 0.0 s |
