import random as rd

from typing import Dict, Tuple
from mpi4py import MPI

from repast4py import core, random, space, schedule, logging, parameters
from repast4py import context as ctx

class ConsumerAgent(core.Agent):
    TYPE=0

    def __init__(self, local_id: int, rank: int, name, budget, initial_usage=0):
        super().__init__(id=local_id, type=ConsumerAgent.TYPE, rank=rank)
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

        print(f"Choosen Producer: {max_score_producer_name}")
        return max_score_producer_name  

    def save(self) -> Tuple:
        return (self.uid, self.budget)
    

class ProducerAgent(core.Agent):
    TYPE=1

    def __init__(self, local_id: int, rank: int, name, initial_trust_level, unit_cost, initial_capacity=0, energy_type=1, failure_prob=0):
        super().__init__(id=local_id, type=ProducerAgent.TYPE, rank=rank)
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
            self.trust_level = max(self.trust_level*(1 - self.beta), 0)
        else:
            self.trust_level = min(self.trust_level*(1 + self.alpha), 1)  
        self.print_status()

    def set_alpha_beta(self, gammas=[]):
        self.alpha = gammas[0]*self.significance + gammas[1]*self.trend
        self.beta = gammas[2]*self.significance + gammas[3]*self.trend
    
    def isOperationFailed(self):
        """
            Function: decide if the operation is failed or not
        """
        if rd.random() < self.failure_prob:
            return True
        else:
            return False

    def print_status(self):
        space_fmt = " "*(20 - len(self.name))
        print(f"{self.name}{space_fmt}| TRUST LEVEL: {self.trust_level} - CAPACITY: {self.capacity}")

    def save(self) -> Tuple:
        return (self.uid, self.name, self.trust_level, self.unit_cost, self.capacity, self.energy_type, self.failure_prob)

producer_cache = {}  

def restore_producer(producer_data: Tuple):    
    """
    Args:
        producer_data: tuple containing the data returned by producer.save.
    """
    # uid is a 3 element tuple: 0 is id, 1 is type, 2 is rank
    uid = producer_data[0] 

    if uid in producer_cache:    
        producer = producer_cache[uid]
    else:    
        producer = ProducerAgent(
                                    uid[0], uid[2], 
                                    producer_data[1],
                                    producer_data[2],
                                    producer_data[3],
                                    producer_data[4],
                                    producer_data[5],
                                    producer_data[6]
                                )
        producer_cache[uid] = producer

    producer.name = producer_data[1]    
    producer.trust_level = producer_data[2]    
    producer.unit_cost = producer_data[3]    
    producer.capacity = producer_data[4]  
    producer.energy_type = producer_data[5]  
    producer.failure_prob = producer_data[6]  
    
    return producer

class Model:    
    def __init__(self, comm: MPI.Intracomm, params: Dict):
        self.runner = schedule.init_schedule_runner(comm)
        self.runner.schedule_repeating_event(1, 1, self.handle_agent)
        self.runner.schedule_stop(20)

        # create the context to hold the agents and manage cross process synchronization
        self.context = ctx.SharedContext(comm)

        # create a bounding box equal to the size of the entire global world grid
        box = space.BoundingBox(0, params['world.width'], 0, params['world.height'], 0, 0)
        # create a SharedGrid of 'box' size with sticky borders that allows multiple agents
        # in each grid location.
        self.grid = space.SharedGrid(name='grid', bounds=box, borders=space.BorderType.Sticky,
                                     occupancy=space.OccupancyType.Multiple, buffer_size=2, comm=comm)
        self.context.add_projection(self.grid)

        rank = comm.Get_rank()
        if rank == 0:
            agent_c1 = ConsumerAgent(123, rank, "Arnaldo", 5000, 9)
            self.context.add(agent_c1)
        elif rank == 1:
            rng = random.default_rng
            producers = params['producers_data']

            for producer in producers:
                # get a random x,y location in the grid
                pt = self.grid.get_random_local_pt(rng)
                # Instance
                p = ProducerAgent(111, rank, "Eólica", 0.8, 12, 1200, 1, 0.2)
                # p = ProducerAgent(
                #     producer["id"], 
                #     rank, 
                #     producer["name"], 
                #     producer["initial_trust_level"], 
                #     producer["unit_cost"], 
                #     producer["initial_capacity"], 
                #     producer["energy_type"], 
                #     producer["failure_prob"]
                # )
                self.context.add(p)
                self.grid.move(p, pt)

    def handle_agent(self):    
        self.context.synchronize(restore_producer)

        for agent in self.context.agents():
            if agent.type == 0:
                print(list(producer_cache.values()))
                agent.make_decision(producer_cache.values())


def main():
    comm = MPI.COMM_WORLD
    # id = comm.Get_rank()                    #number of the process running the code
    # numProcesses = comm.Get_size()          #total number of processes running
    # myHostName = MPI.Get_processor_name()   #machine name running the code
    
    parser = parameters.create_args_parser()
    args = parser.parse_args()
    params = parameters.init_params(args.parameters_file, args.parameters)

    # Run Model
    # ---
    # Instance
    model = Model(comm, params)
    # Start Model
    model.runner.execute()

main()

# mpirun -n 2 python3 main.py conf.yaml
