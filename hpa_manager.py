# hpa_manager.py
import json
import os
from collections import defaultdict
from typing import List, Tuple, Dict, Optional

HPA_JSON_PATH = os.environ.get("HPA_JSON_PATH", "hpa.json")


class HPA:
    def __init__(self, path: str = HPA_JSON_PATH):
        self.path = path
        if os.path.exists(path):
            with open(path, "r") as f:
                self.hpa = json.load(f)
        else:
            self.hpa = {}

        # save src and dst with dict
        self.sessions = {}

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.hpa, f, indent=4, ensure_ascii=False)

    # -------------------------------------------------
    # update src and dst
    # -------------------------------------------------
    def update_src_and_dst(self, session_id: str, src: int, dst: int, blocked: bool):
        """
        No block，update dst of a session,
        maintain src.
        """
        if session_id not in self.sessions:
            # initialize session
            self.sessions[session_id] = {"src": src, "dst": dst}
        else:
            if not blocked:
                self.sessions[session_id]["dst"] = dst

    # -------------------------------------------------
    # match actual input is in hpa.json or not
    # -------------------------------------------------
    def match_hpa(self, position: int, macro: str, micro: str) -> bool:
        """
        certain position，check whether macro and micro exist.
        """
        position = str(position)
        if position in self.hpa:
            if macro in self.hpa[position]:
                if micro in self.hpa[position][macro]:
                    return True
        return False

    # -------------------------------------------------
    # update hpa.json (matched=False)
    # -------------------------------------------------
    def update_hpa(self, position: int, macro: str, micro: str):
        """
        new state, update hpa
        """
        pos_key = str(position)

        if pos_key not in self.hpa:
            self.hpa[pos_key] = {}

        if macro not in self.hpa[pos_key]:
            self.hpa[pos_key][macro] = {}

        if micro not in self.hpa[pos_key][macro]:
            self.hpa[pos_key][macro][micro] = {"count": 1, "prob": 0.0}
        else:
            self.hpa[pos_key][macro][micro]["count"] += 1

        # re-normalize
        total = sum(v["count"] for v in self.hpa[pos_key][macro].values())
        for m, val in self.hpa[pos_key][macro].items():
            val["prob"] = val["count"] / total

        self.save()

    # -------------------------------------------------
    # comput payoff
    # -------------------------------------------------
    def compute_payoff(self, actual_path: List[Tuple[int, str, str]], src: int, dst: int) -> float:
        """
        actual_path: [(position, macro, micro), ...]
        src
        dst
        """
        # 1. probability of actual path
        actual_pr = 1.0
        for pos, macro, micro in actual_path:
            pos_key = str(pos)
            if pos_key in self.hpa and macro in self.hpa[pos_key] and micro in self.hpa[pos_key][macro]:
                actual_pr *= self.hpa[pos_key][macro][micro]["prob"]
            else:
                actual_pr = 0.0
                break

        # 2. best probability
        best_pr = self._find_best_path(src, dst)

        # 3. payoff
        if best_pr == 0:
            return 0.0
        return actual_pr / best_pr

    def _find_best_path(self, src: int, dst: int) -> float:
        """
        DFS 
        """
        src, dst = str(src), str(dst)
        best_pr = 0.0

        def dfs(pos: str, pr: float):
            nonlocal best_pr
            if pos == dst:
                best_pr = max(best_pr, pr)
                return
            if pos not in self.hpa:
                return

            for macro, micros in self.hpa[pos].items():
                for micro, val in micros.items():
                    next_pr = pr * val["prob"]
                    next_pos = str(int(pos) + 1) 
                    dfs(next_pos, next_pr)

        dfs(src, 1.0)
        return best_pr

