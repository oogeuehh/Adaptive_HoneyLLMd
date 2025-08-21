import json
import os
from typing import List, Tuple, Dict, Optional
from collections import deque

HPA_DEFAULT_PATH = os.environ.get("HPA_JSON_PATH", "hpa.json")
EPSILON = 1e-8

class HPA:
    def __init__(self, path: str = HPA_DEFAULT_PATH):
        self.path = path
        self.hpa = {"macros": {}, "global": {"exposure": 1.0}, "meta": {}}
        if os.path.exists(self.path):
            self.load(self.path)

    def load(self, path: str = None):
        path = path or self.path
        with open(path, "r", encoding="utf-8") as f:
            self.hpa = json.load(f)
        self.hpa.setdefault("macros", {})
        self.hpa.setdefault("global", {"exposure": 1.0})
        return self.hpa

    def save(self, path: str = None):
        path = path or self.path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.hpa, f, indent=2, ensure_ascii=False)

    def get_macro(self, macro: str) -> Dict:
        return self.hpa.get("macros", {}).get(macro, {"to_macros": {}, "micro_probs": {}})

    def step_prob(self, from_macro: str, to_macro: str) -> float:
        macro = self.get_macro(from_macro)
        return float(macro.get("to_macros", {}).get(to_macro, 0.0))

    def micro_prob(self, macro: str, micro: str) -> float:
        macro_obj = self.get_macro(macro)
        return float(macro_obj.get("micro_probs", {}).get(micro, 0.0))

    def path_probability(self, path: List[Tuple[str,str]]) -> float:
        """Compute probability of a (macro,micro) path with HPA update for new micro."""
        if not path:
            return 0.0
        prob = 1.0
        for i, (macro, micro) in enumerate(path):
            macro_obj = self.get_macro(macro)
            mp = macro_obj.get("micro_probs", {}).get(micro)
            if mp is None:
                # micro 不在 HPA → 动态加入并归一化
                self.update_from_session([(macro, micro)], weight=1.0)
                macro_obj = self.get_macro(macro)
                mp = macro_obj.get("micro_probs", {}).get(micro, EPSILON)
            prob *= mp
            if i + 1 < len(path):
                next_macro = path[i+1][0]
                sp = macro_obj.get("to_macros", {}).get(next_macro)
                if sp is None:
                    # dst macro 不在 HPA → 动态加入
                    self.update_from_session([(macro, micro), (next_macro, "none")], weight=1.0)
                    macro_obj = self.get_macro(macro)
                    sp = macro_obj.get("to_macros", {}).get(next_macro, EPSILON)
                prob *= sp
        return prob

    def best_path_probability_between(self, src_macro: str, dst_macro: Optional[str], max_depth=6) -> float:
        """Approximate best path probability using greedy search."""
        best_prob = 0.0
        queue = deque()
        queue.append((src_macro, 1.0, 0))
        while queue:
            macro, prob_prod, depth = queue.popleft()
            if dst_macro and macro == dst_macro:
                best_prob = max(best_prob, prob_prod)
            if depth >= max_depth:
                if not dst_macro:
                    best_prob = max(best_prob, prob_prod)
                continue
            macro_obj = self.get_macro(macro)
            max_mp = max(macro_obj.get("micro_probs", {}).values(), default=1.0)
            for nxt_macro, sp in macro_obj.get("to_macros", {}).items():
                if sp <= 0:
                    continue
                new_prob = prob_prod * sp * max_mp
                queue.append((nxt_macro, new_prob, depth+1))
                best_prob = max(best_prob, new_prob)
        return best_prob

    def compute_payoff_ratio(self, current_path: List[Tuple[str,str]], lookahead_depth=6):
        if not current_path:
            return 0.0
        macros_in_hpa = set(self.hpa.get("macros", {}).keys())
        macros_in_path = set(m for m, _ in current_path)

        if macros_in_path.isdisjoint(macros_in_hpa):
            return "new_path"

        if not macros_in_path.issubset(macros_in_hpa):
            self.update_from_session(current_path, weight=1.0)

        current_prob = self.path_probability(current_path)
        src_macro = current_path[0][0]
        best_prob = self.best_path_probability_between(src_macro, None, max_depth=lookahead_depth)
        if best_prob <= 0:
            return float("inf") if current_prob > 0 else 0.0
        return float(current_prob) / float(best_prob)

    def update_from_session(self, session_path: List[Tuple[str,str]], weight: float = 1.0):
        """Update HPA with new macro/micro and normalize probabilities."""
        counts = self.hpa.setdefault("_counts", {})
        macros_counts = counts.setdefault("macros", {})
        for i, (macro, micro) in enumerate(session_path):
            macro_counts = macros_counts.setdefault(macro, {"to_macros": {}, "micro": {}})
            macro_counts["micro"][micro] = macro_counts["micro"].get(micro, 0.0) + weight
            if i + 1 < len(session_path):
                next_macro = session_path[i+1][0]
                macro_counts["to_macros"][next_macro] = macro_counts["to_macros"].get(next_macro, 0.0) + weight

        for macro, val in macros_counts.items():
            micro_counts = val.get("micro", {})
            tot_m = sum(micro_counts.values()) or 1.0
            to_counts = val.get("to_macros", {})
            tot_t = sum(to_counts.values()) or 1.0
            macro_entry = self.hpa.setdefault("macros", {}).setdefault(macro, {"micro_probs": {}, "to_macros": {}})
            for mkey, cnt in micro_counts.items():
                macro_entry.setdefault("micro_probs", {})[mkey] = cnt / tot_m
            for tk, cnt in to_counts.items():
                macro_entry.setdefault("to_macros", {})[tk] = cnt / tot_t
        self.hpa.setdefault("meta", {})["last_updated"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"

