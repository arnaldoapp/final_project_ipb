from src.model.producer import ProducerAgent
from typing import Tuple

from repast4py import core

class ConsumerAgent(core.Agent):
    TYPE=0

    def __init__(self, local_id: int, rank: int, name, budget, initial_usage=0):
        super().__init__(id=local_id, type=ConsumerAgent.TYPE, rank=rank)
        self.name = name
        self.budget = budget
        self.usage = initial_usage
        self.producers = {}

    def save(self) -> Tuple:
        return (self.uid, self.name, self.budget, self.usage)
    
    def update_trust_level(self, uid, positive=True):
        curr_producer = self.producers[uid]
        trust_level = curr_producer.trust_level
        alpha = curr_producer.alpha
        beta = curr_producer.beta

        if positive:
            curr_producer.trust_level = min(trust_level*(1 + alpha), 1)
        else:
            curr_producer.trust_level = max(trust_level*(1 - beta), 0)

        return curr_producer.trust_level
    
    def make_decision(self, producers=[], total_budget=0, total_usage=0):
        """
            Choose "Producer" based on price (unit_cost) and trust.
        """
        total_usage = total_usage if total_usage else self.usage
        total_budget = total_budget if total_budget else self.budget
        producer_scores = {}
        best_producer = None
        
        for prod in producers:
            if prod not in self.producers.keys():
                self.producers[prod] = ProducerAgent(
                                            producers[prod].uid[0],
                                            producers[prod].uid[2],
                                            producers[prod].name,
                                            producers[prod].unit_cost,
                                            producers[prod].capacity,
                                        )
            else:
                self.producers[prod].capacity = producers[prod].capacity
                self.producers[prod].unit_cost = producers[prod].unit_cost

        # Execute Decision
        for prod in self.producers.values():
            # Adjust decision based on trust level
            if prod.trust_level >= 0.5:
                cost = prod.unit_cost * total_usage # calculate cost
                # If trust level is high or medium, make decision as usual
                if cost <= total_budget and total_usage <= prod.capacity:
                    producer_scores[prod.uid] = prod.get_score()
                else:
                    """Reduce Usage""" 
            else:
                # If trust level is low, reduce usage regardless of cost
                """Reduce Usage"""

        if(producer_scores):
            uid = min(producer_scores, key=producer_scores.get)
            best_producer = self.producers[uid]

        return best_producer, self
