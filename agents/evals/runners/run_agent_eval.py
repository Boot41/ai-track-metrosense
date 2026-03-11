from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import sys

AGENTS_DIR = Path(__file__).resolve().parents[2]
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

from evals.lib.adk import write_generated_files
from evals.lib.catalog import load_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MetroSense ADK evals.")
    parser.add_argument(
        "--catalog",
        action="append",
        required=True,
        help="Path to a canonical eval catalog JSON file. Can be passed multiple times.",
    )
    parser.add_argument(
        "--agent-module-path",
        default="agents/metrosense_agent",
        help="Path to the ADK agent module directory.",
    )
    parser.add_argument(
        "--print-detailed-results",
        action="store_true",
        help="Pass through to `adk eval --print_detailed_results`.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    agent_module_path = repo_root / args.agent_module_path
    adk_binary = repo_root / "agents" / ".venv" / "bin" / "adk"

    for catalog_path_str in args.catalog:
        catalog = load_catalog((repo_root / catalog_path_str).resolve())
        eval_set_path, eval_config_path = write_generated_files(repo_root, catalog)

        cmd = [
            str(adk_binary),
            "eval",
            str(agent_module_path),
            str(eval_set_path),
            "--config_file_path",
            str(eval_config_path),
        ]
        if args.print_detailed_results:
            cmd.append("--print_detailed_results")
        subprocess.run(cmd, check=True, cwd=repo_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
