import pytest
from django.core.management import call_command
from django.urls import reverse

from sunglasses.models import FaceShapeRule


@pytest.mark.django_db
def test_seed_creates_six_shapes():
    call_command("seed_face_shapes")
    assert FaceShapeRule.objects.count() == 6


@pytest.mark.django_db
def test_seed_twice_creates_no_duplicates():
    call_command("seed_face_shapes")
    call_command("seed_face_shapes")
    assert FaceShapeRule.objects.count() == 6


@pytest.mark.django_db
def test_seed_does_not_overwrite_tuned_values():
    call_command("seed_face_shapes")
    FaceShapeRule.objects.filter(slug="oval").update(length_ratio=1.99)
    call_command("seed_face_shapes")
    assert FaceShapeRule.objects.get(slug="oval").length_ratio == pytest.approx(1.99)


@pytest.mark.django_db
def test_admin_health_action_reports_missing_frames(admin_client):
    call_command("seed_face_shapes")
    shape = FaceShapeRule.objects.get(slug="oval")
    response = admin_client.post(
        reverse("admin:sunglasses_faceshaperule_changelist"),
        {"action": "run_health_check", "_selected_action": [shape.pk]},
        follow=True,
    )
    assert "has 0 of 3 frame styles" in response.content.decode()