import pytest

from app.tools import document_tools


def test_save_document_infers_title_from_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)

    result = document_tools.save_document("passport_scan.pdf", b"%PDF-fake-bytes")

    assert result == {
        "slug": "passport-scan",
        "title": "passport scan",
        "original_filename": "passport_scan.pdf",
        "file_extension": "pdf",
        "path": tmp_path / "passport-scan.pdf",
    }
    assert (tmp_path / "passport-scan.pdf").read_bytes() == b"%PDF-fake-bytes"
    sidecar = (tmp_path / "passport-scan.md").read_text()
    assert "slug: passport-scan" in sidecar
    assert "original_filename: passport_scan.pdf" in sidecar
    assert "file_extension: pdf" in sidecar


def test_save_document_uses_caption_as_title_when_given(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)

    result = document_tools.save_document("IMG_2024.jpg", b"fake-bytes", title="My Passport Scan")

    assert result["title"] == "My Passport Scan"
    assert result["slug"] == "my-passport-scan"
    assert (tmp_path / "my-passport-scan.jpg").exists()


def test_save_document_disambiguates_slug_collision(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)

    first = document_tools.save_document("scan1.pdf", b"one", title="Passport")
    second = document_tools.save_document("scan2.pdf", b"two", title="Passport")

    assert first["slug"] == "passport"
    assert second["slug"] == "passport-2"
    assert (tmp_path / "passport.pdf").read_bytes() == b"one"
    assert (tmp_path / "passport-2.pdf").read_bytes() == b"two"


def test_save_document_is_findable_afterward(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)

    document_tools.save_document("lease.pdf", b"lease-bytes", title="Apartment Lease")

    found = document_tools.find_document("lease")
    assert len(found) == 1
    assert found[0]["slug"] == "apartment-lease"


def test_categorize_document_renames_slug_and_adds_category(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)
    saved = document_tools.save_document("IMG_2024.jpg", b"photo-bytes")  # placeholder title: "img 2024"

    result = document_tools.categorize_document(
        saved["slug"], title="Habima Theater Tickets", category="ticket"
    )

    assert result == {"slug": "habima-theater-tickets", "title": "Habima Theater Tickets", "category": "ticket"}
    # old files gone, new ones present, bytes preserved across the rename
    assert not (tmp_path / f"{saved['slug']}.md").exists()
    assert not (tmp_path / f"{saved['slug']}.jpg").exists()
    assert (tmp_path / "habima-theater-tickets.jpg").read_bytes() == b"photo-bytes"
    sidecar = (tmp_path / "habima-theater-tickets.md").read_text()
    assert "title: Habima Theater Tickets" in sidecar
    assert "category: ticket" in sidecar
    assert "original_filename: IMG_2024.jpg" in sidecar  # preserved from the original save


def test_categorize_document_without_category_omits_the_field(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)
    saved = document_tools.save_document("note.txt", b"hello")

    document_tools.categorize_document(saved["slug"], title="A Random Note")

    sidecar = (tmp_path / "a-random-note.md").read_text()
    assert "category:" not in sidecar


def test_categorize_document_updates_in_place_when_title_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)
    saved = document_tools.save_document("scan.pdf", b"bytes", title="Passport")

    result = document_tools.categorize_document(saved["slug"], title="Passport", category="ID")

    assert result["slug"] == "passport"
    assert (tmp_path / "passport.pdf").read_bytes() == b"bytes"


def test_categorize_document_disambiguates_collision_with_different_document(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)
    document_tools.save_document("a.pdf", b"one", title="Receipt")
    other = document_tools.save_document("b.pdf", b"two", title="Something Else")

    result = document_tools.categorize_document(other["slug"], title="Receipt", category="receipt")

    assert result["slug"] == "receipt-2"
    assert (tmp_path / "receipt.pdf").read_bytes() == b"one"  # untouched
    assert (tmp_path / "receipt-2.pdf").read_bytes() == b"two"


def test_categorize_document_returns_error_for_unknown_slug(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)

    result = document_tools.categorize_document("does-not-exist", title="Whatever")

    assert "error" in result


def test_categorize_document_is_findable_by_new_category(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)
    saved = document_tools.save_document("photo.jpg", b"bytes")

    document_tools.categorize_document(saved["slug"], title="Concert Poster", category="poster")

    found = document_tools.find_document("poster")
    assert len(found) == 1
    assert found[0]["slug"] == "concert-poster"


@pytest.mark.parametrize("malicious_filename", [
    "evil.pdf/../../../etc/cron.d/evil",
    "evil.txt/../../root/.ssh/authorized_keys",
    "evil./etc/passwd",
])
def test_save_document_rejects_unsafe_extension(tmp_path, monkeypatch, malicious_filename):
    # ext is attacker/user-controlled (the sender's own filename) and ends
    # up directly in a filesystem path — must never let it carry a "/" or
    # ".." out of the docs directory.
    monkeypatch.setattr(document_tools, "docs_dir", lambda: tmp_path)

    result = document_tools.save_document(malicious_filename, b"payload", title="Innocuous Title")

    assert "/" not in result["slug"]
    written_files = {p.name for p in tmp_path.iterdir()}
    assert all("/" not in name and ".." not in name for name in written_files)
    # Confirm nothing escaped tmp_path — every written file is a direct child of it.
    for path in tmp_path.rglob("*"):
        assert path.parent == tmp_path
