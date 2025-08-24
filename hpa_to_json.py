import json
import pandas as pd
from collections import defaultdict

def create_hpa_tree(macro_transition_file, macro_micro_file):
    macro_trans_df = pd.read_csv(macro_transition_file)
    macro_micro_df = pd.read_csv(macro_micro_file)
    
    # node counter
    node_id_counter = 0
    
    # create root node
    root_node = {
        "id": node_id_counter,
        "name": "root",
        "position": -1,
        "children": [],
        "micros": []
    }
    node_id_counter += 1
    
    # dict for save node info
    nodes_by_position = defaultdict(dict)  # position -> macro_name -> node
    nodes_by_id = {}  # id -> node
    
    # add root node to dict
    nodes_by_id[root_node["id"]] = root_node
    
    # macro transformer info
    for _, row in macro_trans_df.iterrows():
        position = row["position"]
        from_macro = row["from_macro"]
        to_macro = row["to_macro"]
        count = row["count"]
        prob = row["prob"]
        
        # from node
        if position not in nodes_by_position or from_macro not in nodes_by_position[position]:
            # create node
            from_node = {
                "id": node_id_counter,
                "name": from_macro,
                "position": position,
                "children": [],
                "micros": [],
                "parent_id": None
            }
            node_id_counter += 1
            
            # dict
            nodes_by_position[position][from_macro] = from_node
            nodes_by_id[from_node["id"]] = from_node
            
            if position == 0:
                root_node["children"].append({
                    "node_id": from_node["id"],
                    "count": 0,  
                    "prob": 0.0  
                })
        else:
            from_node = nodes_by_position[position][from_macro]
        
        # next node
        next_position = position + 1
        if next_position not in nodes_by_position or to_macro not in nodes_by_position[next_position]:
            to_node = {
                "id": node_id_counter,
                "name": to_macro,
                "position": next_position,
                "children": [],
                "micros": [],
                "parent_id": from_node["id"]
            }
            node_id_counter += 1
            
            nodes_by_position[next_position][to_macro] = to_node
            nodes_by_id[to_node["id"]] = to_node
        else:
            to_node = nodes_by_position[next_position][to_macro]
        
        # transformer info
        from_node["children"].append({
            "node_id": to_node["id"],
            "count": count,
            "prob": prob
        })
    
    # micro
    for _, row in macro_micro_df.iterrows():
        position = row["position"]
        macro = row["macro"]
        micro = row["micro"]
        count = row["count"]
        prob = row["prob"]
        
        # corresponding macro
        if position in nodes_by_position and macro in nodes_by_position[position]:
            node = nodes_by_position[position][macro]
            
            # micro info
            node["micros"].append({
                "name": micro,
                "count": count,
                "prob": prob
            })
    
    total_first_level = sum(child["count"] for child in root_node["children"])
    for child in root_node["children"]:
        child["prob"] = child["count"] / total_first_level if total_first_level > 0 else 0.0
    
    result = {
        "root_id": root_node["id"],
        "nodes": list(nodes_by_id.values())
    }
    
    return result

hpa_tree = create_hpa_tree("macro_transition_probs.csv", "macro_path_micro_stats.csv")

with open("hpa.json", "w", encoding="utf-8") as f:
    json.dump(hpa_tree, f, indent=2, ensure_ascii=False)

print("Successfully saved as hpa.json")
