from legacylift.ingest import parse_migration_notes


def test_parse_migration_notes_extracts_php_version():
    text = "Target PHP 8.2 for this migration."
    constraints = parse_migration_notes(text)
    assert constraints["target_php_version"] == "8.2"


def test_parse_migration_notes_extracts_do_not_touch():
    text = "Please do not touch `/uploads` during the migration.\nAlso keep URLs unchanged."
    constraints = parse_migration_notes(text)
    assert any("uploads" in p for p in constraints["do_not_touch_paths"])
    assert constraints["keep_urls_unchanged"] is True


def test_parse_migration_notes_detects_encoding_note():
    text = "Keep Bangla / UTF-8 content intact throughout."
    constraints = parse_migration_notes(text)
    assert constraints["preserve_encoding"] == "UTF-8"


def test_parse_migration_notes_empty_text_yields_no_constraints():
    assert parse_migration_notes("Nothing relevant here.") == {}


def test_parse_migration_notes_detects_preserve_existing_logins():
    # Exact sentence from examples/MIGRATION_NOTES.md
    text = (
        "Logins must keep working for existing users during the upgrade -- "
        "no forced mass password reset."
    )
    constraints = parse_migration_notes(text)
    assert constraints.get("preserve_existing_logins") is True


def test_parse_migration_notes_unrelated_text_does_not_set_preserve_logins():
    text = "Target PHP 8.2. Keep URLs unchanged. Do not touch /uploads."
    constraints = parse_migration_notes(text)
    assert "preserve_existing_logins" not in constraints
