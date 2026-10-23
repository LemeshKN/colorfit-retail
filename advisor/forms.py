from django import forms
from django.utils.translation import gettext_lazy as _


class CardEntryForm(forms.Form):
    card_id = forms.CharField(
        max_length=20,
        label=_("Card ID"),
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered input-lg w-full",
                "placeholder": "ST-07",
                "autocomplete": "off",
                "autocapitalize": "characters",
            }
        ),
    )