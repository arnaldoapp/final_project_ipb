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

    def save(self) -> Tuple:
        return (self.uid, self.name, self.budget, self.usage)
    
    def make_decision(self, producers=[]):
        """
            Choose "Producer" based on price (unit_cost) and trust.
        """
        print("Making Decision...", producers)
    

class ProducerAgent(core.Agent):
    TYPE=1

    def __init__(self, local_id: int, rank: int, name, unit_cost, initial_capacity=0):
        super().__init__(id=local_id, type=ProducerAgent.TYPE, rank=rank)
        self.name = name
        self.unit_cost = unit_cost
        self.capacity = initial_capacity
    
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
        if amount <= self.capacity:
            self.capacity -= amount
            return True
        else:
            return False

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
            agent_c1 = ConsumerAgent(123, rank, "Arnaldo", 5000, 9)
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
        producers = [(p.name, p.unit_cost, p.capacity) for p in producer_cache.values()]

        for agent in self.context.agents():
            if agent.type == 0:
                agent.make_decision(producers)

    def start(self):
        self.runner.execute()


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
    model.start()

main()

# mpirun -n 3 python3 main.py conf.yaml
