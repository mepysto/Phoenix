"""GeoNames place parsing (no network, no database), on real sample rows."""

from pathlib import Path

from scripts.import_places import parse_admin1, parse_cities, parse_countries, search_names

FIXTURES = Path(__file__).parent.parent / "fixtures" / "geonames"


def _lines(name: str) -> list[str]:
    return (FIXTURES / name).read_text(encoding="utf-8").splitlines()


def test_admin1_and_country_names_are_looked_up_by_code() -> None:
    admin1 = parse_admin1(_lines("admin1CodesASCII.txt"))
    countries = parse_countries(_lines("countryInfo.txt"))
    assert admin1["KR.11"] == "Seoul"
    assert admin1["ES.60"] == "Valencia"
    assert countries["MZ"] == "Mozambique"
    assert "#" not in "".join(countries)  # comment lines are skipped


def test_cities_carry_display_context_and_every_name() -> None:
    places = {
        p["id"]: (p, names)
        for p, names in parse_cities(
            _lines("cities5000.txt"),
            parse_admin1(_lines("admin1CodesASCII.txt")),
            parse_countries(_lines("countryInfo.txt")),
        )
    }
    seoul, names = places[1835848]
    assert seoul["name"] == "Seoul"
    assert seoul["country"] == "South Korea"
    assert seoul["country_code"] == "KR"
    assert seoul["population"] > 9_000_000
    assert round(seoul["latitude"]) == 38 and round(seoul["longitude"]) == 127
    # Search finds it by English, local and transliterated names, case-insensitively
    assert {"seoul", "서울", "séoul"} <= names
    # Codes such as airport "SEL" are not names people type
    assert "sel" not in names
    # Same name as the region: no "Valencia, Valencia"
    valencia, _ = places[2509954]
    assert valencia["admin1"] is None


def test_search_names_cleans_and_caps() -> None:
    names = search_names("São Paulo", "Sao Paulo", ["SAO", "https://example.org", " Sampa ", "", "x" * 300])
    assert names == {"são paulo", "sao paulo", "sampa"}
    many = search_names("A", "A", [f"name{i}" for i in range(500)])
    assert len(many) == 300
