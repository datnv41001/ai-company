"""Two physical local-inference slots per host network namespace.

A bound socket is passed to the actual model process. Even if the coordinator
exits before writing another journal entry, the child retains its physical slot.
"""

from contextlib import contextmanager
import os
import socket
import subprocess
import threading

# Fixed, independent of the PR, checkout, journal and user environment.
PORTS = (41981, 41982)
_spawn_lock = threading.Lock()


@contextmanager
def machine_slot():
    for port in PORTS:
        handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if os.name == "nt":
            handle.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            handle.bind(("127.0.0.1", port))
            handle.listen(1)
        except OSError:
            handle.close()
            continue
        try:
            yield handle
        finally:
            handle.close()
        return
    raise RuntimeError("Both host inference slots are in use")


def spawn_with_slot(slot, command, **kwargs):
    """Only the caller's private model subprocess and its supervisor get this handle."""
    fd = slot.fileno()
    if os.name != "nt":
        return subprocess.Popen(command, pass_fds=(fd,), **kwargs)
    startup = subprocess.STARTUPINFO()
    startup.lpAttributeList = {"handle_list": [fd]}
    with _spawn_lock:
        slot.set_inheritable(True)
        try:
            return subprocess.Popen(command, startupinfo=startup, close_fds=True, **kwargs)
        finally:
            slot.set_inheritable(False)
