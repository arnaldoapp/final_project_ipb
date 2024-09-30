from mpi4py import MPI
from typing import Tuple

from repast4py import core, random, space, schedule, logging, parameters
from repast4py import context as ctx
import repast4py

class ClassA(core.Agent):
    TYPE=0

    def __init__(self, local_id: int, rank: int):
        super().__init__(id=local_id, type=ClassA.TYPE, rank=rank)
        self.count = 0

    def sum_counter(self):
        self.count += 1
        print(f'classe A | contador em {self.count}')

    def save(self) -> Tuple:
        return (self.uid, self.count)

class ClassB(core.Agent):
    TYPE=1

    def __init__(self, local_id: int, rank: int):
        super().__init__(id=local_id, type=ClassB.TYPE, rank=rank)
        self.count = 0

    def sum_counter(self):
        self.count += 1
        print(f'classe B | contador em {self.count}')

    def save(self) -> Tuple:
        return (self.uid, self.count)

class Model:
    def __init__(self, comm: MPI.Intracomm):
        self.runner = schedule.init_schedule_runner(comm)
        self.runner.schedule_repeating_event(1, 1, self.handle_agent)
        self.runner.schedule_stop(20)

        # create the context to hold the agents and manage cross process synchronization
        self.context = ctx.SharedContext(comm)

        rank = comm.Get_rank()
        if rank == 0:
            agent = ClassA(0, rank)
            self.context.add(agent)
        elif rank == 1:
            agent = ClassB(0, rank)
            self.context.add(agent)

    def handle_agent(self):
        for agent in self.context.agents():
            agent.sum_counter()

def main():
    comm = MPI.COMM_WORLD
    # id = comm.Get_rank()                    #number of the process running the code
    # numProcesses = comm.Get_size()          #total number of processes running
    # myHostName = MPI.Get_processor_name()   #machine name running the code

    model = Model(comm)
    model.runner.execute()

main()

# mpirun -n 2 python3 main.py
