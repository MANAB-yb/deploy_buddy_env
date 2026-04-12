import asyncio
import os
import json
from typing import List, Optional

from openai import OpenAI
from deploy_buddy import DeployBuddyAction, DeployBuddyEnv


# ---------- ENV CONFIG ----------
IMAGE_NAME = os.getenv("IMAGE_NAME")
API_KEY = os.getenv("API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

TASK_NAME = ["task1" , "task2", "task3", "task4", "task5"]
# TASK_NAME = ["task2"]

BENCHMARK = "deploy_buddy"

MAX_STEPS = 10
TEMPERATURE = 0.3
MAX_TOKENS = 200
MAX_LESSONS_CHARS = 1000


# ---------- SYSTEM PROMPT ----------
SYSTEM_PROMPT = """
You are an SRE agent responsible for diagnosing and fixing production incidents.

You will receive:
- metrics (numerical signals)
- logs (system behavior hints)
- alerts (symptoms)

Your job is to:
1. Carefully analyze ALL signals
2. Identify the MOST LIKELY root cause
3. Take ONE action that directly addresses the root cause

Guidelines:
- DO NOT make unnecessary configuration changes
- Logs often contain the real root cause — prioritize them
- Repeated failures or restarts indicate deeper issues
- If a recent change caused instability, consider reverting it
- Avoid unnecessary actions — efficiency matters

Load Balancer Configuration:
- This can be used to scale up/down the component as well if we want to deploy some more or less nodes, load balancer will take care of
deploying and destroying based on the config
- The system is deployed across multiple availability zones.
- Traffic is distributed based on the number of replicas in each zone.
- Ensure the configuration remains balanced


Valid actions STRICTLY MAINTAIN THIS LIST:
1. change_lb_config(target=<api|db|task_runner>, value=<json>)
2. restart_service(target=<api|db|task_runner>)
3. revert_version(target=<api|db|task_runner>)
4. wait

Action:
- change_lb_config:
  Adjusts the number of replicas in each availability zone for the specified service.
  The `value` must be a JSON object where:
    - Keys represent zone names (e.g., "zone_a", "zone_b", "zone_c")
    - Values represent the desired number of replicas (non-negative integers)
    - When modifying the load balancer configuration, distribute replicas as evenly as possible across all reachable zones. Consider unreachable zones as unavailable, equivalent to having zero replicas.
Examples:
- If zone_b is unreachable:
  {
    "action_type": "change_lb_config",
    "target": "api",
    "value": {
      "zone_a": 1,
      "zone_b": 0,
      "zone_c": 1
    }
  }

Reverting a version is a high-impact action and should NOT be used blindly.
Only use revert_version if there is clear evidence of a recent change causing instability.
Evidence may include:
- logs mentioning upgrades, deployments, or version changes
- errors starting after a change event
- repeated failures following a version update
If there is NO indication of a recent change, avoid reverting.
But if version change is there and errors are present after version change and restarts not helping new version can be incompetenet or buggy
Unnecessary reverts can disrupt a stable system and should be avoided.

Before taking action:
- Identify which component is the SOURCE of the issue
- Distinguish between root cause vs downstream impact
- Always act on the ROOT CAUSE component, not the symptom.

Output STRICTLY JSON: If your output is not valid JSON, your answer is considered WRONG.

{
  "action_type": "...",
  "target": "...",
  "value": <json object or null>
}

DO NOT include any explanation. ONLY output valid JSON.
"""


# ---------- LOGGING ----------
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

import re
import json

def extract_json(text: str):
    try:
        # direct parse
        return json.loads(text)
    except:
        pass

    # try to extract JSON block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return None

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score} rewards={rewards_str}", flush=True)


# ---------- PROMPT ----------
def build_prompt(obs, history) -> str:
    history_block = "\n".join(history[-3:]) if history else "None"

    return f"""
=== OBSERVATION ===

Metrics:
{json.dumps(obs.metrics, indent=2)}

Alerts:
{obs.alerts}

Logs (most recent last):
{obs.logs[-8:]}

Previous Actions:
{history_block}

===================

What is the SINGLE best action to fix the system?

Remember:
- Identify root cause
- Avoid unnecessary scaling
- Prefer precise fixes over brute force
"""


# ---------- MODEL ----------
def get_action(client: OpenAI, obs, history):
    try:
        system_prompt = SYSTEM_PROMPT
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": build_prompt(obs, history)},
            ],
            
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        text = completion.choices[0].message.content.strip()
        action_dict = extract_json(text)

        if action_dict is None:
            raise ValueError("Invalid JSON")

        return DeployBuddyAction(**action_dict), text

    except Exception as e:
        print(f"[DEBUG] Model error: {e}", flush=True)

        # If LLM failed to provide response, wait for the next step
        return DeployBuddyAction(
            action_type="wait",
            target=None,
            value=None
        ), "fallback_action"


# ---------- MAIN ----------
async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    env = await DeployBuddyEnv.from_docker_image(IMAGE_NAME)

    try:
        global_lessons = ""
        for task in TASK_NAME:
            rewards: List[float] = []
            history: List[str] = []
            steps_taken = 0
            success = False

            log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

            try:
                result = await env.reset(taskId=task)
                # print(result)


                for step in range(1, MAX_STEPS + 1):
                    obs = result.observation

                    action, action_str = get_action(client, obs, history)

                    result = await env.step(action=action)

                    reward = result.reward or 0.0
                    done = result.done

                    rewards.append(reward)
                    steps_taken = step

                    log_step(step, action_str, reward, done, None)

                    history.append(f"Step {step}: {action_str} -> {reward:.2f}")

                    if done:
                        success = True
                        break

                # if not solved explicitly
                if not success:
                    success = result.done

            finally:
                # Finally grade it
                dummy_action = DeployBuddyAction(
                                action_type="wait",
                                target=None,
                                value=None,
                                grade=True
                            )
                grade_data = await env.step(action=dummy_action)
                grade = grade_data.observation.grades_data

                score = grade['score']
                # print(f"reason is {grade['reason']}")
                
                reflection_prompt = f"""
                    TASK FINISHED.
                    Score: {grade['score']}/1.0
                    Reason: {grade['reason']}

                    Extract 3 concise operational lessons.

                    Rules:
                    - Each lesson must be specific and actionable
                    - No generic advice
                    - Focus on root-cause identification and correct actions
                    - Keep each lesson under 15 words

                    Output as bullet points.
                    """
                
                # Add the prompt to the existing conversation
                messages = [{"role": "user", "content": reflection_prompt}]
                try:
                    reflection_result = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages
                    )
                    global_lessons += reflection_result.choices[0].message.content + "\n"
                    global_lessons = global_lessons[-MAX_LESSONS_CHARS:]
                except Exception as ex:
                    pass
                    # print("failed to extract lessons from prev test due to ")
                    # print(ex)
                
                log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close error: {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())