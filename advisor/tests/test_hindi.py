import pytest
from django.utils import translation

from catalog.services import customer_label


def test_hindi_text_is_loaded():
    with translation.override("hi"):
        assert translation.gettext("Continue") == "आगे बढ़ें"


def test_customer_labels_switch_to_hindi():
    with translation.override("hi"):
        assert customer_label("best") == "आपके लिए सबसे अच्छा"
        assert customer_label("good") == "अच्छा विकल्प"
    assert customer_label("best") == "Best for you"

@pytest.mark.parametrize(
    "text",
    [
        "Take a photo",
        "Choose a photo",
        "Your photo was not saved.",
        "Try another photo",
        "We could not find a face in this photo.",
    ],
)
def test_new_text_is_translated(text):
    with translation.override("hi"):
        assert translation.gettext(text) != text