from deploy_buddy.models import DeployBuddyAction
# Use one dot for same directory, or two dots for parent
from ..common_methods import CommonMethods
import numpy as np

class EasyDBOverloadTask:
    def __init__(self):
        self.name = "easy"
        self.MAX_REPLICAS = 10
        self.common_methods = CommonMethods()

    def get_initial_state(self):
        return {
            "services": {
                "api": {
                        "latency": 200, 
                        "cpu": 45, 
                        "error": 0.02, 
                        # "default_zone": "zone_a", 
                        "free_memory": 4, 
                        "connections": 50,
                        "version": "v1",
                        "load_balancer": {
                            "zone_a": {
                                "replicas": 1,
                                "reachable": True
                            },
                            "zone_b": {
                                "replicas": 1,
                                "reachable": True 
                            },
                            "zone_c": {
                                "replicas": 0,
                                "reachable": None # lb not trying to connect them
                            }
                        }
                    },
                "db": {
                        "cpu": 90, 
                        "connections": 95, 
                        # "default_zone": "zone_a", 
                        "latency": 600, 
                        "disk_available": 950, 
                        "free_memory": 8,
                        "version": "v1",
                        "load_balancer": {
                            "zone_a": {
                                "replicas": 1,
                                "reachable": True
                            },
                            "zone_b": {
                                "replicas": 0,
                                "reachable": None # lb not trying to connect them
                            },
                            "zone_c": {
                                "replicas": 0,
                                "reachable": None
                            }
                        }
                    },
                "task_runner": {
                        "latency": 200, 
                        "cpu": 45, 
                        "error": 0.02,
                        # "default_zone": "zone_a", 
                        "free_memory": 4, 
                        "disk_available": 14,
                        "version": "v1",
                        "load_balancer": {
                            "zone_a": {
                                "replicas": 1,
                                "reachable": True
                            },
                            "zone_b": {
                                "replicas": 1,
                                "reachable": True 
                            },
                            "zone_c": {
                                "replicas": 0,
                                "reachable": None # lb not trying to connect them
                            }
                        }
                    }
            },
            "time": 0,
        }
    
    def get_additional_observations(self, internal_state, calls):
        return [], []
    
    def apply_actions(self, internal_state, action: DeployBuddyAction):
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
                # internal_state["api"]["replicas"] = final_count
                # Will add some internal load on the DB
                internal_state["db"]["cpu"] = min(internal_state["db"]["cpu"] + 5, 100)
                internal_state["api"]["free_memory"] = min((internal_state["api"]["free_memory"] + delta * 0.1), 15)
            else:
                # Task Runner
                internal_state["task_runner"]["cpu"] = max(((internal_state["task_runner"]["cpu"] * curr_replicas) / final_count), 20)
                internal_state["task_runner"]["connections"] = max(((internal_state["task_runner"]["connections"] * curr_replicas) / final_count), 2)
                # internal_state["task_runner"]["replicas"] = final_count
                # Will add some internal load on the DB
                internal_state["db"]["cpu"] = min(internal_state["db"]["cpu"] + 5, 100)
                internal_state["task_runner"]["free_memory"] = min((internal_state["task_runner"]["free_memory"] + delta * 5), 15)
            self.common_methods.change_internal_state_replicas(internal_state[svc]["load_balancer"], action.value)
        # In all other tasks it can improve a bit but ultimately will come to the same state
        return internal_state

    def compute_reward(self, prev_state, curr_state, action: DeployBuddyAction):
        reward = 0.0

        prev_db = prev_state["services"]["db"]
        curr_db = curr_state["services"]["db"]

        curr_api = curr_state["services"]["api"]
        curr_task_runner = curr_state["services"]["task_runner"]

        reward += (prev_db["latency"] - curr_db["latency"]) * 0.01
        reward += (prev_db["cpu"] - curr_db["cpu"]) * 0.01
        reward += (prev_db["connections"] - curr_db["connections"]) * 0.01


        # penalize for each under utilized components
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
 
        return np.clip(reward, 0.0, 1.0)
    
    def grade(self, final_state, actions):
        db = final_state["services"]["db"]

        success = db["cpu"] < 60 and db["latency"] < 300 and db["connections"] < 70
        score = 0.0
        reason = ""
        if db["cpu"] < 60:
            score += 0.4
            reason += "DB CPU Load reduced, "
        if db["latency"] < 300:
            score += 0.4
            reason += "DB Latency reduced, "
        if db["connections"] < 70:
            score += 0.2
            reason += "DB connections reduced, "

        if reason == "":
            reason = "DB is still overloaded heavily"
        if score == 1:
            reason = "Congratts the DB is completely stable, " + reason

        score -= 0.01 * len(actions)

        score = max(0.01, min(score, 0.99))

        return {
            "success": success,
            "score": round(score, 2),
            "reason": reason
        }
