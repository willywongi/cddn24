import logging.config
import os
import pickle
import sys
from uuid import uuid4

from redis import Redis

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s %(levelname)s %(message)s')


def send_task(name, args=(), kwargs=None, queue_name="default"):
    redis = Redis(host=os.environ['MESSAGE_BROKER_CONTAINER_NAME'])
    
    # https://dramatiq.io/advanced.html#enqueueing-messages-from-other-languages
    redis_message_id = str(uuid4())
    message_id = str(uuid4())
    message = {
        "queue_name": queue_name,
        "actor_name": name,
        "args": args or [],
        "kwargs": kwargs or {},
        "options": {
            "redis_message_id": redis_message_id
        },
        "message_id": message_id,
        "message_timestamp": 0
    }
    redis.hset(f"dramatiq:{queue_name}.msgs", redis_message_id, pickle.dumps(message))
    redis.rpush(f"dramatiq:{queue_name}", redis_message_id)


TASKS = {
    'delete_old_tasks': {
        'kwargs': {
            "max_task_age": 604800
        }
    },
    # Your tasks must be Dramatiq actors:
    # @dramatiq.actor
    # def your_scheduled_task():
    #   pass
}

if __name__ == "__main__":
    task_name = sys.argv[1]
    task_options = TASKS[task_name]
    name = task_options.pop('name', task_name)
    send_task(name, **task_options)
    logger.info("[%s] Task sent", name)
