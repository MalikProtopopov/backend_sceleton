"""Reusable mixins for locale (translation) tables.

Provides ``LocaleBaseMixin`` with the common columns shared by all
``*Locale`` models (locale code, slug, title, SEO meta).  New locale
tables can inherit from this mixin to avoid duplicating column
definitions.  Existing locale tables can be migrated gradually.

Example usage::

    class ProductLocale(Base, UUIDMixin, TimestampMixin, LocaleBaseMixin):
        __tablename__ = "product_locales"

        product_id: Mapped[UUID] = mapped_column(
            PGUUID(as_uuid=True),
            ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        )
        # ... any extra columns specific to this locale ...

        product: Mapped["Product"] = relationship("Product", back_populates="locales")

        __table_args__ = (
            UniqueConstraint("product_id", "locale", name="uq_product_locales"),
        )
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class LocaleBaseMixin:
    """Common columns shared by all ``*Locale`` translation tables.

    Provides:
    - ``locale`` — BCP-47 language code (e.g. ``ru``, ``en``)
    - ``title`` — required title in that locale
    - ``slug`` — URL-safe identifier (unique per entity+locale)
    - SEO fields: ``meta_title``, ``meta_description``, ``meta_keywords``

    The ``slug`` and SEO columns intentionally duplicate the existing
    ``SlugMixin`` / ``SEOMixin`` from ``base_model.py`` so that adopters
    of this mixin don't need to multiply-inherit both.  When migrating
    an existing table, just swap the inheritance list; no DB migration
    is required because column names and types match exactly.
    """

    locale: Mapped[str] = mapped_column(String(5), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_keywords: Mapped[str | None] = mapped_column(String(500), nullable=True)
