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
                cost = self.calculate_cost(prod.unit_cost, total_usage)
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
    
    def update_trust_level(self, uid, positive=True):
        curr_producer = self.producers[uid]
        trust_level = curr_producer.trust_level
        alpha = curr_producer.alpha
        beta = curr_producer.beta

        if positive:
            curr_producer.trust_level = min(trust_level*(1 + alpha), 1)
        else:
            curr_producer.trust_level = max(trust_level*(1 - beta), 0)

    def calculate_cost(self, unit_cost, usage):
        return usage * unit_cost
    
    
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
        rng = random.default_rng

        if rank == 0:
            consumers = params['consumers_data']

            for consumer in consumers:
                # get a random x,y location in the grid
                pt = self.grid.get_random_local_pt(rng)
                # Instance
                c = ConsumerAgent(
                    consumer["id"],
                    rank,
                    consumer["name"], 
                    consumer["budget"], 
                    consumer["usage"], 
                )
                self.context.add(c)
                self.grid.move(c, pt)
        elif rank == 1:
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
        best_producers = []
        curr_consumers = []
        total_usage = 0
        total_budget = 0

        for agent in self.context.agents():
            if agent.type == 0:
                total_budget += agent.budget
                total_usage += agent.usage

        for agent in self.context.agents():
            if agent.type == 0:
                producer, consumer = agent.make_decision(producer_cache, total_budget, total_usage)
                best_producers.append(producer)
                curr_consumers.append(consumer)
                # print(producer.uid, consumer.name)

        if best_producers:
            keys = list(best.uid if best else None for best in best_producers)
            unique_elements = list(set(keys))
            unique_elements = unique_elements.remove(None) if None in unique_elements else unique_elements
            choosen_uid = max(unique_elements, key=lambda x: keys.count(x)) if unique_elements else None
            best_producer = best_producers[keys.index(choosen_uid)]

            if choosen_uid:
                # require slots electricity, success depends on avaliable capacity
                choosen_cache = producer_cache[choosen_uid]
                status = choosen_cache.produce_electricity(total_usage)

                # #TODO: define some criteria on update trust level
                for consumer in curr_consumers:
                    consumer.update_trust_level(choosen_uid, positive="Success" in status)

                space_fmt = " "*(20 - len(choosen_cache.name))
                print(f"[{status}] Choosen Producer: {choosen_cache.name}{space_fmt}| Capacity: {choosen_cache.capacity}", end=" - ")
                print(f"Local Trust Level {best_producer.trust_level}")

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
