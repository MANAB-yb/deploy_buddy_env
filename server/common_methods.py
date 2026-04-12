# Conatains common methods

class CommonMethods():

    
    def define_change_configs(self, future_state, current_state):
        current_node_ct = 0
        final_node_ct = 0
        for zone_name, zone_state in current_state.items():
            # Count only replicas in reachable zones
            if zone_state["reachable"] == True or zone_state["reachable"] == None:
                current_node_ct += zone_state.get("replicas", 0)
                final_node_ct += future_state.get(zone_name, 0)
        current_node_ct = max(current_node_ct, 1)
        final_node_ct = max(final_node_ct, 1)
        return current_node_ct, final_node_ct

    
    def change_internal_state_replicas(self, current_state, future_state):
        for zone, zone_state in current_state.items():
            if zone in future_state:
                zone_state["replicas"] = future_state[zone]
            else:
                zone_state["replicas"] = 0 # to delete all the pods else
    
    
    def get_total_replicas(self, load_balancer_state):
        return sum(
            zone["replicas"]
            for zone in load_balancer_state.values()
            if zone["replicas"] is not None
        )
    
    
    def penalty_for_unbalanced_config(self, current_state):
        considered_nodes = []
        for svc in ["db", "api", "task_runner"]:
            for zone_name, zone_state in  current_state["services"][svc]["load_balancer"].items():
                if zone_state["reachable"] == True or zone_state["reachable"] is None:
                    considered_nodes.append(zone_state["replicas"])
        
        mx_nodes = max(considered_nodes)
        mn_nodes = min(considered_nodes)

        return 0.2 * max(mx_nodes - mn_nodes - 1, 0) # nodes should be uniformly distribute among the reachanble zones


