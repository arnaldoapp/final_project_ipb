from repast4py import random

def add_agents(model, agents_data, rank, agent_class, *args):    
    rng = random.default_rng

    for agent_data in agents_data:
        # Get a random x,y location in the grid
        pt = model.grid.get_random_local_pt(rng)
        
        # Create an instance of the agent
        agent = agent_class(
            agent_data["id"],
            rank,
            *[agent_data[arg] for arg in args]
        )
        
        model.context.add(agent)
        model.grid.move(agent, pt)

def compare_scores(local_best_producer, chosen):
    score_diff = local_best_producer.get_score() - chosen.get_score()

    return score_diff < -4, score_diff
