# blocker.py
import os
import json
import time
from typing import List, Tuple
from hpa_manager import HPA

BLOCK_LOG = os.environ.get("BLOCK_LOG_PATH", "block_events.log")
PAYOFF_THRESHOLD = float(os.environ.get("PAYOFF_THRESHOLD", 0.8))
MIN_STEPS_BEFORE_BLOCK = int(os.environ.get("MIN_STEPS_BEFORE_BLOCK", 1))

def log_block(event: dict):
    event["ts"] = time.time()
    with open(BLOCK_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def should_block(hpa: HPA, session_id: str, session_path: List[Tuple[str,str]]) -> (bool, dict):
    """
    决定是否阻断攻击者：
    1. 路径太短 → 不阻断
    2. 完全新路径 → 不阻断
    3. 部分新状态或已知路径 → 计算 payoff, payoff > 阈值则阻断
    """
    debug = {"session_id": session_id, "path_len": len(session_path)}
    
    if len(session_path) < MIN_STEPS_BEFORE_BLOCK:
        debug["reason"] = "too_short"
        debug["decision"] = False
        return False, debug

    payoff = hpa.compute_payoff_ratio(session_path)
    debug["payoff"] = payoff
    debug["threshold"] = PAYOFF_THRESHOLD

    if payoff == "new_path":
        # 完全新路径，直接允许通行
        debug["reason"] = "new_path_allowed"
        debug["decision"] = False
        return False, debug

    # 部分新状态或完全已知路径 → 根据 payoff 阈值决定
    decision = float(payoff) >= PAYOFF_THRESHOLD
    debug["decision"] = decision

    if decision:
        debug["reason"] = "payoff_exceeded"
        log_block({
            "session": session_id,
            "decision": "block",
            "payoff": payoff,
            "path": session_path
        })
    else:
        debug["reason"] = "ok"

    return decision, debug
