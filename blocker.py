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
    """Return (block_decision, debug_info)"""
    debug = {"session_id": session_id, "path_len": len(session_path)}
    if len(session_path) < MIN_STEPS_BEFORE_BLOCK:
        debug["reason"] = "too_short"
        return False, debug
    payoff = hpa.compute_payoff_ratio(session_path)
    debug["payoff"] = payoff
    debug["threshold"] = PAYOFF_THRESHOLD
    decision = payoff >= PAYOFF_THRESHOLD
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
