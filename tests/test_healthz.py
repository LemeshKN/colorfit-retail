import pytest


@pytest.mark.django_db
def test_healthz_returns_ok_without_queries(client, django_assert_num_queries):
    with django_assert_num_queries(0):
        response = client.get("/healthz/")
    assert response.status_code == 200
    assert response.content == b"ok"


def test_healthz_rejects_post(client):
    response = client.post("/healthz/")
    assert response.status_code == 405