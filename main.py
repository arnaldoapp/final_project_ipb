from random import random as rd
from typing import Dict, Tuple
from mpi4py import MPI

from repast4py import core, random, space, schedule, parameters
from repast4py import context as ctx

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
    
    def make_decision(self, producers=[]):
        """
            Choose "Producer" based on price (unit_cost) and trust.
        """
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
                cost = self.calculate_cost(prod.unit_cost)
                # If trust level is high or medium, make decision as usual
                if cost <= self.budget and self.usage <= prod.capacity:
                    producer_scores[prod.uid] = prod.get_score()
                else:
                    """Reduce Usage""" 
            else:
                # If trust level is low, reduce usage regardless of cost
                """Reduce Usage"""

        if(producer_scores):
            uid = max(producer_scores, key=producer_scores.get)
            best_producer = self.producers[uid]

        return best_producer, self
    
    def update_trust_level(self, uid, positive=True):
        curr_producer = self.producers[uid]
        trust_level = curr_producer.trust_level
        alpha = curr_producer.alpha
        beta = curr_producer.beta

        if positive:
            curr_producer.trust_level = min(trust_level*(1 + alpha), 1)
        else:
            curr_producer.trust_level = max(trust_level*(1 - beta), 0)

    def calculate_cost(self, unit_cost):
        return self.usage * unit_cost
    
    
class ProducerAgent(core.Agent):
    TYPE=1

    def __init__(self, local_id: int, rank: int, name, unit_cost, initial_capacity=0):
        super().__init__(id=local_id, type=ProducerAgent.TYPE, rank=rank)
        self.name = name
        self.unit_cost = unit_cost
        self.capacity = initial_capacity
        # for consumer local accounting
        self.trust_level = 0.5
        self.alpha = 0.01
        self.beta = 0.08
        self.failure_prob = 0.15
    
    def save(self) -> Tuple:
        return (self.uid, self.name, self.unit_cost, self.capacity)

    def produce_electricity(self, amount):
        """
            Function: produce electricty and updates the capacity.
            -
            It is based on the capacity avaliable, but there is a test
            for simulate the failed operation, besides the low capacity 
            scenario.
        """
        failed = rd() < self.failure_prob # failure simulation

        if amount <= self.capacity and not failed:
            self.capacity -= amount
            return "Success"
        else:
            return "Failed"
    
    def get_score(self):
        return self.unit_cost*(1+(10**(-3))-self.trust_level)


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
                                    producer_data[3]
                                )
        producer_cache[uid] = producer
    
    return producer

class Model:    
    def __init__(self, comm: MPI.Intracomm, params: Dict):
        self.runner = schedule.init_schedule_runner(comm)
        self.runner.schedule_repeating_event(1, 1, self.step)
        self.runner.schedule_stop(params['stop.at'])

        # create the context to hold the agents and manage cross process synchronization
        self.context = ctx.SharedContext(comm)

        # create a bounding box equal to the size of the entire global world grid
        box = space.BoundingBox(0, params['world.width'], 0, params['world.height'], 0, 0)
        # create a SharedGrid of 'box' size with sticky borders that allows multiple agents
        # in each grid location.
        self.grid = space.SharedGrid(name='grid', bounds=box, borders=space.BorderType.Sticky,
                                     occupancy=space.OccupancyType.Multiple, buffer_size=3, comm=comm)
        self.context.add_projection(self.grid)

        rank = comm.Get_rank()
        if rank == 0:
            agent_c1 = ConsumerAgent(123, rank, "Arnaldo", 90000, 5000)
            self.context.add(agent_c1)
        elif rank == 1:
            rng = random.default_rng
            producers = params['producers_data']

            for producer in producers:
                # get a random x,y location in the grid
                pt = self.grid.get_random_local_pt(rng)
                # Instance
                p = ProducerAgent(
                    producer["id"],
                    rank,
                    producer["name"], 
                    producer["unit_cost"], 
                    producer["initial_capacity"], 
                )
                self.context.add(p)
                self.grid.move(p, pt)

    def step(self):    
        self.context.synchronize(restore_producer)
        # producers = [(p.name, p.unit_cost, p.capacity) for p in producer_cache.values()]
        choosen = None
        consumer = None

        for agent in self.context.agents():
            if agent.type == 0:
                choosen, consumer = agent.make_decision(producer_cache)

        if choosen:
            # require slots electricity, success depends on avaliable capacity
            choosen_cache = producer_cache[choosen.uid]
            status = choosen_cache.produce_electricity(consumer.usage)

            #TODO: define some criteria on update trust level
            consumer.update_trust_level(choosen.uid, positive="Success" in status)

            space_fmt = " "*(20 - len(choosen_cache.name))
            print(f"[{status}] Choosen Producer: {choosen_cache.name}{space_fmt}| Capacity: {choosen_cache.capacity}", end=" - ")
            print(f"Local Trust Level {choosen.trust_level}")

    def start(self):
        self.runner.execute()


def run():
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
    model.start()

if __name__ == "__main__":
    run()

# mpirun -n 3 python3 main.py conf.yaml
