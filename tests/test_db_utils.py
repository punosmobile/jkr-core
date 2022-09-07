import pytest

from jkrimporter.providers.db.utils import is_asoy, is_company


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Matti Henrikson", False),
        ("As Oy Kehrääjä", True),
        ("Testi As Oy", True),
        ("Testi Asunto oy", True),
        ("Sisältääasoysanan", False),
        ("Foo bost. ab.", True),
        ("Foo bost. abc", False),
        ("KAS KODIT OY RAUHANTIE 27", False),
    ],
)
def test_is_asoy(name, expected):
    assert is_asoy(name) is expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Matti Henrikson", False),
        ("As Oy Kehrääjä", True),
        ("Sisältääasoysanan", False),
        ("company ab.", True),
        ("company ab", True),
        ("company abc", False),
        ("company oy", True),
        ("KAS KODIT OY RAUHANTIE 27", True),
    ],
)
def test_is_company(name, expected):
    assert is_company(name) is expected
