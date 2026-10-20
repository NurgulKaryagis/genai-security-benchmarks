# Hypothesis (written before any run)

Recorded: 2026-10-19

1. **Do-nothing agent:** ASR 0, utility 0 (both benign and under attack).
   Reason: it calls no tools, so neither the attacker's goal nor the
   user's task is ever carried out.

2. **Obey-everything agent:** ASR 100, benign utility 100, utility under
   attack 0.
   Reason: under attack it follows the attacker's instruction instead of
   the user's task.

3. **Scorer:** a deterministic code check is more accurate than an LLM
   judge. The ASR value itself does not change; only its reliability
   does.
