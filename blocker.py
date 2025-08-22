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
    debug = {"session_id": session_id, "path_len": len(session_path)}

    if len(session_path) < MIN_STEPS_BEFORE_BLOCK:
        debug.update({"reason": "too_short", "decision": False})
        return False, debug

    # update HPA first
    hpa.update_from_session(session_path)

    current_prob = hpa.path_probability(session_path)
    payoff = hpa.compute_payoff_ratio(session_path)

    macro, micro = session_path[-1]
    macro_obj = hpa.get_macro(macro)

    # case 1: completely new macro
    if macro not in hpa.hpa.get("macros", {}):
        debug.update({"reason": "new_macro", "decision": False, "payoff": 1.0})
        return False, debug

    # case 2: new micro
    if micro not in macro_obj.get("micro_probs", {}):
        debug.update({"reason": "new_micro_added", "decision": False, "payoff": payoff})
        return False, debug

    # case 3: known path
    decision = False
    if payoff > PAYOFF_THRESHOLD:
        # payoff=1 but existing path => block
        decision = True

    debug.update({"payoff": payoff, "threshold": PAYOFF_THRESHOLD, "decision": decision})
    if decision:
        debug["reason"] = "payoff_exceeded"
        log_block({"session": session_id, "decision": "block", "payoff": payoff, "path": session_path})
    else:
        debug["reason"] = "ok"

    return decision, debug

