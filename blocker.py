# blocker.py
import os
from hpa_manager import HPA

PAYOFF_THRESHOLD = float(os.environ.get("PAYOFF_THRESHOLD", 0.8))

hpa = HPA()

def should_block(macro, micro):
    """判断是否阻断"""
    # 完全新macro
    if macro not in hpa.hpa["micro"]:
        hpa.update_transition(macro, micro)
        return False

    # macro已存在，micro不存在 → 新路径
    if micro not in hpa.hpa["micro"][macro]:
        hpa.update_transition(macro, micro)
        return False

    # payoff计算
    prob = hpa.hpa["micro"][macro][micro]["prob"]
    best_prob = max(v["prob"] for v in hpa.hpa["micro"][macro].values())
    payoff = prob / best_prob if best_prob > 0 else 1.0

    return payoff > PAYOFF_THRESHOLD

