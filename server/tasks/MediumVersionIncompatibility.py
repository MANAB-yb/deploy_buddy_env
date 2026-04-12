from deploy_buddy.models import DeployBuddyAction
# Use one dot for same directory, or two dots for parent
from ..common_methods import CommonMethods
import numpy as np

class MediumVersionIncompatibility:
    def __init__(self):
        self.common_methods = CommonMethods()
        self.name = "medium"
        self.restarted = []
        self.MAX_REPLICAS = 6

    def get_initial_state(self):
        return {
            "services": {
                "api": {
                    "latency": 300, 
                    "error": 0.5, 
                    "cpu": 80, 
                    "connections": 50,
                    "free_memory": 12, 
                    "disk_available": 50,
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
                                "replicas": 1,
                                "reachable": True
                            }
                        }

                },
                "task_runner": {
                    "latency": 200, 
                    "error": 0.7, 
                    "free_memory": 0.5, 
                    "cpu": 85, 
                    "connections": 90, 
                    "disk_available": 12,
                    "version": "v2",
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
                "db": {
                    "cpu": 60, 
                    "connections": 70, 
                    "latency": 50, 
                    "disk_available": 70, 
                    "free_memory": 12,
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
            },
            "incident": "memory_leak",
            "time": 0,
        }
    
    def get_additional_observations(self, internal_state, calls):
        alerts = []
        init_logs = [
            "api server polling for edit universe abc succeeded current state editing",
            "api server polling for edit universe abc succeeded current state editing",
            "api server polling for edit universe abc succeeded current state edited",
            "upgraded version of task_runner from v1 to v2"
            ]
        kube_restart_logs = [
                "api server polling for edit universe abc failed with response 400(Bad Request) error from Task Runner",
                "api server polling for edit universe abc failed with response 400(Bad Request) error from Task Runner",
                "api server polling for edit universe abc failed with response 400(Bad Request) error from Task Runner",
                "api server successfully submitted task create universe xyz",
                "api server polling for edit universe abc failed with response 400(Bad Request) error from Task Runner",
                "200 ok response from task runner - create universe for xyz initiated",
                "api server polling for create universe xyz failed with response 400(Bad Request) error from Task Runner",
                "api server polling for edit universe abc failed with response 400(Bad Request) error from Task Runner",
                "api server polling for create universe xyz failed with response 400(Bad Request) error from Task Runner",
                "api server polling for edit universe abc failed with response 400(Bad Request) error from Task Runner",
                "api server polling for create universe xyz failed with response 400(Bad Request) error from Task Runner",
                "api server polling for edit universe abc failed with response 400(Bad Request) error from Task Runner",
                "api server polling for create universe xyz failed with response 400(Bad Request) error from Task Runner"
            ]
        logs = []
        if calls == 0:
            return init_logs + kube_restart_logs, alerts
        elif internal_state["task_runner"]["version"] == "v2":
            # Still it's incompatibe
            return kube_restart_logs, alerts
        else:
            # if more than 1 GB free memory left then we can say it's stable
            return [], alerts
    
        


    def apply_actions(self, internal_state, action: DeployBuddyAction):
        if action.action_type == "change_lb_config":
            svc = action.target
            curr_replicas, final_count = self.common_methods.define_change_configs(action.value, internal_state[svc]["load_balancer"])
            delta = final_count - curr_replicas
            if delta == 0:
                return internal_state # nothing to increase if 0
            
            if svc == "db":
                # curr_replicas = internal_state["db"]["replicas"]
                
                # as of now evenly distributing the total load accross the instances
                internal_state["db"]["cpu"] = max(((internal_state["db"]["cpu"] * curr_replicas) / final_count), 20)
                internal_state["db"]["connections"] = max(((internal_state["db"]["connections"] * curr_replicas) / final_count), 2)
                internal_state["db"]["latency"] = max(((internal_state["db"]["latency"] * curr_replicas) / final_count), 2)
                # internal_state["db"]["replicas"] = final_count
            elif svc == "api":
                # curr_replicas = internal_state["api"]["replicas"]
                
                # as of now evenly distributing the total load accross the instances
                internal_state["api"]["cpu"] = max(((internal_state["api"]["cpu"] * curr_replicas) / final_count), 20)
                internal_state["api"]["connections"] = max(((internal_state["api"]["connections"] * curr_replicas) / final_count), 2)
                # internal_state["api"]["replicas"] = final_count
                # Will add some internal load on the DB
                internal_state["db"]["cpu"] = min(internal_state["db"]["cpu"] + 5, 100)
                internal_state["api"]["free_memory"] = min((internal_state["api"]["free_memory"] + delta * 5), 15)
                # adds lot of loads to task runner as more pods will request task runner
                internal_state["task_runner"]["free_memory"] = max(internal_state["task_runner"]["free_memory"] - 0.3 * final_count, 0.0)
            else:
                # Task Runner
                # curr_replicas = internal_state["task_runner"]["replicas"]
                
                # task runner is leaking a high amount of memory more than what allocated
                # due to buggy code so new pods will also have utilize the memory and cpu allocated to it or may be less
                # so decreasing memory very less when new instance added and will increase penalty for that action
                internal_state["task_runner"]["cpu"] = min(internal_state["task_runner"]["cpu"] + 2, 100)
                internal_state["task_runner"]["connections"] = max(((internal_state["task_runner"]["connections"] * curr_replicas) / final_count), 2)
                # internal_state["task_runner"]["replicas"] = final_count
                internal_state["task_runner"]["free_memory"] = max(internal_state["task_runner"]["free_memory"] - 0.1 * delta, 0.1)
                # Will add some internal load on the DB
                internal_state["db"]["cpu"] = min(internal_state["db"]["cpu"] + 5, 100)
            self.common_methods.change_internal_state_replicas(internal_state[svc]["load_balancer"], action.value)

        elif action.action_type == "revert_version":
            svc = action.target
            # Reverting db and api versions have no impact
            if svc == "task_runner":
                if internal_state["task_runner"]["version"] == "v2":
                    internal_state["task_runner"]["version"] = "v1"
                else:
                    return
                internal_state["task_runner"]["free_memory"] = 7
                internal_state["task_runner"]["cpu"] = min(60, internal_state["task_runner"]["cpu"])
                internal_state["task_runner"]["error"] = min(0.1, internal_state["task_runner"]["error"])
                internal_state["task_runner"]["latency"] = 100
                internal_state["api"]["error"] = min(0.2, internal_state["api"]["error"])
                internal_state["api"]["cpu"] = max(internal_state["api"]["cpu"] - 20, 23)
                internal_state["task_runner"]["version"] = "v1"
                return internal_state
        
        if internal_state["task_runner"]["version"] == "v2":
            internal_state["task_runner"]["latency"] += 20
            internal_state["api"]["latency"] += 10
            internal_state["api"]["error"] += 0.01
            internal_state["task_runner"]["error"] += 0.02
        
        # In all other tasks it can improve a bit for some time but ultimately will come to the same state
        return internal_state
    
    def compute_reward(self, prev_state, curr_state, action: DeployBuddyAction):
        reward = 0.0

        # although restarts don't help here but good practice to try rolling restart
        if action.action_type == "restart_service" and action.target not in self.restarted:
            reward += 0.3
            self.restarted.append(action.target)

        curr_api = curr_state["services"]["api"]

        curr_db = curr_state["services"]["db"]

        prev_task_runner = prev_state["services"]["task_runner"]
        curr_task_runner = curr_state["services"]["task_runner"]

        reward += (prev_task_runner["latency"] - curr_task_runner["latency"]) * 0.05
        reward += (prev_task_runner["cpu"] - curr_task_runner["cpu"]) * 0.05
        reward += (curr_task_runner["free_memory"] - prev_task_runner["free_memory"]) * 0.05

        # penalty for underutilized resources we want to be cost efficient
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

        reward -= penalty
        if action.action_type == "change_lb_config":
            reward -= self.common_methods.penalty_for_unbalanced_config(current_state=curr_state)

        # penalize for incorrect action
        if action.action_type == "revert_version" and action.target == "task_runner" and prev_task_runner["version"] == "v2":
            reward += 0.5
        elif action.action_type == "revert_version":
            # penalizing for each incorrect version revert which don't make sense and can harm the system
            reward -= 0.2
        
        return np.clip(reward, 0, 1)
    
    def grade(self, final_state, actions):
        tr = final_state["services"]["task_runner"]

        reverted = any(
            a.action_type == "revert_version" and a.target == "task_runner"
            for a in actions
        )

        memory_ok = tr["free_memory"] > 2

        success = reverted and memory_ok
        score = 0.0
        reason = ""
        if reverted and not memory_ok:
            score = 0.4
            reason += "reverting versions worked, but still we need to look "
        if success:
            score = 1.0
            reason = "Memory leak totally fixed"
        
        if reason == "":
            reason = "Memory leak not properly resolved"

        # small deduction in score if the overall steps increase
        
        score -= 0.01 * len(actions)

        score = max(0.01, min(score, 0.99))

        return {
            "success": success,
            "score": round(score, 2),
            "reason": reason
        }
