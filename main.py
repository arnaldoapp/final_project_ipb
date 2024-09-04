import random

class CommonAgent:
    def __init__(self, local_id: int, name: str, trust_level: float):
        self.name = name
        self.trust_level = trust_level
        self.alpha = 0.01
        self.beta = 0.08
        # On the furute these vars (gammas, significance, trend) should be setted by:
        # PRODUCER: seasonality based on its energy type and avaliability.
        # CONSUMER: consumer payment historic
        self.gammas = []
        self.significance = None
        self.trend = None
        # On the furute we can add the historic of failures and trust level to update that.
        self.failure_prob = None

    def update_trust_level(self, failed=False):
        if failed:
            self.trust_level = self.trust_level*(1 - self.beta)
        else:
            self.trust_level = self.trust_level*(1 + self.alpha)

    def set_alpha_beta(gammas=[]):
        self.alpha = gammas[0]*significance + gammas[1]*trend
        self.beta = gammas[2]*significance + gammas[3]*trend
    
    def isOperationFailed(self, failure_prob=0.0):
        """
            Function: decide if the operation is failed or not
        """
        if random.random() < failure_prob / 100:
            return True
        else:
            return False


class ConsumerAgent(CommonAgent):
    def __init__(self, name, budget, initial_usage=0):
        super().__init__(name=name, trust_level=1)
        self.budget = budget
        self.usage = initial_usage
    
    def consume_electricity(self, amount):
        """
            Function: consume electricty based on the best tradeoff 
            (make decision).
            -
            There is a test for simulate the failed operation.
        """
        if self.isOperationFailed():
            self.make_decision()
            self.update_trust_level()
            return True
        else:
            self.update_trust_level(failed=True)
            return False

    def make_decision():
        """
            Choose "Producer" based on price (unit_cost) and trust.
        """
        producer_scores = {}
        for prod in producers:
            producer_scores[prod.name] = prod.get_score()
            # how add budget criteria on best producer calculation?
            # self.budget
    

class ProducerAgent(CommonAgent):
    def __init__(self, name, unit_cost, energy_type, initial_capacity=0):
        super().__init__(name=name, trust_level=1)
        self.unit_cost = unit_cost
        self.capacity = initial_capacity
        self.energy_type
        # measured by the seasonality based on its energy type and avaliability. 
        self.quality = None

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
            return False

    def get_score():
        return self.unit_cost*(1+0.001-self.trust_level)

