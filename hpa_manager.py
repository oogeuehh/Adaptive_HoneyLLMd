import json
import os
from typing import List, Tuple, Dict, Optional
from collections import deque
from datetime import datetime

HPA_DEFAULT_PATH = os.environ.get("HPA_JSON_PATH", "hpa.json")
EPSILON = 1e-8

class HPA:
    def __init__(self, path: str = HPA_DEFAULT_PATH):
        self.path = path
        self.hpa = {"macros": {}, "meta": {}}
        if os.path.exists(self.path):
            self.load(self.path)

    def load(self, path: str = None):
        path = path or self.path
        with open(path, "r", encoding="utf-8") as f:
            self.hpa = json.load(f)
        self.hpa.setdefault("macros", {})
        return self.hpa

    def save(self, path: str = None):
        path = path or self.path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.hpa, f, indent=2, ensure_ascii=False)

    def get_macro(self, macro: str) -> Dict:
        return self.hpa.get("macros", {}).get(macro, {"to_macros": {}, "micro_probs": {}})

    def path_probability(self, path: List[Tuple[str,str]]) -> float:
        if not path: return 0.0
        prob = 1.0
        for i, (macro, micro) in enumerate(path):
            macro_obj = self.get_macro(macro)
            mp = macro_obj.get("micro_probs", {}).get(micro, EPSILON)
            prob *= mp
            if i + 1 < len(path):
                next_macro = path[i+1][0]
                sp = macro_obj.get("to_macros", {}).get(next_macro, EPSILON)
                prob *= sp
        return prob

    def best_path_probability(self, src_macro: str, max_depth=6) -> float:
        """Greedy搜索某macro出发的最优路径概率"""
        best_prob = 0.0
        queue = deque([(src_macro, 1.0, 0)])
        while queue:
            macro, prob_prod, depth = queue.popleft()
            best_prob = max(best_prob, prob_prod)
            if depth >= max_depth: continue
            macro_obj = self.get_macro(macro)
            max_mp = max(macro_obj.get("micro_probs", {}).values(), default=1.0)
            for nxt_macro, sp in macro_obj.get("to_macros", {}).items():
                if sp <= 0: continue
                queue.append((nxt_macro, prob_prod * sp * max_mp, depth+1))
        return best_prob if best_prob > 0 else EPSILON

    def compute_payoff_ratio(self, current_path: List[Tuple[str,str]]) -> float:
        if not current_path: return 0.0
        src_macro = current_path[0][0]
        current_prob = self.path_probability(current_path)
        best_prob = self.best_path_probability(src_macro)
        return current_prob / best_prob if best_prob > 0 else 0.0

    def update_from_session(self, session_path: List[Tuple[str,str]], weight: float = 1.0):
        counts = self.hpa.setdefault("_counts", {})
        macros_counts = counts.setdefault("macros", {})

        for i, (macro, micro) in enumerate(session_path):
            macro_counts = macros_counts.setdefault(macro, {"to_macros": {}, "micro": {}})
            macro_counts["micro"][micro] = macro_counts["micro"].get(micro, 0.0) + weight
            if i + 1 < len(session_path):
                next_macro = session_path[i+1][0]
                macro_counts["to_macros"][next_macro] = macro_counts["to_macros"].get(next_macro, 0.0) + weight

        # normalize
        for macro, val in macros_counts.items():
            micro_counts = val.get("micro", {})
            tot_m = sum(micro_counts.values()) or 1.0
            to_counts = val.get("to_macros", {})
            tot_t = sum(to_counts.values()) or 1.0
            macro_entry = self.hpa.setdefault("macros", {}).setdefault(macro, {"micro_probs": {}, "to_macros": {}})
            for mkey, cnt in micro_counts.items():
                macro_entry["micro_probs"][mkey] = cnt / tot_m
            for tk, cnt in to_counts.items():
                macro_entry["to_macros"][tk] = cnt / tot_t

        self.hpa.setdefault("meta", {})["last_updated"] = datetime.utcnow().isoformat() + "Z"
