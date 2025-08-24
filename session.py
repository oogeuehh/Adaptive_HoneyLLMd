from command_parser import parse_command
from hpa_loader import nodes_dict
from payoff_calculator import max_path_prob

class Session:
    def __init__(self, session_id):
        self.session_id = session_id
        self.current_node_id = 1  # 根节点
        self.process_vector = []  # 存储(macro, micro)元组
        self.matched = True
        self.src_node_id = None
        self.dst_node_id = None
        self.actual_prob = 1.0
        self.is_first_pair = True
        
    def add_command(self, command):
        pairs = parse_command(command)
        for macro, micro in pairs:
            current_node = nodes_dict[self.current_node_id]
            found = False
            for child in current_node['children']:
                child_node = nodes_dict[child['node_id']]
                if child_node['name'] == macro:
                    transition_prob = child['prob']
                    micro_found = False
                    for m in child_node['micros']:
                        if m['name'] == micro:
                            micro_prob = m['prob']
                            micro_found = True
                            break
                    if micro_found:
                        if self.is_first_pair:
                            self.actual_prob *= micro_prob
                            self.is_first_pair = False
                        else:
                            self.actual_prob *= transition_prob * micro_prob
                            
                        self.current_node_id = child['node_id']
                        if self.src_node_id is None:
                            self.src_node_id = self.current_node_id
                        self.dst_node_id = self.current_node_id
                        self.process_vector.append((macro, micro))
                        found = True
                        break
            if not found:
                self.matched = False
                break
                
    def get_payoff(self):
        if not self.matched:
            return None
        if self.src_node_id is None or self.dst_node_id is None:
            return None
        max_prob = max_path_prob(self.src_node_id, self.dst_node_id)
        if max_prob == 0:
            return 0.0
        return self.actual_prob / max_prob
        
    def should_block(self, threshold=0.8):
        if not self.matched:
            return False
        payoff = self.get_payoff()
        if payoff is None:
            return False
