"""Execute generated programs in a fail-closed macOS filesystem/network sandbox."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import Any


class GeneratorError(RuntimeError):
    """A generator failed validation, isolation, or execution."""


def _profile(job: Path, python: Path) -> str:
    roots = {str(python.parent.parent), str(python.resolve().parent.parent)}
    if python.resolve() == Path(sys.executable).resolve():
        roots.update((sys.prefix, sys.base_prefix))
    roots.update((str(job), "/System", "/usr/lib", "/usr/share", "/Library/Apple"))
    reads = " ".join(f"(subpath {json.dumps(root)})" for root in sorted(roots))
    # CPython's macOS startup needs the root directory itself, not its subtree.
    special = " ".join(
        f"(literal {json.dumps(path)})"
        for path in ("/", "/dev/null", "/dev/urandom", "/dev/random", "/etc/localtime", "/private/etc/localtime")
    )
    return f"""(version 1)
(allow default)
(deny network*)
(deny mach-lookup)
(deny file-read*)
(allow file-read* {reads} {special})
(deny file-write*)
(allow file-write* (subpath {json.dumps(str(job))}) (literal "/dev/null"))
(deny process-fork)
(deny process-exec)
(allow process-exec (literal {json.dumps(str(python))}) (literal {json.dumps(str(python.resolve()))}))
"""


def _snippet(path: Path) -> str:
    with path.open("rb") as handle:
        value = handle.read(4096).decode("utf-8", errors="replace")
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", value)


def _decode_output(raw: str, count: int) -> list[dict[str, Any]]:
    try:
        rows = json.loads(raw)
        json.dumps(rows, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise GeneratorError("Generator stdout must be one finite JSON array") from exc
    if not isinstance(rows, list) or len(rows) != count:
        raise GeneratorError(f"Generator must return exactly {count} records")
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("problem"), str) or not row["problem"].strip():
            raise GeneratorError(f"Record {index} needs a nonempty problem string")
        if "answer" not in row:
            raise GeneratorError(f"Record {index} needs an answer")
        if "explanation" in row and not isinstance(row["explanation"], str):
            raise GeneratorError(f"Record {index} explanation must be a string")
    return rows


def run_generator(
    code: str,
    sample_seed: int,
    count: int,
    work_dir: Path,
    python_executable: str = sys.executable,
    timeout: int = 60,
) -> list[dict[str, Any]]:
    """Run code reading {seed,count} on stdin and writing a JSON array on stdout.

    No generated code is imported into this process. Failed jobs remain on disk
    for diagnosis. This requires sandbox-exec and never executes unisolated.
    """
    if sys.platform != "darwin" or not shutil.which("sandbox-exec"):
        raise GeneratorError("Generator runtime not available: macOS sandbox-exec is required")
    python = Path(python_executable).absolute()
    if not python.is_file() or count < 1 or timeout < 1 or not code.strip():
        raise GeneratorError("An existing Python executable, nonempty code and positive count/timeout are required")
    work_dir.mkdir(parents=True, exist_ok=True)
    job = Path(tempfile.mkdtemp(prefix="generator-", dir=work_dir)).resolve()
    script = job / "generator.py"
    script.write_text(code, encoding="utf-8")
    profile = job / "sandbox.sb"
    profile.write_text(_profile(job, python), encoding="utf-8")
    bootstrap = job / "bootstrap.py"
    bootstrap.write_text(
        "import resource, runpy\n"
        f"resource.setrlimit(resource.RLIMIT_CPU, ({timeout}, {timeout}))\n"
        "resource.setrlimit(resource.RLIMIT_FSIZE, (4194304, 4194304))\n"
        "resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))\n"
        f"runpy.run_path({str(script)!r}, run_name='__main__')\n",
        encoding="utf-8",
    )
    request = job / "stdin.json"
    request.write_text(json.dumps({"seed": sample_seed, "count": count}), encoding="utf-8")
    out_path, err_path = job / "stdout.json", job / "stderr.log"
    env = {"HOME": str(job), "TMPDIR": str(job), "PATH": "/usr/bin:/bin", "LC_ALL": "C", "PYTHONHASHSEED": "0"}
    # -I would ignore PYTHONHASHSEED. With a clean env, -P/-s keep imports safe
    # while allowing deterministic string/set hashes inside the OS sandbox.
    command = ["/usr/bin/sandbox-exec", "-f", str(profile), str(python), "-P", "-s", "-B", str(bootstrap)]
    try:
        with request.open("rb") as stdin, out_path.open("wb") as stdout, err_path.open("wb") as stderr:
            proc = subprocess.Popen(command, cwd=job, env=env, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                proc.wait(timeout=timeout + 2)
            except subprocess.TimeoutExpired as exc:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
                raise GeneratorError(f"Generator timed out after {timeout}s; job={job}") from exc
    except OSError as exc:
        raise GeneratorError(f"Generator runtime not available: {exc}") from exc
    if proc.returncode:
        detail = _snippet(err_path)
        if "sandbox-exec:" in detail or "sandbox_init" in detail:
            raise GeneratorError(f"Generator runtime not available: {detail}")
        raise GeneratorError(f"Generator exited {proc.returncode}; job={job}\n{detail}")
    try:
        return _decode_output(out_path.read_text(encoding="utf-8"), count)
    except GeneratorError as exc:
        raise GeneratorError(f"{exc}; job={job}\n{_snippet(err_path)}") from exc
    except UnicodeError as exc:
        raise GeneratorError("Generator stdout must be UTF-8 JSON") from exc
