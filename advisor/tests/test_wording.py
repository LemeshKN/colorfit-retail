import re

from django.conf import settings

BANNED = re.compile(r"\b(fair|dark|wheatish)\b", re.IGNORECASE)


def _template_files():
    root = settings.BASE_DIR
    skip = {"env", "node_modules", ".git"}
    for path in root.rglob("*.html"):
        if skip.isdisjoint(path.relative_to(root).parts):
            yield path


def test_templates_use_no_banned_tone_words():
    found = []
    for path in _template_files():
        text = path.read_text(encoding="utf-8")
        for match in BANNED.finditer(text):
            found.append(f"{path.name}: {match.group(0)}")
    assert found == []