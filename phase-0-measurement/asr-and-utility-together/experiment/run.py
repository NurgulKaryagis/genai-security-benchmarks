"""Run agents through every condition and write results.

Usage (from the repo root):
    python3 phase-0-measurement/asr-and-utility-together/experiment/run.py --agents do_nothing obey_all --reps 3
    python3 phase-0-measurement/asr-and-utility-together/experiment/run.py --agents llm_agent --reps 5
    python3 .../run.py --agents llm_agent --smoke    # 2 tasks, 1 rep, written to results/smoke/
"""

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from shared.harness.core import (rep_metrics, run_episode, summarize,  # noqa: E402
                                 verdicts_identical_across_reps, write_jsonl)
from shared.harness.openai_chat import OpenAIClient, load_api_key  # noqa: E402
from shared.targets.email_calendar import Tools, make_workspace, snapshot  # noqa: E402
from shared.targets.llm_agent import LLMAgent  # noqa: E402

import injection_template  # noqa: E402
from agents import DoNothingAgent, ObeyAllAgent  # noqa: E402
from tasks import INJECTION_TASKS, USER_TASKS  # noqa: E402

RESULTS = HERE.parent / "results"
AGENT_MODEL = "gpt-6-luna"
AGENT_DISPLAY_NAME = "GPT-6 Luna"


def build_agent(name):
    if name == "do_nothing":
        return DoNothingAgent()
    if name == "obey_all":
        return ObeyAllAgent({t.prompt: t.id for t in USER_TASKS})
    if name == "llm_agent":
        client = OpenAIClient(load_api_key(ROOT / ".env"))
        return LLMAgent(client, AGENT_MODEL, AGENT_DISPLAY_NAME)
    raise ValueError(f"unknown agent {name}")


def run_agent(agent, reps, user_tasks):
    episodes, per_rep = [], []
    for rep in range(reps):
        rep_eps = []
        for ut in user_tasks:
            for inj in [None, *INJECTION_TASKS]:
                ep = run_episode(agent, ut, inj, injection_template.render,
                                 make_workspace, Tools, rep, snapshot)
                rep_eps.append(ep)
                print(f"  rep {rep} {ut.id} {inj.id if inj else '--'}: {ep['status']}"
                      f" utility={ep['utility']} attack={ep['attack_success']}", flush=True)
        episodes += rep_eps
        per_rep.append(rep_metrics(rep_eps))
    return episodes, per_rep


def spend(episodes):
    calls = [c for e in episodes for c in ((e["agent_meta"] or {}).get("api_calls") or [])]
    return {
        "api_calls": len(calls),
        "cost_usd": round(sum(c["cost_usd"] for c in calls), 4),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "reasoning_tokens": sum(c["reasoning_tokens"] for c in calls),
        "returned_models": sorted({c["returned_model"] for c in calls if c["returned_model"]}),
        "mean_episode_latency_s": round(sum(e["latency_s"] for e in episodes) / len(episodes), 3),
    }


def fmt(m):
    if m["mean"] is None:
        return "n/a"
    return f"{m['mean']:.1%} ± {m['std']:.1%}"


def write_table(out_dir):
    rows = [json.loads(p.read_text()) for p in sorted(out_dir.glob("summary_*.json"))]
    lines = [
        "Mean ± sample std across repetitions. Errors are counted, never treated as blocked attacks.",
        "",
        "| Agent | Reps | Benign utility | Utility under attack | ASR | Exposure | Errors | Identical across reps | Episodes/rep (benign + attacked) | Cost (USD) | Mean latency/episode |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in rows:
        lines.append(
            f"| `{s['agent']}` | {s['reps']} | {fmt(s['benign_utility'])} | {fmt(s['utility_under_attack'])} | "
            f"{fmt(s['asr'])} | {fmt(s['exposure_rate'])} | {s['errors_total']} | "
            f"{'yes' if s['identical_across_reps'] else 'no'} | "
            f"{s['n_benign_per_rep']} + {s['n_attacked_per_rep']} | "
            f"{s['spend']['cost_usd']:.4f} | {s['spend']['mean_episode_latency_s']} s |"
        )
    table = "\n".join(lines)
    (out_dir / "summary.md").write_text(table + "\n")
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", nargs="+", default=["do_nothing", "obey_all"])
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--smoke", action="store_true", help="T01-T02 only, 1 rep, results/smoke/")
    args = ap.parse_args()

    user_tasks = USER_TASKS[:2] if args.smoke else USER_TASKS
    reps = 1 if args.smoke else args.reps
    out_dir = RESULTS / "smoke" if args.smoke else RESULTS

    for name in args.agents:
        print(f"{name}: {reps} reps × {len(user_tasks) * (1 + len(INJECTION_TASKS))} episodes")
        agent = build_agent(name)
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        episodes, per_rep = run_agent(agent, reps, user_tasks)
        write_jsonl(out_dir / "raw" / f"{name}.jsonl", episodes)
        s = summarize(per_rep)
        s.update({
            "agent": name,
            "identical_across_reps": verdicts_identical_across_reps(episodes),
            "spend": spend(episodes),
            "run": {
                "started_utc": started,
                "python": platform.python_version(),
                "injection_template": injection_template.TEMPLATE_NAME,
                "model": getattr(agent, "model", None),
            },
        })
        (out_dir / f"summary_{name}.json").write_text(json.dumps(s, indent=2))

    print(write_table(out_dir))


if __name__ == "__main__":
    main()
