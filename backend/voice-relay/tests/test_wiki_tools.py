import pytest

from app.tools import wiki_tools


def test_slugify_ascii_kebab_case():
    assert wiki_tools.slugify("Home Address") == "home-address"
    assert wiki_tools.slugify("  Multiple   Spaces  ") == "multiple-spaces"


def test_slugify_non_ascii_falls_back_to_untitled():
    assert wiki_tools.slugify("בית") == "untitled"


def test_create_new_page(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki_tools, "wiki_dir", lambda: tmp_path)

    result = wiki_tools.save_memory(
        slug="favorite-color", title="Favorite Color", content="Teal.", tag="private"
    )

    assert result == {"action": "created", "slug": "favorite-color"}
    page = wiki_tools.read_wiki_page("favorite-color")
    assert page["title"] == "Favorite Color"
    assert page["tag"] == "private"
    assert page["content"] == "Teal."
    assert page["created_at"] == page["updated_at"]


def test_merge_into_existing_page_preserves_tag_and_created_at(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki_tools, "wiki_dir", lambda: tmp_path)

    wiki_tools.save_memory(slug="car", title="Car", content="Owns a Kia.", tag="private")
    first = wiki_tools.read_wiki_page("car")

    result = wiki_tools.save_memory(slug="car", title="Car", content="Also owns a BYD.")

    assert result == {"action": "merged", "slug": "car"}
    merged = wiki_tools.read_wiki_page("car")
    assert "Owns a Kia." in merged["content"]
    assert "Also owns a BYD." in merged["content"]
    assert merged["tag"] == "private"  # untouched by merge, per docs/db/memory-module.md
    assert merged["created_at"] == first["created_at"]
    assert merged["updated_at"] >= first["updated_at"]


def test_list_wiki_pages_manifest_has_no_body(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki_tools, "wiki_dir", lambda: tmp_path)
    wiki_tools.save_memory(slug="topic-a", title="Topic A", content="Some detail nobody should see in the manifest.")

    manifest = wiki_tools.list_wiki_pages()

    assert len(manifest) == 1
    assert manifest[0]["slug"] == "topic-a"
    assert "content" not in manifest[0]


def test_read_wiki_page_missing_slug_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki_tools, "wiki_dir", lambda: tmp_path)
    assert wiki_tools.read_wiki_page("does-not-exist") is None


def test_read_wiki_page_extracts_linked_slugs(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki_tools, "wiki_dir", lambda: tmp_path)
    wiki_tools.save_memory(slug="page-a", title="Page A", content="See also [[page-b]] and [[page-c]].")

    page = wiki_tools.read_wiki_page("page-a")

    assert page["linked_slugs"] == ["page-b", "page-c"]


def test_append_reminder_creates_reserved_page(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki_tools, "wiki_dir", lambda: tmp_path)

    result = wiki_tools.append_reminder("every 10th", "pay the storage unit invoice")

    assert result == {"action": "created"}
    page = wiki_tools.read_wiki_page("reminders")
    assert page["title"] == "Reminders"
    assert "- every 10th: pay the storage unit invoice" in page["content"]


def test_append_reminder_accumulates_does_not_replace(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki_tools, "wiki_dir", lambda: tmp_path)

    wiki_tools.append_reminder("every 10th", "pay the storage unit invoice")
    result = wiki_tools.append_reminder("every Monday", "take out the recycling bin")

    assert result == {"action": "appended"}
    page = wiki_tools.read_wiki_page("reminders")
    assert "- every 10th: pay the storage unit invoice" in page["content"]
    assert "- every Monday: take out the recycling bin" in page["content"]


@pytest.mark.parametrize("malicious_slug", [
    "../../../etc/passwd",
    "..\\..\\windows\\system32\\config",
    "foo/bar",
    "foo bar",
    "",
])
def test_save_memory_rejects_unsafe_slugs(tmp_path, monkeypatch, malicious_slug):
    monkeypatch.setattr(wiki_tools, "wiki_dir", lambda: tmp_path)

    with pytest.raises(wiki_tools.UnsafeSlugError):
        wiki_tools.save_memory(slug=malicious_slug, title="x", content="x")

    # nothing should have been written anywhere, in or out of tmp_path
    assert not any(tmp_path.rglob("*.md"))


@pytest.mark.parametrize("malicious_slug", ["../../../etc/passwd", "foo/bar"])
def test_read_wiki_page_rejects_unsafe_slugs(tmp_path, monkeypatch, malicious_slug):
    monkeypatch.setattr(wiki_tools, "wiki_dir", lambda: tmp_path)

    with pytest.raises(wiki_tools.UnsafeSlugError):
        wiki_tools.read_wiki_page(malicious_slug)
