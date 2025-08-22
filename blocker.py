# blocker.py
import os
from hpa_manager import HPA

PAYOFF_THRESHOLD = float(os.environ.get("PAYOFF_THRESHOLD", 0.8))

def should_block(hpa: HPA, session_id: str, actual_path, src: int, dst: int, matched: bool) -> bool:
    """
    :param hpa: object HPA
    :param session_id
    :param actual_path: [(position, macro, micro), ...]
    :param src
    :param dst
    :param matched: (True/False)
    """

    if matched:
        payoff = hpa.compute_payoff(actual_path, src, dst)
        if payoff > PAYOFF_THRESHOLD:
            return True
        else:
            return False
    else:
        return False


