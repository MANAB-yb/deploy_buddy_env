# Use one dot for same directory, or two dots for parent
from ..common_methods import CommonMethods
import numpy as np

class HardZoneFailureTask:
    def __init__(self):
        self.common_methods = CommonMethods()
        self.name = "zone_failure"
        self.failed_zone = "zone_b"
        self.healthy_zones = ["zone_a", "zone_c"]
        self.restarted = []

    def get_initial_state(self):
        return {
            "services": {
                "api": {
                    "latency": 600,
                    "error": 0.45,
                    "cpu": 80,
                    "connections": 120,
                    "free_memory": 6,
                    "disk_available": 70,
                    "version": "v1",
                    "load_balancer": {
                        "zone_a": {
                            "replicas": 1, 
                            "healthy": 1,
                            "reachable": True
                            },
                        "zone_b": {
                            "replicas": 2, 
                            "healthy": 0,
                            "reachable": False
                        },  # Failed zone
                        "zone_c": {
                            "replicas": 1,
                            "healthy": 1, 
                            "reachable": True
                        },
                    },
                },
                "task_runner": {
                    "latency": 500,
                    "error": 0.35,
                    "cpu": 97,
                    "connections": 90,
                    "free_memory": 5,
                    "disk_available": 60,
                    "version": "v1",
                    "load_balancer": {
                        "zone_a": {
                            "replicas": 1,
                            "healthy": 1,
                            "reachable": True
                            },
                        "zone_b": {
                            "replicas": 2,
                            "healthy": 0,
                            "reachable": False
                        },
                        "zone_c": {
                            "replicas": 1,
                            "healthy": 1,
                            "reachable": True
                        },
                    },
                },
                "db": {
                    "latency": 120,
                    "error": 0.1,
                    "cpu": 60,
                    "connections": 100,
                    "free_memory": 10,
                    "disk_available": 80,
                    "version": "v1",
                    "load_balancer": {
                        "zone_a": {
                            "replicas": 1,
                            "healthy": 1,
                            "reachable": True
                            },
                        "zone_b": {
                            "replicas": 0,
                            "healthy": 0,
                            "reachable": False # no replicas in zone b
                            },
                        "zone_c": {
                            "replicas": 1,
                            "healthy": 1, 
                            "reachable": True
                            },
                    },
                },
            },
            "time": 0
        }
    
    def get_additional_observations(self, internal_state, calls):
        
        logs = [
            "Health check failures detected for zone_b",
            "Load balancer marked zone_b as unreachable",
            "Increased latency due to traffic concentration in remaining zones",
            "Pod eviction events observed in zone_b",
        ]
        alerts = []

        if internal_state["api"]["latency"] > 300:
            alerts = [
                "High API latency detected",
                "Elevated error rates across services",
                ]

        return logs, alerts
    
    def apply_actions(self, internal_state, action):
        services = internal_state

        if action.action_type == "change_lb_config":
            svc = action.target
            curr_replicas, final_count = self.common_methods.define_change_configs(action.value, internal_state[svc]["load_balancer"])
            delta = final_count - curr_replicas
            if svc == "db":
                
                internal_state["db"]["cpu"] = max(((internal_state["db"]["cpu"] * curr_replicas) / final_count), 10)
                internal_state["db"]["connections"] = max(((internal_state["db"]["connections"] * curr_replicas) / final_count), 2)
                internal_state["db"]["latency"] = max(((internal_state["db"]["latency"] * curr_replicas) / final_count), 2)
                # internal_state["db"]["replicas"] = final_count
            elif svc == "api":
                
                internal_state["api"]["cpu"] = max(((internal_state["api"]["cpu"] * curr_replicas) / final_count), 20)
                internal_state["api"]["connections"] = max(((internal_state["api"]["connections"] * curr_replicas) / final_count), 2)
                
                internal_state["db"]["cpu"] = min(internal_state["db"]["cpu"] + 0.1 * delta, 100)
                internal_state["api"]["free_memory"] = min((internal_state["api"]["free_memory"] + delta * 5), 15)
            else:
                
                internal_state["task_runner"]["cpu"] = max(((internal_state["task_runner"]["cpu"] * curr_replicas) / final_count), 20)
                internal_state["task_runner"]["connections"] = max(((internal_state["task_runner"]["connections"] * curr_replicas) / final_count), 2)
                internal_state["task_runner"]["latency"] = max(((internal_state["task_runner"]["latency"] * curr_replicas) / final_count), 50)
                internal_state["db"]["cpu"] = min(internal_state["db"]["cpu"] + 5, 100)
                internal_state["task_runner"]["free_memory"] = min((internal_state["task_runner"]["free_memory"] + delta * 5), 15)
            self.common_methods.change_internal_state_replicas(internal_state[svc]["load_balancer"], action.value)

            # Ensure failed zone has zero replicas
            services[svc]["load_balancer"][self.failed_zone]["replicas"] = 0

        elif action.action_type == "restart_service":
            svc = action.target
            services[svc]["latency"] *= 0.6
            services[svc]["error"] *= 0.6

        return internal_state
    
    def compute_reward(self, prev_state, curr_state, action):
        reward = 0.0

        if action.action_type == "restart_service" and action.target not in self.restarted:
            reward += 0.02
            self.restarted.append(action.target)

        for svc in ["api", "task_runner"]:
            prev = prev_state["services"][svc]
            curr = curr_state["services"][svc]

            # Improvement in stats rewards
            if prev["latency"] > 300 or curr["latency"] > prev["latency"]:
                reward += (prev["latency"] - curr["latency"]) * 0.005
            if prev["error"] > 0.5 or curr["error"] > prev["error"]:
                reward += (prev["error"] - curr["error"]) * 0.005
            if prev["cpu"] > 75 or curr["cpu"] > prev["cpu"]:
                reward += (prev["cpu"] - curr["cpu"]) * 0.005
            if prev["free_memory"] < 1 or prev["free_memory"] > curr["free_memory"]:
                reward += (curr["free_memory"] - prev["free_memory"]) * 0.005

        # penalties for adding nodes in wrong zone
        if action.action_type == "change_lb_config":
            reward -= action.value[self.failed_zone] * 0.05
            


        # Penalize unnecessary scaling (cost awareness)
        # penalty for underutilized resources we want to be cost efficient
        curr_api = curr_state["services"]["api"]
        curr_db = curr_state["services"]["db"]
        prev_task_runner = prev_state["services"]["task_runner"]
        curr_task_runner = curr_state["services"]["task_runner"]
        def under_util_penalty(cpu, free_mem):
            penalty = 0.0
            if free_mem < 16 or cpu > 30:
                return penalty # only penalize if everything is underutilized
            if free_mem >= 16:
                penalty += (free_mem - 16) * 0.03 
            if cpu <= 30:
                penalty += (30 - cpu) * 0.03
            return penalty

        penalty = 0.0
        penalty += under_util_penalty(curr_api["cpu"], curr_api["free_memory"])
        penalty += under_util_penalty(curr_db["cpu"], curr_db["free_memory"])
        penalty += under_util_penalty(curr_task_runner["cpu"], curr_task_runner["free_memory"])

        if action.action_type == "revert_version":
            reward -= 0.2 # already in v1 no sense to revert any component's version

        if action.action_type == "change_lb_config":
            reward -= self.common_methods.penalty_for_unbalanced_config(current_state=curr_state)


        reward -= penalty
        # return reward

        return np.clip(reward, 0.1, 0.99)
    
    def grade(self, final_state, actions):
        score = 0.0
        api = final_state["services"]["api"]
        db = final_state["services"]["db"]
        task = final_state["services"]["task_runner"]

        services = final_state["services"]
        success = True
        reason = []

        for svc in services:
            lb = services[svc]["load_balancer"]

            # Failed zone should have zero replicas
            if lb[self.failed_zone]["replicas"] > 0:
                success = False
                reason.append(f"{svc}: replicas still running in failed zone")
                score -= 0.05 * lb[self.failed_zone]["replicas"]

        
        api_ok = api["latency"] < 300 and api["cpu"] < 70 and api["free_memory"] > 3
        db_ok = db["cpu"] < 70
        task_ok = task["latency"] < 300 and task["cpu"] < 70 and task["free_memory"] > 3

        if task_ok:
            score += 0.3
            reason += "task runners are now healthy "
        if db_ok:
            score += 0.3
            reason += "DB now healthy "
        if api_ok:
            score += 0.4
            reason += "Api servers healthy"

        if not api_ok or not db_ok or not task_ok:
            success = False

        
        score -= 0.01 * len(actions)
        score = max(0.01, min(score, 0.99))

        return {
            "success": success,
            "score": round(score, 2),
            "reason": "Zone failure mitigated successfully"
            if success else "; ".join(reason),
        }