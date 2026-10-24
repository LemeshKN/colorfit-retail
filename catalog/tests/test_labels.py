import pytest

from catalog.services import customer_label


def test_best_label():
    assert customer_label("best") == "Best for you"


def test_good_label():
    assert customer_label("good") == "Good option"


@pytest.mark.parametrize("status", ["try_carefully", "usually_avoid", "", "unknown"])
def test_hidden_statuses_have_no_label(status):
    assert customer_label(status) is None