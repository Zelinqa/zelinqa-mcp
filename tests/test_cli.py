"""Argument parsing, startup refusal without a key, and stderr-only logging."""

from __future__ import annotations

import logging
import sys

import pytest
from mcp.server.mcpserver import MCPServer

from nbq_mcp import __version__
from nbq_mcp.cli import EXIT_MISSING_API_KEY, build_parser, configure_logging, main


def test_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.log_level == "WARNING"


def test_explicit_arguments() -> None:
    args = build_parser().parse_args(
        [
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "9001",
            "--log-level",
            "DEBUG",
        ]
    )
    assert args.transport == "streamable-http"
    assert args.host == "0.0.0.0"
    assert args.port == 9001
    assert args.log_level == "DEBUG"


@pytest.mark.parametrize("argv", [["--transport", "sse"], ["--log-level", "TRACE"]])
def test_unsupported_values_are_refused(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        build_parser().parse_args(argv)
    assert raised.value.code == 2


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["--version"])
    assert raised.value.code == 0
    assert capsys.readouterr().out.strip() == f"nbq-mcp {__version__}"


def test_missing_api_key_exits_two_and_writes_to_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("NBQ_API_KEY", raising=False)

    assert main([]) == EXIT_MISSING_API_KEY

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "NBQ_API_KEY is not set" in captured.err
    assert "runtime" in captured.err


def test_blank_api_key_is_treated_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NBQ_API_KEY", "   ")
    assert main([]) == EXIT_MISSING_API_KEY


def test_main_serves_the_requested_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NBQ_API_KEY", "nbq_live_fake_unit_test_key")
    served: list[tuple[str, str, int, str]] = []

    def fake_run(server: MCPServer[None], transport: str, *, host: str, port: int) -> None:
        # host and port are transport options in the MCP SDK, not server settings.
        served.append((transport, host, port, server.settings.log_level))

    monkeypatch.setattr("nbq_mcp.cli.run_server", fake_run)

    exit_code = main(
        [
            "--transport",
            "streamable-http",
            "--host",
            "127.0.0.1",
            "--port",
            "9100",
            "--log-level",
            "ERROR",
        ]
    )

    assert exit_code == 0
    assert served == [("streamable-http", "127.0.0.1", 9100, "ERROR")]


def test_logging_is_configured_on_stderr_only() -> None:
    configure_logging("INFO")
    handlers = logging.getLogger().handlers
    assert handlers
    for handler in handlers:
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr
