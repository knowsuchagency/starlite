from typing import TYPE_CHECKING

from starlite import Starlite
from starlite.cli.commands.sessions import get_session_backend
from starlite.cli.main import starlite_group as cli_command
from starlite.middleware import RateLimitConfig
from starlite.middleware.session.server_side import ServerSideSessionConfig

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from _pytest.monkeypatch import MonkeyPatch
    from click.testing import CliRunner
    from pytest_mock import MockerFixture

    from starlite.storage.memory_backend import MemoryStorageBackend


def test_get_session_backend(memory_storage_backend: "MemoryStorageBackend") -> None:
    session_middleware = ServerSideSessionConfig(storage=memory_storage_backend).middleware
    app = Starlite(
        [],
        middleware=[
            RateLimitConfig(rate_limit=("second", 1)).middleware,
            session_middleware,
        ],
    )

    assert get_session_backend(app) is session_middleware.kwargs["backend"]


def test_delete_session_no_backend(runner: "CliRunner", monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setenv("STARLITE_APP", "docs.examples.hello_world:app")
    result = runner.invoke(cli_command, "sessions delete foo")

    assert result.exit_code == 1
    assert "Session middleware not installed" in result.output


def test_delete_session_cookie_backend(runner: "CliRunner", monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setenv("STARLITE_APP", "docs.examples.middleware.session.cookie_backend:app")

    result = runner.invoke(cli_command, "sessions delete foo")

    assert result.exit_code == 1
    assert "Only server-side backends are supported" in result.output


def test_delete_session(
    runner: "CliRunner", monkeypatch: "MonkeyPatch", mocker: "MockerFixture", mock_confirm_ask: "MagicMock"
) -> None:
    monkeypatch.setenv("STARLITE_APP", "docs.examples.middleware.session.memory_backend:app")
    mock_delete = mocker.patch("starlite.storage.memory_backend.MemoryStorageBackend.delete")

    result = runner.invoke(cli_command, ["sessions", "delete", "foo"])

    assert mock_confirm_ask.called_once_with("[red]Delete session 'foo'?")
    assert not result.exception
    mock_delete.assert_called_once_with("foo")


def test_clear_sessions_no_backend(runner: "CliRunner", monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setenv("STARLITE_APP", "docs.examples.hello_world:app")
    result = runner.invoke(cli_command, "sessions clear")

    assert result.exit_code == 1
    assert "Session middleware not installed" in result.output


def test_clear_sessions_cookie_backend(runner: "CliRunner", monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setenv("STARLITE_APP", "docs.examples.middleware.session.cookie_backend:app")

    result = runner.invoke(cli_command, "sessions clear")

    assert result.exit_code == 1
    assert "Only server-side backends are supported" in result.output


def test_clear_sessions(
    runner: "CliRunner", monkeypatch: "MonkeyPatch", mocker: "MockerFixture", mock_confirm_ask: "MagicMock"
) -> None:
    monkeypatch.setenv("STARLITE_APP", "docs.examples.middleware.session.memory_backend:app")
    mock_delete = mocker.patch("starlite.storage.memory_backend.MemoryStorageBackend.delete_all")

    result = runner.invoke(cli_command, ["sessions", "clear"])

    assert mock_confirm_ask.called_once_with("[red]Delete all sessions?")
    assert not result.exception
    mock_delete.assert_called_once()
