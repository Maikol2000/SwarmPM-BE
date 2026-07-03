import json
from time import monotonic

from pydantic import TypeAdapter

from app.core.config import get_settings
from app.schemas import SpaceCategory, SpaceContent, SpaceContentItem, SpaceDepartment, SpaceSubcategory, SpaceTrend

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - dependency is declared in requirements
    Redis = None

    class RedisError(Exception):
        pass

_CACHE_TTL_SECONDS = 300
_cache: dict[str, tuple[float, object]] = {}
_redis_client = None
_category_list_adapter = TypeAdapter(list[SpaceCategory])
_content_map_adapter = TypeAdapter(dict[tuple[str, str], SpaceContent])
_department_list_adapter = TypeAdapter(list[SpaceDepartment])
_trend_list_adapter = TypeAdapter(list[SpaceTrend])


def _get_redis_client():
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    if not settings.redis_url or Redis is None:
        return None

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        client.ping()
    except RedisError:
        return None

    _redis_client = client
    return _redis_client


def _cache_backend() -> str:
    return "redis" if _get_redis_client() is not None else "memory"


def _serialize(cache_key: str, value: object) -> str:
    if cache_key == "categories":
        return json.dumps(_category_list_adapter.dump_python(value, mode="json"))
    if cache_key == "content":
        payload = {
            f"{category_id}::{subcategory_id}": panel.model_dump(mode="json")
            for (category_id, subcategory_id), panel in value.items()
        }
        return json.dumps(payload)
    if cache_key == "departments":
        return json.dumps(_department_list_adapter.dump_python(value, mode="json"))
    if cache_key == "trending":
        return json.dumps(_trend_list_adapter.dump_python(value, mode="json"))
    raise KeyError(f"Unsupported cache key: {cache_key}")


def _deserialize(cache_key: str, payload: str) -> object:
    decoded = json.loads(payload)
    if cache_key == "categories":
        return _category_list_adapter.validate_python(decoded)
    if cache_key == "content":
        return {
            tuple(compound_key.split("::", 1)): SpaceContent.model_validate(panel)
            for compound_key, panel in decoded.items()
        }
    if cache_key == "departments":
        return _department_list_adapter.validate_python(decoded)
    if cache_key == "trending":
        return _trend_list_adapter.validate_python(decoded)
    raise KeyError(f"Unsupported cache key: {cache_key}")


def _with_cache(cache_key: str, builder):
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            cached = redis_client.get(f"spaces:{cache_key}")
        except RedisError:
            cached = None
        if cached is not None:
            return _deserialize(cache_key, cached)

    now = monotonic()
    cached = _cache.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]

    value = builder()
    _cache[cache_key] = (now + _CACHE_TTL_SECONDS, value)
    if redis_client is not None:
        try:
            redis_client.setex(f"spaces:{cache_key}", _CACHE_TTL_SECONDS, _serialize(cache_key, value))
        except RedisError:
            pass
    return value


def _build_categories() -> list[SpaceCategory]:
    return sorted(
        [
            SpaceCategory(
                id="ops",
                name="Operations",
                icon="briefcase",
                order=1,
                subcategories=[
                    SpaceSubcategory(
                        id="ops-standup",
                        category_id="ops",
                        name="Standup",
                        badge_count=3,
                        ticker="8 live blockers",
                        stats={"active_threads": 8, "members": 14},
                    ),
                    SpaceSubcategory(
                        id="ops-reviews",
                        category_id="ops",
                        name="Reviews",
                        badge_count=1,
                        ticker="2 reviews pending",
                        stats={"reviews_pending": 2, "sla_hours": 6},
                    ),
                ],
            ),
            SpaceCategory(
                id="build",
                name="Build",
                icon="hammer",
                order=2,
                subcategories=[
                    SpaceSubcategory(
                        id="build-api",
                        category_id="build",
                        name="API",
                        badge_count=5,
                        ticker="5 deploy items",
                        stats={"open_prs": 5, "deploys_today": 2},
                    ),
                    SpaceSubcategory(
                        id="build-ui",
                        category_id="build",
                        name="UI",
                        badge_count=2,
                        ticker="2 regressions tracked",
                        stats={"bugs": 2, "stories_ready": 7},
                    ),
                ],
            ),
            SpaceCategory(
                id="people",
                name="People",
                icon="users",
                order=3,
                subcategories=[
                    SpaceSubcategory(
                        id="people-hiring",
                        category_id="people",
                        name="Hiring",
                        badge_count=4,
                        ticker="4 candidates in loop",
                        stats={"interviews": 4, "offers": 1},
                    ),
                    SpaceSubcategory(
                        id="people-recognition",
                        category_id="people",
                        name="Recognition",
                        badge_count=0,
                        ticker="Badges refresh at 17:00 UTC",
                        stats={"kudos": 11, "milestones": 3},
                    ),
                ],
            ),
        ],
        key=lambda category: category.order,
    )


def _build_content() -> dict[tuple[str, str], SpaceContent]:
    return {
        ("ops", "ops-standup"): SpaceContent(
            category_id="ops",
            subcategory_id="ops-standup",
            ticker="8 live blockers",
            items=[
                SpaceContentItem(
                    id="ops-standup-1",
                    title="Morning blockers digest",
                    summary="Two backend tasks are blocked on staging credentials.",
                    status="needs-attention",
                    owner="mike",
                ),
                SpaceContentItem(
                    id="ops-standup-2",
                    title="EMEA handoff ready",
                    summary="Runbook notes have been posted for the overnight queue.",
                    status="on-track",
                    owner="sofia",
                ),
            ],
        ),
        ("ops", "ops-reviews"): SpaceContent(
            category_id="ops",
            subcategory_id="ops-reviews",
            ticker="2 reviews pending",
            items=[
                SpaceContentItem(
                    id="ops-reviews-1",
                    title="Escalated QA review",
                    summary="Regression ticket needs backend sign-off before release.",
                    status="pending-review",
                    owner="ana",
                )
            ],
        ),
        ("build", "build-api"): SpaceContent(
            category_id="build",
            subcategory_id="build-api",
            ticker="5 deploy items",
            items=[
                SpaceContentItem(
                    id="build-api-1",
                    title="Gateway cutover checklist",
                    summary="Rate limit rules are queued for the next deploy train.",
                    status="in-progress",
                    owner="mike",
                )
            ],
        ),
        ("build", "build-ui"): SpaceContent(
            category_id="build",
            subcategory_id="build-ui",
            ticker="2 regressions tracked",
            items=[
                SpaceContentItem(
                    id="build-ui-1",
                    title="Composer alignment issue",
                    summary="Layout shift reproduced on Safari and assigned for patching.",
                    status="triaged",
                    owner="leo",
                )
            ],
        ),
        ("people", "people-hiring"): SpaceContent(
            category_id="people",
            subcategory_id="people-hiring",
            ticker="4 candidates in loop",
            items=[
                SpaceContentItem(
                    id="people-hiring-1",
                    title="Backend interview loop",
                    summary="One candidate advanced to final system design round.",
                    status="scheduled",
                    owner="riley",
                )
            ],
        ),
        ("people", "people-recognition"): SpaceContent(
            category_id="people",
            subcategory_id="people-recognition",
            ticker="Badges refresh at 17:00 UTC",
            items=[
                SpaceContentItem(
                    id="people-recognition-1",
                    title="Milestone spotlight",
                    summary="Three contributors unlocked new delivery badges this week.",
                    status="published",
                    owner="nina",
                )
            ],
        ),
    }


def _build_departments() -> list[SpaceDepartment]:
    return [
        SpaceDepartment(id="dept-ops", name="Operations", category_id="ops", active_users=14, badge_count=4),
        SpaceDepartment(id="dept-build", name="Engineering", category_id="build", active_users=22, badge_count=7),
        SpaceDepartment(id="dept-people", name="People Ops", category_id="people", active_users=8, badge_count=1),
    ]


def _build_trending() -> list[SpaceTrend]:
    return [
        SpaceTrend(id="trend-ops-standup", label="Standup blockers", category_id="ops", subcategory_id="ops-standup", score=0.98),
        SpaceTrend(id="trend-build-api", label="API deploy train", category_id="build", subcategory_id="build-api", score=0.93),
        SpaceTrend(id="trend-people-hiring", label="Hiring pipeline", category_id="people", subcategory_id="people-hiring", score=0.81),
    ]


def list_categories() -> list[SpaceCategory]:
    return _with_cache("categories", _build_categories)


def list_subcategories(category_id: str) -> list[SpaceSubcategory] | None:
    categories = list_categories()
    for category in categories:
        if category.id == category_id:
            return category.subcategories
    return None


def get_space_content(category_id: str, subcategory_id: str) -> SpaceContent | None:
    content = _with_cache("content", _build_content)
    return content.get((category_id, subcategory_id))


def list_departments() -> list[SpaceDepartment]:
    return _with_cache("departments", _build_departments)


def list_trending() -> list[SpaceTrend]:
    return _with_cache("trending", _build_trending)


def refresh_cache() -> dict[str, int | str]:
    _cache.clear()
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.delete("spaces:categories", "spaces:content", "spaces:departments", "spaces:trending")
        except RedisError:
            pass
    categories = list_categories()
    departments = list_departments()
    trending = list_trending()
    content = _with_cache("content", _build_content)
    return {
        "status": "refreshed",
        "cache_backend": _cache_backend(),
        "categories": len(categories),
        "departments": len(departments),
        "trending": len(trending),
        "content_panels": len(content),
        "ttl_seconds": _CACHE_TTL_SECONDS,
    }
