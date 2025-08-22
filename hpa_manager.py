# hpa_manager.py
import json
import pandas as pd
import os
from collections import defaultdict

HPA_JSON_PATH = os.environ.get("HPA_JSON_PATH", "hpa.json")

class HPA:
    def __init__(self, path=HPA_JSON_PATH):
        self.path = path
        if os.path.exists(path):
            with open(path, "r") as f:
                self.hpa = json.load(f)
        else:
            self.hpa = {"macro": {}, "micro": {}}

    @staticmethod
    def from_csv(macro_csv, micro_csv, out_json="hpa.json"):
        macro_df = pd.read_csv(macro_csv)
        micro_df = pd.read_csv(micro_csv)

        hpa = {"macro": defaultdict(dict), "micro": defaultdict(dict)}

        # 宏观转移
        for _, row in macro_df.iterrows():
            src = row["from_macro"]
            dst = row["to_macro"]
            prob = row["prob"]
            hpa["macro"][src][dst] = {"count": row["count"], "prob": prob}

        # 微观转移
        for _, row in micro_df.iterrows():
            macro = row["macro"]
            micro = row["micro"]
            prob = row["prob"]
            hpa["micro"][macro][micro] = {"count": row["count"], "prob": prob}

        # 保存
        with open(out_json, "w") as f:
            json.dump(hpa, f, indent=2)
        return out_json

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.hpa, f, indent=2)

    def update_transition(self, macro, micro):
        """ 更新HPA：如果不存在，新增；存在则计数+1并重算概率 """
        # 更新 micro
        if macro not in self.hpa["micro"]:
            self.hpa["micro"][macro] = {}
        if micro not in self.hpa["micro"][macro]:
            self.hpa["micro"][macro][micro] = {"count": 0, "prob": 0.0}
        self.hpa["micro"][macro][micro]["count"] += 1

        # 重新计算概率
        total = sum(v["count"] for v in self.hpa["micro"][macro].values())
        for m, v in self.hpa["micro"][macro].items():
            v["prob"] = v["count"] / total

        self.save()

