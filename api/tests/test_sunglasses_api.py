import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from shops.models import AdviceSession, Shop
from sunglasses.models import FaceShapeRule, FrameStyle

URL = "/api/v1/sunglasses/classify/"
GOOD = {
    "face_length": 145,
    "forehead_width": 85,
    "cheekbone_width": 100,
    "jaw_width": 75,
}


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def on(settings):
    settings.SUNGLASSES_ENABLED = True


@pytest.fixture
def shop(db):
    return Shop.objects.create(name="Test Shop", code="T-1", slug="t-1", city="Test City")


def make_shape(name, length, forehead, jaw, order=1):
    return FaceShapeRule.objects.create(
        name=name,
        slug=name.lower(),
        sort_order=order,
        length_ratio=length,
        forehead_ratio=forehead,
        jaw_ratio=jaw,
    )


def make_frames(shape):
    for rank in (1, 2, 3):
        FrameStyle.objects.create(
            shape=shape,
            name=f"{shape.name} frame {rank}",
            slug=f"{shape.slug}-{rank}",
            image_file=f"img/frames/{shape.slug}-{rank}.svg",
            note="Test note",
            rank=rank,
        )


@pytest.fixture
def shapes(db):
    oval = make_shape("Oval", 1.45, 0.85, 0.75, order=1)
    make_shape("Square", 1.20, 0.90, 0.90, order=2)
    make_frames(oval)
    return oval


def test_valid_numbers_return_shape_and_three_frames(api, on, shapes):
    response = api.post(URL, GOOD, format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["shape"] == {"name": "Oval", "slug": "oval"}
    assert data["alternative"] is None
    assert [f["rank"] for f in data["frames"]] == [1, 2, 3]


def test_close_second_shape_is_returned_as_alternative(api, on, db):
    oval = make_shape("Oval", 1.40, 0.85, 0.75, order=1)
    make_shape("Square", 1.40, 0.87, 0.75, order=2)
    make_frames(oval)
    numbers = {**GOOD, "face_length": 140}
    data = api.post(URL, numbers, format="json").json()
    assert data["shape"]["slug"] == "oval"
    assert data["alternative"] == {"name": "Square", "slug": "square"}


@pytest.mark.parametrize(
    "payload",
    [
        {**GOOD, "face_length": 0},
        {**GOOD, "face_length": -5},
        {**GOOD, "face_length": 500},  # ratio 5.0 is too long for a face
        {**GOOD, "forehead_width": 5},  # ratio 0.05 is too narrow
        {**GOOD, "jaw_width": "abc"},
        {"face_length": 145, "forehead_width": 85, "cheekbone_width": 100},
        {},
    ],
)
def test_bad_numbers_return_400(api, on, shapes, payload):
    assert api.post(URL, payload, format="json").status_code == 400


def test_extra_fields_are_refused(api, on, shapes):
    response = api.post(URL, {**GOOD, "photo": "data:image/png;base64,AAAA"}, format="json")
    assert response.status_code == 400


def test_no_shape_rules_returns_503(api, on, db):
    assert api.post(URL, GOOD, format="json").status_code == 503


def test_endpoint_is_404_when_switch_is_off(api, shapes, settings):
    settings.SUNGLASSES_ENABLED = False
    assert api.post(URL, GOOD, format="json").status_code == 404


def test_get_is_not_allowed(api, on, shapes):
    assert api.get(URL).status_code == 405


def test_nothing_is_written(api, on, shapes):
    with CaptureQueriesContext(connection) as queries:
        response = api.post(URL, GOOD, format="json")
    assert response.status_code == 200
    writes = ("INSERT", "UPDATE", "DELETE")
    assert not any(q["sql"].lstrip().upper().startswith(writes) for q in queries.captured_queries)
    assert AdviceSession.objects.count() == 0


def test_classify_is_rate_limited(api, on, shapes):
    for _ in range(20):
        assert api.post(URL, GOOD, format="json").status_code == 200
    assert api.post(URL, GOOD, format="json").status_code == 429


def test_api_frames_match_the_result_page(api, client, shop, on, shapes):
    data = api.post(URL, GOOD, format="json").json()
    page = client.get(
        reverse("sunglasses:shape_detail", args=[shop.slug, data["shape"]["slug"]])
    )
    page_names = [frame.name for frame in page.context["frames"]]
    assert [f["name"] for f in data["frames"]] == page_names