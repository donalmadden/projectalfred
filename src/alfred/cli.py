"""Command-line entrypoint for Alfred."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from importlib import metadata
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

import uvicorn

from alfred.api import EvaluateRequest, GenerateRequest, evaluate, generate
from alfred.schemas.agent import ExecutorOutput


class CLIError(RuntimeError):
    """Raised for handled CLI errors that should exit 1."""


def _candidate_repo_roots() -> list[Path]:
    roots: list[Path] = []
    for base in (Path.cwd(), Path(__file__).resolve().parents[2]):
        for candidate in (base, *base.parents):
            if candidate not in roots:
                roots.append(candidate)
    return roots


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _read_optional_text(value: Optional[str], path: Optional[str], *, label: str) -> Optional[str]:
    if value is not None:
        return value
    if path is None:
        return None
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CLIError(f"Unable to read {label} from {path!r}: {exc}") from exc


def _load_validator_module() -> ModuleType:
    script_path: Optional[Path] = None
    for root in _candidate_repo_roots():
        candidate = root / "scripts" / "validate_alfred_planning_facts.py"
        if candidate.is_file():
            script_path = candidate
            break
    if script_path is None:
        raise CLIError(
            "Validator script not found under the current working tree. "
            "Run this command from a repository checkout."
        )

    spec = spec_from_file_location("alfred_validate_planning_facts", script_path)
    if spec is None or spec.loader is None:
        raise CLIError(f"Unable to load validator script from {script_path}.")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alfred", description="Alfred command-line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser(
        "plan",
        help="Generate a draft handover plan",
        description="Invoke Alfred's planner pipeline or print a dry-run execution plan.",
    )
    plan_parser.add_argument("--sprint-goal", default=None, help="Optional sprint goal prompt.")
    plan_parser.add_argument(
        "--prior-handover-id",
        default=None,
        help="Optional prior handover identifier for contextual labelling.",
    )
    plan_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan request and execution steps without invoking the planner.",
    )

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate checkpoint evidence",
        description="Invoke Alfred's quality-judge pipeline or print a dry-run evaluation plan.",
    )
    evaluate_parser.add_argument(
        "--handover-text",
        default=None,
        help="Inline handover markdown to evaluate.",
    )
    evaluate_parser.add_argument(
        "--handover-path",
        default=None,
        help="Path to a handover markdown file to evaluate.",
    )
    evaluate_parser.add_argument(
        "--checkpoint-definition",
        default=None,
        help="Inline JSON checkpoint definition.",
    )
    evaluate_parser.add_argument(
        "--checkpoint-definition-path",
        default=None,
        help="Path to a JSON checkpoint definition file.",
    )
    evaluate_parser.add_argument(
        "--executor-output-json",
        default=None,
        help="Inline JSON executor output payload.",
    )
    evaluate_parser.add_argument(
        "--executor-output-path",
        default=None,
        help="Path to a JSON file containing executor output payload.",
    )
    evaluate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the evaluation request and planned checks without invoking the judge.",
    )

    serve_parser = subparsers.add_parser(
        "serve",
        help="Start Alfred's API server",
        description="Run the FastAPI service through uvicorn.",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host. Default: 127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port. Default: 8000")
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for local development.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Run the planning factual validator",
        description="Validate a handover draft against Alfred's factual planning rules.",
    )
    validate_parser.add_argument("path", help="Path to the handover markdown file to validate.")
    validate_parser.add_argument("--expected-id", default=None, help="Expected handover id.")
    validate_parser.add_argument(
        "--expected-previous",
        default=None,
        help="Expected previous handover id.",
    )
    validate_parser.add_argument("--expected-date", default=None, help="Expected ISO date.")

    subparsers.add_parser(
        "version",
        help="Print Alfred's installed package version",
        description="Print Alfred's version from importlib.metadata.",
    )

    return parser


def _plan_command(args: argparse.Namespace) -> int:
    if args.dry_run:
        _emit_json(
            {
                "command": "plan",
                "dry_run": True,
                "request": {
                    "sprint_goal": args.sprint_goal,
                    "prior_handover_id": args.prior_handover_id,
                },
                "steps": [
                    "load Alfred config",
                    "collect board, velocity, repo facts, and handover context",
                    "invoke planner and critique loop",
                    "print draft handover payload",
                ],
            }
        )
        return 0

    response = asyncio.run(
        generate(
            GenerateRequest(
                sprint_goal=args.sprint_goal,
                prior_handover_id=args.prior_handover_id,
            )
        )
    )
    _emit_json(response.model_dump(mode="json"))
    return 0


def _evaluate_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    handover_text = _read_optional_text(args.handover_text, args.handover_path, label="handover text")
    checkpoint_definition = _read_optional_text(
        args.checkpoint_definition,
        args.checkpoint_definition_path,
        label="checkpoint definition",
    )
    executor_output_json = _read_optional_text(
        args.executor_output_json,
        args.executor_output_path,
        label="executor output JSON",
    )

    if args.dry_run:
        _emit_json(
            {
                "command": "evaluate",
                "dry_run": True,
                "request": {
                    "handover_document_markdown": handover_text,
                    "checkpoint_definition": checkpoint_definition,
                    "executor_output_json": executor_output_json,
                },
                "steps": [
                    "load Alfred config",
                    "prepare checkpoint evaluation request",
                    "invoke quality judge",
                    "print checkpoint verdict payload",
                ],
            }
        )
        return 0

    if handover_text is None:
        parser.error("evaluate requires --handover-text or --handover-path unless --dry-run is set")
    if checkpoint_definition is None:
        parser.error(
            "evaluate requires --checkpoint-definition or --checkpoint-definition-path unless --dry-run is set"
        )

    executor_output: Optional[ExecutorOutput] = None
    if executor_output_json is not None:
        try:
            executor_output = ExecutorOutput.model_validate(json.loads(executor_output_json))
        except json.JSONDecodeError as exc:
            raise CLIError(f"Executor output is not valid JSON: {exc}") from exc
        except Exception as exc:
            raise CLIError(f"Executor output does not match the expected schema: {exc}") from exc

    response = asyncio.run(
        evaluate(
            EvaluateRequest(
                handover_document_markdown=handover_text,
                checkpoint_definition=checkpoint_definition,
                executor_output=executor_output,
            )
        )
    )
    _emit_json(response.model_dump(mode="json"))
    return 0


def _serve_command(args: argparse.Namespace) -> int:
    uvicorn.run(
        "alfred.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def _validate_command(args: argparse.Namespace) -> int:
    module = _load_validator_module()
    argv = [args.path]
    if args.expected_id:
        argv.extend(["--expected-id", args.expected_id])
    if args.expected_previous:
        argv.extend(["--expected-previous", args.expected_previous])
    if args.expected_date:
        argv.extend(["--expected-date", args.expected_date])
    return int(module.main(argv))


def _version_command() -> int:
    try:
        print(metadata.version("alfred"))
    except metadata.PackageNotFoundError as exc:
        raise CLIError("Installed package metadata for 'alfred' was not found.") from exc
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "plan":
            return _plan_command(args)
        if args.command == "evaluate":
            return _evaluate_command(args, parser)
        if args.command == "serve":
            return _serve_command(args)
        if args.command == "validate":
            return _validate_command(args)
        if args.command == "version":
            return _version_command()
    except CLIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
