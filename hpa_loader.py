import json

def load_hpa_data(file_path='hpa.json'):
    with open(file_path, 'r') as f:
        hpa_data = json.load(f)
    nodes = hpa_data['nodes']
    nodes_dict = {node['id']: node for node in nodes}
    
    max_micro_probs = {}
    for node_id, node in nodes_dict.items():
        max_micro_prob = max([micro['prob'] for micro in node['micros']])
        max_micro_probs[node_id] = max_micro_prob
        
    return nodes_dict, max_micro_probs

# 全局变量
nodes_dict, max_micro_probs = load_hpa_data()
