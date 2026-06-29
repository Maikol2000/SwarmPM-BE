from app.schemas import SpaceCategory, SpaceSubcategory


def list_categories() -> list[SpaceCategory]:
    return [
        SpaceCategory(
            id="ops",
            name="Operations",
            subcategories=[
                SpaceSubcategory(id="ops-standup", name="Standup"),
                SpaceSubcategory(id="ops-reviews", name="Reviews"),
            ],
        ),
        SpaceCategory(
            id="build",
            name="Build",
            subcategories=[
                SpaceSubcategory(id="build-api", name="API"),
                SpaceSubcategory(id="build-ui", name="UI"),
            ],
        ),
    ]
