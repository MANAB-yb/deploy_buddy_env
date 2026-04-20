---
title: Deploy Buddy Environment Server
emoji: 🎚️
colorFrom: pink
colorTo: gray
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

## 🌟 Deploy Buddy

**Deploy Buddy** is a realistic Site Reliability Engineering (SRE) simulation environment designed to evaluate intelligent agents in handling production-like incidents. Inspired by real-world operational challenges, each scenario requires agents to go beyond single-step fixes and instead perform **multi-step decision-making** to restore system stability.

Each interaction step represents a distinct challenge for the agent, where **rewards** are granted for effective decisions and **penalties** are applied for harmful or ineffective actions. These consequences may introduce new system states, encouraging the agent to reason iteratively and adapt its strategy over time.

To further emulate real-world operational constraints, Deploy Buddy incorporates **cost-awareness** by penalizing over-provisioned or idle resources. This incentivizes agents to prioritize **cost-effective solutions** while maintaining system reliability and performance.


### Key Highlights
- **Real-World Actions**: Agents perform practical operational steps such as scaling services, restarting components, reverting faulty deployments, and redistributing replicas.
- **Multi-Step RL Interaction**: Many incidents require a sequence of coordinated actions rather than a single fix, encouraging long-horizon reasoning.
- **Root Cause Analysis**: Scenarios are designed to differentiate between *symptoms* and the *actual underlying problem*.
- **Decision Trade-offs**: Agents must balance reliability, performance, and cost, mirroring real SRE decision-making.
- **System-Level Reasoning**: Tasks capture the interdependencies of distributed systems, requiring holistic understanding.
- **Progressive Difficulty**: Incidents range from straightforward bottlenecks to complex cascading failures



---

## 🧩 Tasks

Deploy Buddy contains **five incident scenarios**, each crafted to test different aspects of operational intelligence and decision-making.

### 🟢 Task 1: Easy — Database Bottleneck

**Problem**
- Database CPU usage is critically high and connection pools are exhausted.

**Symptoms**
- Increased API latency.
- Elevated database CPU and connection metrics.

**Root Cause**
- Database overload due to increased traffic.

**Correct Action**
- ✅ **Scale the database** to handle the additional load.

**Common Incorrect Actions**
- ❌ Scaling the API service.
- ❌ Restarting unrelated services.

**Learning Objective**
> *Identify the true bottleneck and scale the correct component.*

---

### 🟡 Task 2: Medium — Incompatible version change Deployment

**Problem**
- Most of the API Calls by api server to task runner are failing with Bad request error

**Clues**
- Logs indicate a **recent version upgrade**.
- error rate in api server and task runner services increasing with time

**Root Cause**
- A **recent version pathcing in task runner service is incompatible**

**Correct Action**
- ✅ **Revert the Task Runner to the previous stable version.**

**Common Incorrect Actions**
- ❌ Scaling the Task Runner (does not fix the bug and increases cost).
- ❌ Restarting services without reverting the version.

**Learning Objective**
> *Not all incidents are solved by scaling—sometimes the issue lies in faulty/incompatible code.*


---

### 🟡 Task 3: Medium — Memory Leak After Deployment

**Problem**
- Task Runner services exhibit continuously increasing memory usage and frequent crashes.

**Clues**
- Logs indicate a **recent version upgrade**.
- Memory usage grows steadily over time.

**Root Cause**
- A **memory leak introduced in the latest deployment**, not a resource shortage.

**Correct Action**
- ✅ **Revert the Task Runner to the previous stable version.**

**Common Incorrect Actions**
- ❌ Scaling the Task Runner (does not fix the bug and increases cost).
- ❌ Restarting services without reverting the version.

**Learning Objective**
> *Not all incidents are solved by scaling—sometimes the issue lies in faulty code.*

---

---

### 🟠 Task 4: Medium-Hard — Availability Zone Failure

**Problem**
- One availability zone becomes unreachable, reducing system redundancy and resilience.

**Symptoms**
- Reduced replica count in the affected zone.
- Increased load on remaining zones.
- Potential risk to service availability.

**Root Cause**
- Infrastructure failure leading to a **zone outage**.

**Correct Action**
- ✅ **Redistribute and scale replicas in healthy zones** to maintain high availability.

**Common Incorrect Actions**
- ❌ Scaling replicas in the unreachable zone.
- ❌ Restarting services without addressing capacity constraints.

**Learning Objective**
> *Ensure resilience by maintaining redundancy and intelligently redistributing resources.*

---

### 🔴 Task 5: Hard — Cascading Failure from Retry Storm

**Problem**
- Too many retry API Calls causing cascading failures across services.

**Symptoms**
- Increasing API error rates.
- Overloaded Task Runners.
- System instability due to repeated retries.

**Root Cause**
- A **feedback loop between the API and Task Runner**, where retries amplify system load.

**Correct Multi-Step Actions**
1. ✅ **Scale the Task Runner** to handle the backlog.
2. ✅ **Restart the API Server** to break the retry loop.

**Common Incorrect Actions**
- ❌ Scaling down the Task Runner.
- ❌ Reverting service versions.
- ❌ Restarting unrelated components.

**Learning Objective**
> *Understand system interactions and execute coordinated multi-step mitigation.*



---

## 🧠 Skills Evaluated

| Capability | Description |
|-----------|-------------|
| **Root Cause Analysis** | Distinguishing between symptoms and underlying issues. |
| **Real-World Actions** | Executing operational steps like scaling, restarting, and reverting deployments. |
| **Multi-Step Decision Making** | Performing coordinated sequences of actions to resolve incidents. |
| **System-Level Reasoning** | Understanding dependencies across distributed services. |
| **Decision Trade-offs** | Balancing reliability, performance, and cost. |
| **High Availability & Resilience** | Maintaining service continuity during infrastructure failures. |

---

> **Deploy Buddy enacts real-world SRE operations**, providing a meaningful benchmark for evaluating intelligent agents capable of managing production-scale distributed systems.

## Key Lessons

* Don’t blindly scale
* Prioritize both metrics and logs, and current state
* Identify root cause, not symptoms
* Systems fail in chains, not isolation
* Right action > more resources

## Goals
* Incident diagnosis
* Infrastructure decision-making
* Real-world system failures
* Most cost effective Solutions

## 👀 Observation Space

The **observation space** in Deploy Buddy represents the real-time state of a distributed production system. It provides agents with structured telemetry, logs, alerts, and infrastructure-level details required for **root cause analysis**, **multi-step decision-making**, and **cost-effective remediation**.

Each interaction with the environment returns a JSON object containing the current system state, the reward for the previous action, and whether the episode has terminated.

### 📦 Observation Structure

```json
{
  "observation": {
    "metrics": { ... },
    "logs": [ ... ],
    "alerts": [ ... ],
    "step": 0,
    "internal_state": { ... },
    "task_id": 0,
    "grades_data": {}
  },
  "reward": 0.0,
  "done": false
}
```


📊 1. Metrics

The metrics field contains high-level telemetry similar to what an SRE would observe from monitoring systems such as Prometheus, Datadog, or CloudWatch. These metrics help the agent quickly identify anomalies and potential bottlenecks.

| Field | Type | Description |
| :--- | :--- | :--- |
| `api_latency` | float | Average API response latency in milliseconds. |
| `api_error` | float | API error rate (0–1). |
| `api_free_memory` | float | Available memory for the API service (GB). |
| `db_cpu` | float | Database CPU utilization percentage. |
| `db_connections` | float | Percentage of database connections in use. |
| `db_latency` | float | Database query latency in milliseconds. |
| `db_disk_availability` | float | Available disk space for the database (GB). |
| `task_runner_cpu` | float | CPU utilization of the Task Runner service. |
| `task_runner_disk` | float | Available disk space for the Task Runner (GB). |
| `task_runner_free_memory` | float | Available memory for the Task Runner (GB). |

2. Logs

The logs field provides textual clues about system behavior, often pointing toward the root cause of an incident.

🚨 3. Alerts

The alerts field simulates monitoring alerts that signal abnormal system conditions. These are high-level indicators guiding the agent toward problematic components.

🏗️ 5. Internal State

The internal_state provides a detailed, service-level view of the system. While metrics offer aggregated insights, this section exposes deeper infrastructure details necessary for precise remediation actions.

Each service (api, db, task_runner) includes performance metrics, deployment versions, and load balancer configurations across availability zones.

| Field | Type | Description |
| :--- | :--- | :--- |
| `api_latency` | float | Average API response latency in milliseconds. |
| `api_error` | float | API error rate (0–1). |
| `api_free_memory` | float | Available memory for the API service (GB). |
| `db_cpu` | float | Database CPU utilization percentage. |
| `db_connections` | float | Percentage of database connections in use. |
| `db_latency` | float | Database query latency in milliseconds. |
| `db_disk_availability` | float | Available disk space for the database (GB). |
| `task_runner_cpu` | float | CPU utilization of the Task Runner service. |
| `task_runner_disk` | float | Available disk space for the Task Runner (GB). |
| `task_runner_free_memory` | float | Available memory for the Task Runner (GB). |
| `latency` | float | Service-specific latency in milliseconds. |
| `cpu` | float | CPU utilization percentage. |
| `error` | float | Error rate (0–1). |
| `free_memory` | float | Available memory (GB). |
| `connections` | int | Number of active connections (API/DB only). |
| `disk_available` | float | Available disk space (GB). |
| `version` | string | Currently deployed software version. |
| `load_balancer` | object | Distribution of replicas across availability zones. |


### sample Example
```json
{
  "observation": {
    "metrics": {
      "api_latency": 208.0,
      "api_error": 0.02,
      "api_free_memory": 4.0,
      "db_cpu": 90.0,
      "db_connections": 95.0,
      "db_latency": 607.0,
      "db_disk_availability": 950.0,
      "task_runner_cpu": 45.0,
      "task_runner_disk": 14.0,
      "task_runner_free_memory": 4.0
    },
    "logs": [
      "DB connection pool exhausted"
    ],
    "alerts": [
      "High CPU usage in db",
      "High DB Latency alert"
    ],
    "step": 0,
    "internal_state": {
      "api": {
        "latency": 200,
        "cpu": 45,
        "error": 0.02,
        "free_memory": 4,
        "connections": 50,
        "version": "v1",
        "load_balancer": {
          "zone_a": { "replicas": 1, "reachable": true },
          "zone_b": { "replicas": 1, "reachable": true },
          "zone_c": { "replicas": 0, "reachable": null }
        }
      },
      "db": {
        "cpu": 90,
        "connections": 95,
        "latency": 600,
        "disk_available": 950,
        "free_memory": 8,
        "version": "v1",
        "load_balancer": {
          "zone_a": { "replicas": 1, "reachable": true },
          "zone_b": { "replicas": 0, "reachable": null },
          "zone_c": { "replicas": 0, "reachable": null }
        }
      },
      "task_runner": {
        "latency": 200,
        "cpu": 45,
        "error": 0.02,
        "free_memory": 4,
        "disk_available": 14,
        "version": "v1",
        "load_balancer": {
          "zone_a": { "replicas": 1, "reachable": true },
          "zone_b": { "replicas": 1, "reachable": true },
          "zone_c": { "replicas": 0, "reachable": null }
        }
      }
    },
    "task_id": 0,
    "grades_data": {}
  },
  "reward": 0.0,
  "done": false
} 
```



## 🏆 Reward Evaluation
Each action taken by the agent is evaluated based on its **impact on system health**, **progress toward incident resolution**, and **cost efficiency**.

---

### 🌟 Key Principles

| Principle | Description |
|----------|-------------|
| **Heuristic-Based** | Rewards are derived from domain-informed rules reflecting real SRE practices. |
| **Multi-Step Evaluation** | Each action is evaluated within the context of a sequential decision-making process. |
| **Root Cause Alignment** | Actions addressing the true root cause receive higher rewards. |
| **Cost Awareness** | Over-provisioning or idle resources incur penalties to encourage efficient solutions. |
| **Safety-Oriented** | Harmful or destabilizing actions are penalized to discourage risky behavior. |

---

### 🧩 Reward Components

The total reward at each step is computed as a combination of several interpretable components:

| Component | Description | Example |
|----------|-------------|---------|
| **Correct Action Reward** | Granted when the agent performs an action aligned with the root cause. | Scaling the database during a DB bottleneck. |
| **Incorrect Action Penalty** | Applied when the action does not address the issue or worsens the system. | Scaling the API instead of the database. |
| **System Health Improvement** | Rewards measurable improvements in metrics such as latency or error rates. | Reduction in API latency after remediation. |
| **Multi-Step Progress** | Incremental rewards for actions that move the system toward resolution. | Scaling before restarting to stabilize the system. |
| **Cost Efficiency Penalty** | Penalizes over-provisioned or idle resources. | Excess replicas after incident resolution. |
| **Stability Bonus** | Granted when the system reaches a healthy and stable state. | All services operating within normal thresholds. |
| **Time Penalty** | Encourages faster resolution by penalizing unnecessary steps. | Idle or ineffective actions. |

---

### 🧮 Reward Calculation

The reward is computed as a weighted sum of the above components:

```text
Reward =
  + Correct_Action_Bonus
  + System_Health_Improvement
  + Stability_Bonus
  - Incorrect_Action_Penalty
  - Cost_Penalty
  - Time_Penalty
```


## Baseline Inference Scores

| **Tier** | **Task ID** | **Mean Score** | **Max Score** |
| :--- | :--- | :--- | :--- |
| Easy | `task_1` | 0.95 | 0.95 |
| Medium | `task_2` | 0.50 | 0.80 |
| Medium | `task_3` | 0.60 | 0.85 |
| Medium-Hard | `task_4` | 0.50 | 0.75 |
| Hard | `task_5` | 0.47 | 0.66 |
| **OVERALL** | — | **0.64** | **0.82** |

---

## 🏗️ Architecture


Client → Action → Server → Simulation → Observation → Client


* *Client* → Sends actions
* *Server (FastAPI)* → Simulates system
* *Models* → Define actions & observations
* *Docker* → Runs environment

---


## Building the Docker Image

Before using the environment, you need to build the Docker image:

```bash
# From project root
docker build -t deploy_buddy-env:latest -f server/Dockerfile .
```

## Deploying to Hugging Face Spaces

You can easily deploy your OpenEnv environment to Hugging Face Spaces using the `openenv push` command:

```bash
# From the environment directory (where openenv.yaml is located)
openenv push

# Or specify options
openenv push --namespace my-org --private
```

The `openenv push` command will:
1. Validate that the directory is an OpenEnv environment (checks for `openenv.yaml`)
2. Prepare a custom build for Hugging Face Docker space (enables web interface)
3. Upload to Hugging Face (ensuring you're logged in)

### Prerequisites

- Authenticate with Hugging Face: The command will prompt for login if not already authenticated

### Options

- `--directory`, `-d`: Directory containing the OpenEnv environment (defaults to current directory)
- `--repo-id`, `-r`: Repository ID in format 'username/repo-name' (defaults to 'username/env-name' from openenv.yaml)
- `--base-image`, `-b`: Base Docker image to use (overrides Dockerfile FROM)
- `--private`: Deploy the space as private (default: public)

### Examples

```bash
# Push to your personal namespace (defaults to username/env-name from openenv.yaml)
openenv push

# Push to a specific repository
openenv push --repo-id my-org/my-env

# Push with a custom base image
openenv push --base-image ghcr.io/meta-pytorch/openenv-base:latest

# Push as a private space
openenv push --private

# Combine options
openenv push --repo-id my-org/my-env --base-image custom-base:latest --private
```

After deployment, your space will be available at:
`https://huggingface.co/spaces/<repo-id>`

The deployed space includes:
- **Web Interface** at `/web` - Interactive UI for exploring the environment
- **API Documentation** at `/docs` - Full OpenAPI/Swagger interface
- **Health Check** at `/health` - Container health monitoring
- **WebSocket** at `/ws` - Persistent session endpoint for low-latency interactions

## Environment Details

### Action
**DeployBuddyAction**: Contains a single field
- `message` (str) - The message to echo back

### Observation
**DeployBuddyObservation**: Contains the echo response and metadata
- `echoed_message` (str) - The message echoed back
- `message_length` (int) - Length of the message
- `reward` (float) - Reward based on message length (length × 0.1)
- `done` (bool) - Always False for echo environment
- `metadata` (dict) - Additional info like step count

### Reward

The reward is based on how effectively the agent resolves the underlying issue.

- The environment evaluates the **final system state** and **actions taken**
- Correct root-cause fixes receive higher scores
- Partial fixes may receive intermediate rewards
- Incorrect or unnecessary actions receive low or zero reward

#### Example:

- Correctly fixing a memory leak via version revert → reward: **1.0**
- Partially addressing the issue (e.g., revert but memory still low) → reward: **0.4**
- Incorrect action (e.g., scaling when not needed) → reward: **0.0**

## Advanced Usage

It helps to create a powerfull LLM which will help to find out the root cause in a incident occured in a distributed environment systems and resolve it

### Using the Context Manager

The client supports context manager usage for automatic connection management:

```python
from deploy_buddy import DeployBuddyAction, DeployBuddyEnv

# Connect with context manager (auto-connects and closes)
with DeployBuddyEnv(base_url="http://localhost:8000") as env:
    result = env.reset()
    print(f"Reset: {result.observation.echoed_message}")
    # Multiple steps with low latency
    for msg in ["Hello", "World", "!"]:
        result = env.step(DeployBuddyAction(message=msg))
        print(f"Echoed: {result.observation.echoed_message}")
```

The client uses WebSocket connections for:
- **Lower latency**: No HTTP connection overhead per request
- **Persistent session**: Server maintains your environment state
- **Efficient for episodes**: Better for many sequential steps

### Concurrent WebSocket Sessions

The server supports multiple concurrent WebSocket connections. To enable this,
modify `server/app.py` to use factory mode:

```python
# In server/app.py - use factory mode for concurrent sessions
app = create_app(
    DeployBuddyEnvironment,  # Pass class, not instance
    DeployBuddyAction,
    DeployBuddyObservation,
    max_concurrent_envs=4,  # Allow 4 concurrent sessions
)
```

Then multiple clients can connect simultaneously:

```python
from deploy_buddy import DeployBuddyAction, DeployBuddyEnv
from concurrent.futures import ThreadPoolExecutor

def run_episode(client_id: int):
    with DeployBuddyEnv(base_url="http://localhost:8000") as env:
        result = env.reset()
        for i in range(10):
            result = env.step(DeployBuddyAction(message=f"Client {client_id}, step {i}"))
        return client_id, result.observation.message_length

# Run 4 episodes concurrently
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(run_episode, range(4)))
```


### Direct Environment Testing

Test the environment logic directly without starting the HTTP server:

```bash
# From the server directory
python3 server/deploy_buddy_environment.py
```

This verifies that:
- Environment resets correctly
- Step executes actions properly
- State tracking works
- Rewards are calculated correctly

### Running Locally

Run the server locally for development:

```bash
uvicorn server.app:app --reload
```

## Project Structure

```
deploy_buddy/
├── .dockerignore         # Docker build exclusions
├── __init__.py            # Module exports
├── README.md              # This file
├── openenv.yaml           # OpenEnv manifest
├── pyproject.toml         # Project metadata and dependencies
├── uv.lock                # Locked dependencies (generated)
├── client.py              # DeployBuddyEnv client
├── models.py              # Action and Observation models
└── server/
    ├── __init__.py        # Server module exports
    ├── deploy_buddy_environment.py  # Core environment logic
    ├── app.py             # FastAPI application (HTTP + WebSocket endpoints)
    └── Dockerfile         # Container image definition
    |___tasks              # Contains tasks definations, grading logic etc
        ├── EasyDBOverloadTask.py
        ├── MediumMemoryLeakTask.py
        ├── MediumVersionIncompatibility.py
        ├── HardFeedbackLoopTask.py
        └── HardFeedBackLoop.py
```
