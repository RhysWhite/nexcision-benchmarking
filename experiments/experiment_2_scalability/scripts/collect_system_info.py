#!/usr/bin/env python3
"""Collect reproducible hardware and software metadata for Experiment 2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_command(command: list[str]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "command": command}
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "available": True,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_wheel(repo_root: Path) -> Path | None:
    wheels = sorted((repo_root / "software").glob("nexcision-*.whl"))
    return wheels[0] if wheels else None


def platform_commands(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Return platform-appropriate commands without assuming Linux utilities."""
    common = {
        "uname": run_command(["uname", "-a"]),
        "git_commit": run_command(["git", "-C", str(repo_root), "rev-parse", "HEAD"]),
        "nexcise_version": run_command([sys.executable, "-m", "nexcision", "--version"]),
    }

    system = platform.system()
    if system == "Darwin":
        common.update(
            {
                "macos_version": run_command(["sw_vers"]),
                "hardware_profile": run_command(
                    ["system_profiler", "SPHardwareDataType", "-json"]
                ),
                "model": run_command(["sysctl", "-n", "hw.model"]),
                "memory_bytes": run_command(["sysctl", "-n", "hw.memsize"]),
                "physical_cpu_count": run_command(["sysctl", "-n", "hw.physicalcpu"]),
                "logical_cpu_count": run_command(["sysctl", "-n", "hw.logicalcpu"]),
                "power_source": run_command(["pmset", "-g", "batt"]),
                "power_settings": run_command(["pmset", "-g", "custom"]),
                "root_disk": run_command(["diskutil", "info", "/"]),
                "filesystem": run_command(["df", "-h", str(repo_root)]),
            }
        )
    elif system == "Linux":
        common.update(
            {
                "lscpu": run_command(["lscpu"]),
                "memory": run_command(["free", "-b"]),
                "block_devices": run_command(
                    ["lsblk", "-o", "NAME,TYPE,SIZE,ROTA,MODEL,MOUNTPOINT"]
                ),
                "filesystem_repository": run_command(["df", "-T", str(repo_root)]),
                "filesystem_tmp": run_command(["df", "-T", "/tmp"]),
                "hostname": run_command(["hostname", "-f"]),
                "uptime": run_command(["uptime"]),
                "load_average": run_command(["cat", "/proc/loadavg"]),
                "numa": run_command(["numactl", "--hardware"]),
                "slurm_node": run_command(["scontrol", "show", "node", platform.node().split(".")[0]]),
            }
        )
    else:
        common["filesystem"] = run_command(["df", "-h", str(repo_root)])

    return common


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    wheel = find_wheel(repo_root)
    disk = shutil.disk_usage(repo_root)

    payload: dict[str, Any] = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "working_directory": str(Path.cwd().resolve()),
        "repository_root": str(repo_root),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": sys.version,
            "python_executable": sys.executable,
            "logical_cpu_count": os.cpu_count(),
        },
        "storage_at_repository": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
        },
        "environment": {
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
            "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
            "SLURM_JOB_ID": os.environ.get("SLURM_JOB_ID"),
            "SLURM_CPUS_PER_TASK": os.environ.get("SLURM_CPUS_PER_TASK"),
            "SLURM_MEM_PER_NODE": os.environ.get("SLURM_MEM_PER_NODE"),
            "SLURM_JOB_NAME": os.environ.get("SLURM_JOB_NAME"),
            "SLURM_JOB_PARTITION": os.environ.get("SLURM_JOB_PARTITION"),
            "SLURM_JOB_NODELIST": os.environ.get("SLURM_JOB_NODELIST"),
            "SLURM_CPUS_ON_NODE": os.environ.get("SLURM_CPUS_ON_NODE"),
            "SLURM_JOB_CPUS_PER_NODE": os.environ.get("SLURM_JOB_CPUS_PER_NODE"),
            "SLURM_TMPDIR": os.environ.get("SLURM_TMPDIR"),
            "TMPDIR": os.environ.get("TMPDIR"),
        },
        "commands": platform_commands(repo_root),
        "software_wheel": None,
    }

    if wheel is not None:
        payload["software_wheel"] = {
            "path": str(wheel),
            "size_bytes": wheel.stat().st_size,
            "sha256": sha256_file(wheel),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"System information written to: {args.output}")
    print(f"Detected platform: {platform.system()} {platform.machine()}")
    print(f"Free storage at repository: {disk.free / (1024**3):.1f} GiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
