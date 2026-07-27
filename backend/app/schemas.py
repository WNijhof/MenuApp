import datetime

from pydantic import BaseModel, ConfigDict


class SourceCreate(BaseModel):
    name: str
    base_url: str
    sitemap_url: str | None = None
    max_pages: int = 300


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    sitemap_url: str | None
    enabled: bool
    max_pages: int
    last_synced_at: datetime.datetime | None
    last_sync_found: int
    last_sync_error: str | None
    recipe_count: int = 0


class SourceUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    sitemap_url: str | None = None
    enabled: bool | None = None
    max_pages: int | None = None


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int | None
    url: str
    title: str
    image_url: str | None
    dish_type: str
    course: str
    rating: str | None
    cuisine: str | None
    ingredients: list[str]
    instructions: list[str]
    prep_time_minutes: int | None
    cook_time_minutes: int | None
    total_time_minutes: int | None
    servings: str | None
    has_offer: bool = False

    @staticmethod
    def from_model(recipe, has_offer: bool = False):
        import json

        return RecipeOut(
            id=recipe.id,
            source_id=recipe.source_id,
            url=recipe.url,
            title=recipe.title,
            image_url=recipe.image_url,
            dish_type=recipe.dish_type,
            course=recipe.course,
            rating=recipe.rating,
            cuisine=recipe.cuisine,
            ingredients=json.loads(recipe.ingredients_json or "[]"),
            instructions=json.loads(recipe.instructions_json or "[]"),
            prep_time_minutes=recipe.prep_time_minutes,
            cook_time_minutes=recipe.cook_time_minutes,
            total_time_minutes=recipe.total_time_minutes,
            servings=recipe.servings,
            has_offer=has_offer,
        )


class AddRecipeUrl(BaseModel):
    url: str


class RatingUpdate(BaseModel):
    rating: str | None = None


class ExclusionCreate(BaseModel):
    term: str


class ExclusionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term: str
    expands_to: list[str] = []


class PantryStapleCreate(BaseModel):
    term: str


class PantryStapleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term: str


class LeftoverCreate(BaseModel):
    term: str


class LeftoverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term: str


class WeekMenuDayOut(BaseModel):
    day_of_week: int
    recipe: RecipeOut | None
    warning: str | None = None


class WeekMenuOut(BaseModel):
    week_start_date: datetime.date
    days: list[WeekMenuDayOut]
    course_counts: dict[str, int] = {}
    warnings: list[str] = []


class GenerateMenuRequest(BaseModel):
    course_counts: dict[str, int] | None = None
    week_start_date: datetime.date | None = None


class ShoppingListItemOut(BaseModel):
    text: str
    extra_id: int | None = None  # set only for manually-added items (removable)


class ShoppingListOut(BaseModel):
    week_start_date: datetime.date
    items: list[ShoppingListItemOut]


class ShoppingListExtraCreate(BaseModel):
    text: str


class FrequentItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term: str
    use_count: int


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store: str
    name: str
    price: float | None
    original_price: float | None
    discount_label: str | None
    valid_until: datetime.date | None


class OfferSyncResult(BaseModel):
    store: str
    offers_found: int


class AppSettingsOut(BaseModel):
    default_hoofdgerecht: int
    default_voorgerecht: int
    default_nagerecht: int


class AppSettingsUpdate(BaseModel):
    default_hoofdgerecht: int
    default_voorgerecht: int
    default_nagerecht: int


class SyncResult(BaseModel):
    source_id: int
    source_name: str
    pages_checked: int
    recipes_found: int
    recipes_updated: int = 0
    error: str | None = None
