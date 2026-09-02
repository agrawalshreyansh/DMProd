from redis import Redis
from rq import Queue

from app.config import settings

_connection: Redis | None = None


def get_queue(connection: Redis | None = None) -> Queue:
    """RQ queue bound to the shared Redis connection.

    Tests inject a `fakeredis` connection here instead of hitting real Redis
    (same pattern as `app.db.init_db`'s optional `client` param).
    """
    global _connection
    if connection is not None:
        _connection = connection
    if _connection is None:
        _connection = Redis.from_url(settings.redis_url)
    return Queue("reels", connection=_connection)
