"""Confirmation-first repair execution with explicit rollback transactions."""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

from devdoctor import bootstrap
from devdoctor.paths import state_dir
from devdoctor.utils import run_command

_REGISTERED = False


@dataclass(frozen=True, slots=True)
class RepairAction:
    tool_id: str
    tool_title: str
    problem: str
    risk: str
    command: tuple[str, ...]
    verification_command: tuple[str, ...] | None
    rollback_command: tuple[str, ...]


def collect_repair_actions(inventory: bootstrap.BootstrapInventory) -> tuple[RepairAction, ...]:
    """Collect only repair recommendations with both executable and rollback commands."""

    actions: list[RepairAction] = []
    for detection in inventory.detections:
        for recommendation in detection.repair_recommendations:
            if recommendation.command is None or recommendation.rollback_command is None:
                continue
            actions.append(
                RepairAction(
                    tool_id=detection.spec.id,
                    tool_title=detection.spec.title,
                    problem=recommendation.problem,
                    risk=recommendation.risk,
                    command=recommendation.command,
                    verification_command=recommendation.verification_command,
                    rollback_command=recommendation.rollback_command,
                )
            )
    return tuple(actions)


def _transactions_dir() -> Path:
    path = state_dir() / "repair-transactions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _new_transaction_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def _transaction_path(transaction_id: str) -> Path:
    if not transaction_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in transaction_id):
        raise ValueError("invalid transaction id")
    return _transactions_dir() / f"{transaction_id}.json"


def _render_command(command: tuple[str, ...]) -> str:
    return " ".join(command)


def _write_transaction(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _allowed_rollback_command(command: tuple[str, ...]) -> bool:
    """Constrain persisted rollback execution to command forms emitted by DevDoctor."""

    allowed_prefixes = (
        ("sudo", "apt", "remove"),
        ("sudo", "dnf", "remove"),
        ("sudo", "pacman", "-R"),
        ("sudo", "zypper", "remove"),
        ("sudo", "xbps-remove"),
        ("sudo", "apk", "del"),
        ("sudo", "snap", "remove"),
        ("rpm-ostree", "uninstall"),
        ("nix", "profile", "remove"),
        ("brew", "uninstall"),
        ("flatpak", "uninstall"),
        ("pipx", "uninstall"),
        ("npm", "uninstall", "-g"),
        ("pnpm", "remove", "-g"),
        ("yarn", "global", "remove"),
        ("gem", "uninstall"),
        ("composer", "global", "remove"),
        ("rustup", "toolchain", "uninstall"),
        ("mise", "uninstall"),
        ("asdf", "uninstall"),
        ("sudo", "systemctl", "stop", "docker"),
        ("sudo", "gpasswd", "-d"),
    )
    return any(command[: len(prefix)] == prefix for prefix in allowed_prefixes)


def _validate_tool_ids(tool_ids: tuple[str, ...]) -> None:
    if not tool_ids:
        return
    known = {spec.id for spec in bootstrap.get_bootstrap_tools()}
    unknown = sorted(set(tool_ids) - known)
    if unknown:
        raise typer.BadParameter(f"unknown tool id(s): {', '.join(unknown)}")


def register_repair_transaction_commands(app: typer.Typer) -> None:
    """Register conservative repair execution and rollback commands once."""

    global _REGISTERED
    if _REGISTERED:
        return
    _REGISTERED = True

    @app.command("repair-apply")
    def repair_apply(
        tools: list[str] | None = typer.Argument(
            None,
            help="Optional tool IDs. Only repairs with a known rollback command are executable.",
        ),
        apply: bool = typer.Option(False, "--apply", help="Execute after preview and confirmation."),
        yes: bool = typer.Option(False, "--yes", "-y", help="Skip per-action confirmation."),
    ) -> None:
        """Preview or execute rollback-capable repair actions."""

        tool_ids = tuple(tools or ())
        _validate_tool_ids(tool_ids)
        inventory = bootstrap.bootstrap_inventory(include_ids=tool_ids or None)
        actions = collect_repair_actions(inventory)
        if not actions:
            typer.echo("No executable rollback-capable repairs found.")
            return

        typer.echo("Repair preview:")
        for action in actions:
            typer.echo(
                f"- {action.tool_id}: {action.problem}\n"
                f"  run: {_render_command(action.command)}\n"
                f"  rollback: {_render_command(action.rollback_command)}\n"
                f"  risk: {action.risk}"
            )
        if not apply:
            typer.echo("No changes made. Use --apply to execute rollback-capable repairs.")
            return

        transaction_id = _new_transaction_id()
        path = _transaction_path(transaction_id)
        payload: dict[str, Any] = {
            "schema_version": 1,
            "transaction_id": transaction_id,
            "created_at": datetime.now(UTC).isoformat(),
            "actions": [],
        }

        for action in actions:
            rendered = _render_command(action.command)
            if not yes and not typer.confirm(f"Run `{rendered}`?"):
                continue
            started = time.perf_counter()
            completed = subprocess.run(list(action.command), check=False)
            record: dict[str, Any] = {
                "tool_id": action.tool_id,
                "tool_title": action.tool_title,
                "problem": action.problem,
                "risk": action.risk,
                "command": list(action.command),
                "rollback_command": list(action.rollback_command),
                "exit_code": completed.returncode,
                "duration_seconds": round(time.perf_counter() - started, 3),
                "status": "failed" if completed.returncode else "applied",
                "verification_command": (
                    list(action.verification_command) if action.verification_command else None
                ),
                "verification_exit_code": None,
            }
            if completed.returncode == 0 and action.verification_command:
                verification = run_command(action.verification_command, timeout=10)
                record["verification_exit_code"] = verification.returncode
                if verification.returncode != 0:
                    record["status"] = "verification-failed"
            payload["actions"].append(record)
            _write_transaction(path, payload)
            if record["status"] != "applied":
                typer.echo(
                    f"Repair stopped with status {record['status']}. "
                    f"Preview rollback with: devdoctor repair-rollback {transaction_id}"
                )
                raise typer.Exit(code=completed.returncode or 1)

        if payload["actions"]:
            typer.echo(f"Repair transaction: {transaction_id}")
            typer.echo(f"Journal: {path}")
            typer.echo(f"Rollback preview: devdoctor repair-rollback {transaction_id}")
        else:
            typer.echo("No repair actions were approved; no transaction was created.")

    @app.command("repair-rollback")
    def repair_rollback(
        transaction_id: str = typer.Argument(..., help="Transaction ID emitted by repair-apply."),
        apply: bool = typer.Option(False, "--apply", help="Execute rollback after preview."),
        yes: bool = typer.Option(False, "--yes", "-y", help="Skip per-command confirmation."),
    ) -> None:
        """Preview or execute validated rollback commands from a repair transaction."""

        try:
            path = _transaction_path(transaction_id)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if not path.exists():
            raise typer.BadParameter(f"unknown transaction: {transaction_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1 or payload.get("transaction_id") != transaction_id:
            raise typer.BadParameter("invalid or incompatible transaction journal")

        candidates: list[dict[str, Any]] = []
        for record in reversed(payload.get("actions", [])):
            if record.get("status") not in {"applied", "verification-failed"}:
                continue
            command = tuple(str(part) for part in record.get("rollback_command", ()))
            if not command or not _allowed_rollback_command(command):
                typer.echo(f"Blocked unrecognized rollback command for {record.get('tool_id', 'unknown')}.")
                continue
            record["_rollback_tuple"] = command
            candidates.append(record)

        if not candidates:
            typer.echo("No pending validated rollback commands in this transaction.")
            return

        typer.echo("Rollback preview:")
        for record in candidates:
            typer.echo(f"- {_render_command(record['_rollback_tuple'])}")
        if not apply:
            typer.echo("No changes made. Use --apply to execute rollback commands.")
            return

        for record in candidates:
            command = record.pop("_rollback_tuple")
            rendered = _render_command(command)
            if not yes and not typer.confirm(f"Run rollback `{rendered}`?"):
                continue
            completed = subprocess.run(list(command), check=False)
            record["rollback_exit_code"] = completed.returncode
            record["rolled_back_at"] = datetime.now(UTC).isoformat()
            record["status"] = "rolled-back" if completed.returncode == 0 else "rollback-failed"
            _write_transaction(path, payload)
            if completed.returncode != 0:
                raise typer.Exit(code=completed.returncode)
