"""TaskIQ broker configuration.

Uses Redis as the message queue backend. The broker is shared
across all task modules.

Run the worker:
    taskiq worker app.tasks.broker:broker
"""

from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.config import get_settings

settings = get_settings()
_redis_url = str(settings.redis_url)

result_backend = RedisAsyncResultBackend(redis_url=_redis_url)

broker = ListQueueBroker(url=_redis_url).with_result_backend(result_backend)
