"""Place names for search (GeoNames cities5000, CC BY 4.0).

Loaded by scripts/import_places.py. Each place keeps one display row; every
name it is known by (local, English, transliterations, other languages)
goes to place_names, lower-cased, so a prefix search finds "Seoul", "seo"
and "서울" alike.
"""

from sqlalchemy import BigInteger, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class Place(Base):
    __tablename__ = "places"

    # GeoNames id: stable across releases, so re-imports replace rows in place
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    admin1: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    population: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class PlaceName(Base):
    __tablename__ = "place_names"

    place_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("places.id", ondelete="CASCADE"), primary_key=True
    )
    # Lower-cased (casefold) so LIKE 'q%' is case-insensitive without lower() per row
    name: Mapped[str] = mapped_column(String(200), primary_key=True)

    __table_args__ = (
        # text_pattern_ops: prefix LIKE uses the index whatever the database collation
        Index("idx_place_names_prefix", "name", postgresql_ops={"name": "text_pattern_ops"}),
    )
