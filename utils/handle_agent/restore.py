from src.model.producer import ProducerAgent

from typing import Tuple

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
