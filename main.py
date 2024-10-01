import random
import time

class ConsumerAgent():
    def __init__(self, local_id: int, name, budget, initial_usage=0):
        self.name = name
        self.budget = budget
        self.usage = initial_usage

    def calculate_cost(self, price_per_unit):
        return self.usage * price_per_unit

    def make_decision(self, producers=[]):
        """
            Choose "Producer" based on price (unit_cost) and trust.
        """
        producer_scores = {}
        for prod in producers:
            # how add budget criteria on best producer calculation?
            # self.budget
            # Adjust decision based on trust level
            if prod.trust_level >= 0.5:
                # If trust level is high or medium, make decision as usual
                cost = self.calculate_cost(prod.unit_cost)
                if cost <= self.budget and prod.produce_electricity(self.usage):
                    producer_scores[prod.name] = prod.get_score()
                else:
                    """Reduce Usage""" 
            else:
                # If trust level is low, reduce usage regardless of cost
                """Reduce Usage"""

        if(producer_scores):
            max_score_producer_name = max(producer_scores, key=producer_scores.get)
        else:
            max_score_producer_name = "None producer avaliable."

        return max_score_producer_name
    

class ProducerAgent:
    def __init__(self, local_id: int, name, initial_trust_level, unit_cost, initial_capacity=0, energy_type=1, failure_prob=0):
        self.name = name
        self.trust_level = initial_trust_level
        self.unit_cost = unit_cost
        self.capacity = initial_capacity
        self.energy_type = energy_type
        self.alpha = 0.01
        self.beta = 0.08
        # On the furute we can add the historic of failures and trust level to update that.
        self.failure_prob = failure_prob
        # measured by the seasonality based on its energy type and avaliability. 
        self.quality = 0.9  # Initial quality rating
        # On the furute these vars (gammas, significance, trend) should be setted by:
        # PRODUCER: seasonality based on its energy type and avaliability.
        # CONSUMER: consumer payment historic
        self.gammas = []
        self.significance = None
        self.trend = None

    def produce_electricity(self, amount):
        """
            Function: produce electricty and updates the capacity.
            -
            It is based on the capacity avaliable, but there is a test
            for simulate the failed operation, besides the low capacity 
            scenario.
        """
        if amount <= self.capacity and not self.isOperationFailed():
            self.capacity -= amount
            self.update_trust_level()
            return True
        else:
            self.update_trust_level(failed=True)
            return False

    def get_score(self):
        return self.unit_cost*(1+0.001-self.trust_level)

    def update_trust_level(self, failed=False):
        if failed:
            self.trust_level = self.trust_level*(1 - self.beta)
        else:
            self.trust_level = min(self.trust_level*(1 + self.alpha), 1)

    def set_alpha_beta(gammas=[]):
        self.alpha = gammas[0]*significance + gammas[1]*trend
        self.beta = gammas[2]*significance + gammas[3]*trend
    
    def isOperationFailed(self):
        """
            Function: decide if the operation is failed or not
        """
        if random.random() < self.failure_prob:
            return True
        else:
            return False

    def print_status(self):
        space_fmt = " "*(20 - len(self.name))
        print(f"{self.name}{space_fmt}| TRUST LEVEL: {self.trust_level} - CAPACITY: {self.capacity}")


p1 = ProducerAgent(111, "Eólica", 0.8, 12, 1200, 1, 0.2)
p2 = ProducerAgent(222, "Solar", 0.75, 6, 600, 2, 0.15)
p3 = ProducerAgent(333, "Hidroelétrica", 0.9, 17, 1700, 3, 0.1)

c1 = ConsumerAgent(123, "Genivaldo", 5000, 9)

while(True):
    p1.print_status()
    p2.print_status()
    p3.print_status()

    print(c1.make_decision([p1,p2,p3]))

    time.sleep(2)
