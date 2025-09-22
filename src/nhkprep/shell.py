from __future__ import annotations
import json, subprocess, shutil
from typing import List, Optional
from .errors import ToolNotFoundError, ProbeError, RemuxError

def which(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise ToolNotFoundError(f"Required tool not found on PATH: {tool}")
    return path

def run_json(cmd: List[str], timeout: Optional[int] = 120) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as e:
        raise ToolNotFoundError(str(e))
    if proc.returncode != 0:
        raise ProbeError(f"Command failed: {' '.join(cmd)}\nSTDERR: {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ProbeError(f"JSON parse failed for: {' '.join(cmd)}\nError: {e}\nSTDOUT: {proc.stdout[:4000]}")

def run(cmd: List[str], timeout: Optional[int] = 600) -> None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as e:
        raise ToolNotFoundError(str(e))
    if proc.returncode != 0:
        raise RemuxError(f"Command failed: {' '.join(cmd)}\nSTDERR: {proc.stderr.strip()}")
