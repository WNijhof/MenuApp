import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(500))
    sitemap_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_pages: Mapped[int] = mapped_column(Integer, default=300)
    last_synced_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_sync_found: Mapped[int] = mapped_column(Integer, default=0)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    recipes: Mapped[list["Recipe"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (UniqueConstraint("url", name="uq_recipe_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )
    url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    dish_type: Mapped[str] = mapped_column(String(50), default="overig")
    course: Mapped[str] = mapped_column(String(20), default="hoofdgerecht")
    rating: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    cuisine: Mapped[str | None] = mapped_column(String(100), nullable=True)
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingredients_json: Mapped[str] = mapped_column(Text, default="[]")
    instructions_json: Mapped[str] = mapped_column(Text, default="[]")
    # True for recipes typed in by hand (routers/recipes.py's /manual
    # endpoints) rather than scraped from a source or added by URL - these
    # have no real page behind their `url` (see add_manual_recipe), so the
    # frontend uses this flag to show/edit them in-app instead of linking out.
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    # 'nl' or 'en' - the language the recipe's own text is written in (from
    # the site's schema.org `inLanguage` when present, otherwise guessed;
    # see services/language_detect.py). Used to translate ingredient lines
    # to the UI language on the shopping list regardless of recipe language.
    language: Mapped[str | None] = mapped_column(String(5), nullable=True)
    prep_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cook_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    servings: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scraped_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    source: Mapped["Source"] = relationship(back_populates="recipes")


class ExclusionRule(Base):
    __tablename__ = "exclusion_rules"
    __table_args__ = (UniqueConstraint("term", name="uq_exclusion_term"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class PantryStaple(Base):
    __tablename__ = "pantry_staples"
    __table_args__ = (UniqueConstraint("term", name="uq_pantry_staple_term"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class Leftover(Base):
    __tablename__ = "leftovers"
    __table_args__ = (UniqueConstraint("term", name="uq_leftover_term"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class ShoppingListExtra(Base):
    """A manually-added item for the current week's shopping list -
    cleared alongside Leftover on each new generation, same reasoning:
    it's a this-week-only addition, not a standing preference."""

    __tablename__ = "shopping_list_extras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class FrequentItem(Base):
    """A previously-typed shopping list item, remembered as a quick-add
    favorite. Bundle-variant selection piggybacks on this: "Eieren
    6-pack" and "Eieren los" are simply two different remembered strings
    the user builds up through normal use, not a separate structured
    catalog."""

    __tablename__ = "frequent_items"
    __table_args__ = (UniqueConstraint("term", name="uq_frequent_item_term"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(300))
    use_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class TranslationCache(Base):
    """Caches ingredient-line translations (see services/translator.py) so
    the same line is only ever sent to the translation API once, keyed on
    the exact text plus language pair rather than just the text - the same
    Dutch line should never need re-translating once it's in the cache for
    a given target language."""

    __tablename__ = "translation_cache"
    __table_args__ = (
        UniqueConstraint(
            "source_text", "source_lang", "target_lang", name="uq_translation_cache"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_text: Mapped[str] = mapped_column(Text)
    source_lang: Mapped[str] = mapped_column(String(5))
    target_lang: Mapped[str] = mapped_column(String(5))
    translated_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class AppSettings(Base):
    """Singleton settings row (always id=1) - default course counts used
    when generating a week without an explicit override."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    default_hoofdgerecht: Mapped[int] = mapped_column(Integer, default=5)
    default_voorgerecht: Mapped[int] = mapped_column(Integer, default=0)
    default_nagerecht: Mapped[int] = mapped_column(Integer, default=0)
    background_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="en")


class WeekMenu(Base):
    __tablename__ = "week_menus"
    __table_args__ = (UniqueConstraint("week_start_date", name="uq_week_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start_date: Mapped[datetime.date] = mapped_column(Date)
    course_counts_json: Mapped[str] = mapped_column(Text, default="{}")
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    days: Mapped[list["WeekMenuDay"]] = relationship(
        back_populates="week_menu",
        cascade="all, delete-orphan",
        order_by="WeekMenuDay.day_of_week",
    )


class WeekMenuDay(Base):
    __tablename__ = "week_menu_days"
    __table_args__ = (
        UniqueConstraint("week_menu_id", "day_of_week", name="uq_week_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_menu_id: Mapped[int] = mapped_column(ForeignKey("week_menus.id"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=maandag .. 6=zondag
    recipe_id: Mapped[int | None] = mapped_column(
        ForeignKey("recipes.id"), nullable=True
    )
    # Per-day flags, all reset whenever the day's recipe changes:
    # pinned - survives regenerating the week / changing the dish counts;
    # cooked - ticked off once made (shown greyed out; also survives a
    #          regenerate, since a dish already cooked shouldn't vanish);
    # skip_shopping - this dish's ingredients are left off the shopping list
    #          (eating out, everything already at home, ...).
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    cooked: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_shopping: Mapped[bool] = mapped_column(Boolean, default=False)

    week_menu: Mapped["WeekMenu"] = relationship(back_populates="days")
    recipe: Mapped["Recipe | None"] = relationship()
