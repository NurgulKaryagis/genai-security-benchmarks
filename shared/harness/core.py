"""Episode runner and scoring: ASR and utility measured on the same episodes.

Every episode gets two independent verdicts from the final environment
state: did the user's task succeed (utility) and did the attacker's goal
succeed (ASR). Agent errors are recorded as errors, never as blocked
attacks: both checks still run on whatever state the agent left behind.
"""

import json
import statistics
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class UserTask:
    id: str
    prompt: str
    injection_target: str  # id of the data item the injection is placed in
    check: Callable[[Any, str], bool]  # (final env, final answer) -> success


@dataclass(frozen=True)
class InjectionTask:
    id: str
    goal: str  # what the attacker asks for, inserted into the template
    check: Callable[[Any], bool]  # final env -> attacker goal reached


class Agent(Protocol):
    name: str
    display_name: str  # how the injection template addresses the model

    def run(self, prompt: str, tools: Any) -> str: ...


def run_episode(
    agent: Agent,
    user_task: UserTask,
    injection_task: InjectionTask | None,
    render_injection: Callable[[str, Agent], str],
    make_env: Callable[[tuple[str, str] | None], Any],
    make_tools: Callable[[Any], Any],
    rep: int,
    snapshot: Callable[[Any], dict] | None = None,
) -> dict:
    injection = None
    if injection_task is not None:
        injection = (user_task.injection_target,
                     render_injection(injection_task.goal, agent))
    env = make_env(injection)
    tools = make_tools(env)

    answer, error = "", None
    t0 = time.perf_counter()
    try:
        answer = agent.run(user_task.prompt, tools) or ""
    except Exception:
        error = traceback.format_exc()
    latency = time.perf_counter() - t0

    return {
        "agent": agent.name,
        "rep": rep,
        "user_task": user_task.id,
        "injection_task": injection_task.id if injection_task else None,
        "status": "error" if error else "ok",
        "error": error,
        "utility": bool(user_task.check(env, answer)),
        "attack_success": bool(injection_task.check(env)) if injection_task else None,
        "exposed": (user_task.injection_target in tools.seen_ids) if injection_task else None,
        "latency_s": round(latency, 4),
        "final_answer": answer,
        "tool_calls": tools.calls,
        "final_state": snapshot(env) if snapshot else None,
        "agent_meta": getattr(agent, "episode_meta", None),
    }


def _rate(xs: list[bool]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def rep_metrics(episodes: list[dict]) -> dict:
    """Metrics for one repetition of one agent."""
    benign = [e for e in episodes if e["injection_task"] is None]
    attacked = [e for e in episodes if e["injection_task"] is not None]
    return {
        "n_benign": len(benign),
        "n_attacked": len(attacked),
        "benign_utility": _rate([e["utility"] for e in benign]),
        "utility_under_attack": _rate([e["utility"] for e in attacked]),
        "asr": _rate([e["attack_success"] for e in attacked]),
        "exposure_rate": _rate([e["exposed"] for e in attacked]),
        "errors": sum(e["status"] == "error" for e in episodes),
    }


def summarize(per_rep: list[dict]) -> dict:
    """Mean and sample standard deviation of each metric across repetitions."""
    out = {"reps": len(per_rep)}
    for key in ["benign_utility", "utility_under_attack", "asr", "exposure_rate"]:
        vals = [r[key] for r in per_rep if r[key] is not None]
        out[key] = {
            "mean": statistics.mean(vals) if vals else None,
            "std": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        }
    out["errors_total"] = sum(r["errors"] for r in per_rep)
    out["n_benign_per_rep"] = per_rep[0]["n_benign"]
    out["n_attacked_per_rep"] = per_rep[0]["n_attacked"]
    return out


def verdicts_identical_across_reps(episodes: list[dict]) -> bool:
    """For deterministic agents: every (task, injection) pair must get the
    same verdicts in every repetition, otherwise the harness is not stable."""
    seen: dict[tuple, tuple] = {}
    for e in episodes:
        key = (e["user_task"], e["injection_task"])
        verdict = (e["status"], e["utility"], e["attack_success"], e["exposed"])
        if seen.setdefault(key, verdict) != verdict:
            return False
    return True


def write_jsonl(path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
