# hpa_manager.py
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
        # normalize (ensure dicts exist)
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
        """macro->macro single-step prob"""
        macro = self.get_macro(from_macro)
        return float(macro.get("to_macros", {}).get(to_macro, 0.0))

    def micro_prob(self, macro: str, micro: str) -> float:
        macro_obj = self.get_macro(macro)
        return float(macro_obj.get("micro_probs", {}).get(micro, 0.0))

    def path_probability(self, path: List[Tuple[str,str]]) -> float:
        """Compute probability of given (macro,micro) sequence.
        path: list of (macro, micro)
        probability = product over i of [ P(micro_i | macro_i) * P(macro_{i+1} | macro_i) (if next)
        For last element, only micro prob applies.
        """
        if not path:
            return 0.0
        prob = 1.0
        for i, (macro, micro) in enumerate(path):
            mp = self.micro_prob(macro, micro) if micro is not None else 0.0
            if mp == 0:
                # 情况 1(b)：micro 不在 HPA → 惩罚项
                mp = EPSILON
            prob *= mp
            # 下一个 macro
            if i + 1 < len(path):
                next_macro = path[i+1][0]
                sp = self.step_prob(macro, next_macro)
                if sp == 0:
                    # 情况 1(b)：dst macro 不在 HPA → 惩罚项
                    sp = EPSILON
                prob *= sp
        return prob

    def best_path_probability_between(self, src_macro: str, dst_macro: Optional[str], max_depth=6) -> float:
        """Find approximate best path probability starting at src_macro to reach dst_macro (if dst_macro is None, find most probable path up to depth).
        Uses greedy beam/DFS limited search multiplying step probs and micro probs.
        Returns best probability (product) found.
        """
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
            for nxt, sp in macro_obj.get("to_macros", {}).items():
                if sp <= 0:
                    continue
                micro_probs = macro_obj.get("micro_probs", {})
                if micro_probs:
                    max_mp = max(micro_probs.values())
                else:
                    max_mp = 1.0
                new_prob = prob_prod * sp * (max_mp if max_mp > 0 else EPSILON)
                if new_prob <= 0:
                    continue
                queue.append((nxt, new_prob, depth+1))
                best_prob = max(best_prob, new_prob)
        return best_prob

    def compute_payoff_ratio(self, current_path: List[Tuple[str,str]], lookahead_depth=6):
        """计算 payoff ratio，支持三种情况：
        1. 状态都在 HPA → 正常计算
        2. 完全新路径 → 返回 "new_path"，不 block
        3. 部分新状态 → 先更新 HPA，再计算
        """
        if not current_path:
            return 0.0

        # 判断路径里是否有完全新 macro
        macros_in_hpa = set(self.hpa.get("macros", {}).keys())
        macros_in_path = set(m for m, _ in current_path)

        if macros_in_path.isdisjoint(macros_in_hpa):
            # 情况 2：完全新路径
            return "new_path"

        # 情况 3：部分新状态 → 更新 HPA
        if not macros_in_path.issubset(macros_in_hpa):
            self.update_from_session(current_path, weight=1.0)

        # 情况 1：正常计算 payoff
        current_prob = self.path_probability(current_path)
        src_macro = current_path[0][0]
        best_prob = self.best_path_probability_between(src_macro, None, max_depth=lookahead_depth)

        if best_prob <= 0:
            return float("inf") if current_prob > 0 else 0.0
        return float(current_prob) / float(best_prob)

    def update_from_session(self, session_path: List[Tuple[str,str]], weight: float = 1.0):
        """动态更新 HPA：把新 macro/micro 加进去并归一化"""
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
