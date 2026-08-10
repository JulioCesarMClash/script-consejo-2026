from datetime import date
from pathlib import Path

from src.consejo.config.settings import Settings


def test_settings_loads_dotenv_values_with_comments_and_quotes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# Database settings\n"
        "DB_HOST=db.example\n"
        "DB_PORT=5433\n"
        'GOOGLE_APPLICATION_CREDENTIALS="/path/with spaces/credentials.json"\n'
        "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "src.consejo.config.settings.ENV_FILE",
        env_file,
    )

    settings = Settings()

    assert settings.db_host == "db.example"
    assert settings.db_port == 5433
    assert settings.google_application_credentials == (
        "/path/with spaces/credentials.json"
    )


def test_explicit_environment_values_take_precedence_over_dotenv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DB_HOST=from-file\nDB_PORT=5433\n", encoding="utf-8")
    monkeypatch.setattr("src.consejo.config.settings.ENV_FILE", env_file)
    monkeypatch.setenv("DB_HOST", "from-environment")

    settings = Settings()

    assert settings.db_host == "from-environment"
    assert settings.db_port == 5433


def test_missing_dotenv_is_allowed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "src.consejo.config.settings.ENV_FILE",
        tmp_path / ".env",
    )

    settings = Settings()

    assert settings.db_host == ""


def test_settings_loads_certificate_period(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CERTIFICATE_PERIOD_START=2025-09-01\n"
        "CERTIFICATE_PERIOD_END=2026-08-01\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("src.consejo.config.settings.ENV_FILE", env_file)

    settings = Settings()

    assert settings.certificate_period_start == date(2025, 9, 1)
    assert settings.certificate_period_end == date(2026, 8, 1)
