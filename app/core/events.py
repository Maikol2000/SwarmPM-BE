import json
from collections.abc import Mapping

from redis import Redis

from app.core.config import get_settings


class DomainEventPublisher:
    def publish(self, stream: str, event: Mapping[str, str]) -> None:
        raise NotImplementedError


class RedisStreamPublisher(DomainEventPublisher):
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def publish(self, stream: str, event: Mapping[str, str]) -> None:
        self._redis.xadd(stream, fields=dict(event), maxlen=10000, approximate=True)


class NoopEventPublisher(DomainEventPublisher):
    def publish(self, stream: str, event: Mapping[str, str]) -> None:
        # Local dev and tests can run without Redis while keeping the call path in place.
        _ = (stream, event)


def build_event_publisher() -> DomainEventPublisher:
    settings = get_settings()
    if not settings.redis_url:
        return NoopEventPublisher()

    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return RedisStreamPublisher(client)
    except Exception:
        return NoopEventPublisher()


def encode_event_payload(event: Mapping[str, object]) -> dict[str, str]:
    return {"payload": json.dumps(event, separators=(",", ":"), default=str)}
