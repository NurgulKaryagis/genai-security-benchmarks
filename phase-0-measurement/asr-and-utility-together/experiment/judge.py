"""Score recorded llm_agent episodes with the LLM judge and compare its
verdicts with the code check.

Usage (from the repo root):
    python3 phase-0-measurement/asr-and-utility-together/experiment/judge.py
    python3 .../judge.py --smoke     # judges results/smoke/raw/llm_agent.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from shared.harness.core import write_jsonl  # noqa: E402
from shared.harness.llm_judge import judge_episode  # noqa: E402
from shared.harness.openai_chat import APIError, OpenAIClient, load_api_key  # noqa: E402

from tasks import INJECTION_TASKS, USER_TASKS  # noqa: E402

JUDGE_MODEL = "gpt-6.1-sol"
RESULTS = HERE.parent / "results"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    out_dir = RESULTS / "smoke" if args.smoke else RESULTS

    prompts = {t.id: t.prompt for t in USER_TASKS}
    goals = {t.id: t.goal for t in INJECTION_TASKS}
    episodes = [json.loads(l) for l in open(out_dir / "raw" / "llm_agent.jsonl")]
    client = OpenAIClient(load_api_key(ROOT / ".env"))

    judged = []
    for i, ep in enumerate(episodes):
        goal = goals.get(ep["injection_task"])
        try:
            verdict, record = judge_episode(client, JUDGE_MODEL, prompts[ep["user_task"]],
                                            goal, ep, ep["final_state"])
        except APIError as e:
            verdict, record = {"error": str(e)}, None
        judged.append({
            "episode_index": i, "rep": ep["rep"], "user_task": ep["user_task"],
            "injection_task": ep["injection_task"], "agent_status": ep["status"],
            "code_utility": ep["utility"], "code_attack": ep["attack_success"],
            "judge": verdict, "judge_call": record,
        })
        print(f"  {i:3d} {ep['user_task']} {ep['injection_task'] or '--'}: "
              f"code=({ep['utility']},{ep['attack_success']}) "
              f"judge=({verdict.get('user_task_completed')},{verdict.get('attacker_goal_achieved')})",
              flush=True)
    write_jsonl(out_dir / "raw" / "llm_agent_judged.jsonl", judged)

    ok = [j for j in judged if "error" not in j["judge"]]
    util_agree = sum(j["code_utility"] == j["judge"]["user_task_completed"] for j in ok)
    att = [j for j in ok if j["injection_task"]]
    att_agree = sum(j["code_attack"] == j["judge"]["attacker_goal_achieved"] for j in att)
    calls = [j["judge_call"] for j in judged if j["judge_call"]]
    summary = {
        "judge_model": JUDGE_MODEL,
        "episodes": len(judged),
        "judge_errors": len(judged) - len(ok),
        "utility_agreement": f"{util_agree}/{len(ok)}",
        "attack_agreement": f"{att_agree}/{len(att)}",
        "disagreements": [j["episode_index"] for j in ok
                          if j["code_utility"] != j["judge"]["user_task_completed"]
                          or (j["injection_task"] and j["code_attack"] != j["judge"]["attacker_goal_achieved"])],
        "cost_usd": round(sum(c["cost_usd"] for c in calls), 4),
        "returned_models": sorted({c["returned_model"] for c in calls if c["returned_model"]}),
    }
    (out_dir / "judge_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
