from hpa_loader import nodes_dict, max_micro_probs

def max_path_prob(src_id, dst_id):
    if src_id == dst_id:
        return max_micro_probs[src_id]
    
    n = len(nodes_dict)
    dp = {node_id: 0.0 for node_id in nodes_dict}
    dp[src_id] = 1.0
    
    for i in range(n-1):
        for node_id in nodes_dict:
            if dp[node_id] > 0:
                node = nodes_dict[node_id]
                for child in node['children']:
                    v_id = child['node_id']
                    if v_id not in nodes_dict:
                        continue
                    p = child['prob']
                    weight = p * max_micro_probs[v_id]
                    new_val = dp[node_id] * weight
                    if new_val > dp[v_id]:
                        dp[v_id] = new_val
                        
    return max_micro_probs[src_id] * dp.get(dst_id, 0.0)
