"""Read host GPU and process working-set counters, without exposing unrelated process records."""

import ctypes
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path


def peak_ram(pid):
    if os.name != "nt":
        rows = Path(f"/proc/{pid}/status").read_text().splitlines()
        return int(next(s.split()[1] for s in rows if s.startswith("VmHWM:"))) * 1024
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [(f"n{i}", ctypes.c_size_t) for i in range(8)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    read = ctypes.WinDLL("psapi").GetProcessMemoryInfo
    read.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        return None
    try:
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        return counters.n0 if read(handle, ctypes.byref(counters), counters.cb) else None
    finally:
        kernel.CloseHandle(handle)


class Resources:
    def __init__(self, pid):
        self.pid = pid
        self.stop = threading.Event()
        self.board = []
        self.process = []
        self.ram = []
        self.tool = shutil.which("nvidia-smi")
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def query(self, setting):
        if not self.tool:
            return []
        result = subprocess.run(
            [self.tool, setting, "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return [s.strip() for s in result.stdout.splitlines()] if not result.returncode else []

    def sample(self):
        while not self.stop.is_set():
            try:
                ram = peak_ram(self.pid)
                if ram:
                    self.ram.append(ram)
                board = self.query("--query-gpu=memory.used")
                if board and board[0].isdigit():
                    self.board.append(int(board[0]))
                for row in self.query("--query-compute-apps=pid,used_gpu_memory"):
                    pid, memory = map(str.strip, row.split(","))
                    if pid == str(self.pid) and memory.isdigit():
                        self.process.append(int(memory))
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            self.stop.wait(1)

    def __enter__(self):
        self.started = time.perf_counter()
        self.thread.start()
        return self

    def __exit__(self, *unused):
        self.stop.set()
        self.thread.join()
        self.elapsed = time.perf_counter() - self.started

    def report(self):
        return dict(
            peak_process_working_set_bytes=max(self.ram, default=None),
            peak_board_vram_mib_sampled=max(self.board, default=None),
            peak_process_vram_mib_sampled=max(self.process, default=None),
            board_samples=len(self.board),
            process_gpu_samples=len(self.process),
            measured_seconds=round(self.elapsed, 3),
            configured_context_tokens=4096,
        )
