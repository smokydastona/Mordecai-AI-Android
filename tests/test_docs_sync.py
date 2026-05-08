from scripts.check_docs_sync import validate_docs_sync


def test_docs_sync_requires_changelog_readme_and_docs_for_code_changes():
    errors = validate_docs_sync(["src/mordecai/main.py"])

    assert any("CHANGELOG.md" in error for error in errors)
    assert any("README.md" in error for error in errors)
    assert any("docs/" in error for error in errors)


def test_docs_sync_requires_copilot_instructions_for_process_changes():
    errors = validate_docs_sync([".github/workflows/ci.yml", "CHANGELOG.md", "README.md", "docs/architecture.md"])

    assert any(".github/copilot-instructions.md" in error for error in errors)


def test_docs_sync_passes_when_required_docs_are_present():
    errors = validate_docs_sync(
        [
            "src/mordecai/main.py",
            "CHANGELOG.md",
            "README.md",
            "docs/architecture.md",
        ]
    )

    assert errors == []


def test_docs_sync_treats_android_shell_and_gradle_files_as_implementation():
    errors = validate_docs_sync(["android-shell/src/main/java/ai/mordecai/shell/MainActivity.kt", "settings.gradle.kts"])

    assert any("CHANGELOG.md" in error for error in errors)
    assert any("README.md" in error for error in errors)
    assert any("docs/" in error for error in errors)