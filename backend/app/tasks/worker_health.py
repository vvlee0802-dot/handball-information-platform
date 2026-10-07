from redis import Redis
from rq import Queue, Worker

from app.core.config import settings


def main() -> int:
    connection = Redis.from_url(settings.redis_url)
    connection.ping()
    queue = Queue(settings.task_queue_name, connection=connection)
    workers = Worker.all(connection=connection, queue=queue)
    return 0 if any(worker.get_state() in {"busy", "idle"} for worker in workers) else 1


if __name__ == "__main__":
    raise SystemExit(main())
