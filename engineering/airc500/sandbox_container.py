"""Run one frozen synthetic fact check in a local, offline Linux container."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid


HERE = Path(__file__).resolve().parent
CORPUS_PIN = "3c1ddbc6b862ecff979a0544f34dc4b874b8e5f49604e75aaba9329a0780382f"
NAME = "airc-synthetic-fact-review"
SOCKET = "unix:///var/run/docker.sock"
MEMORY = 64 * 1024 * 1024
SCRATCH = 4 * 1024 * 1024
INPUT = "/input/case.json"


def scoped_case(case_id):
    raw = (HERE / "fixtures/marketing-pr.json").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != CORPUS_PIN:
        raise ValueError("Frozen synthetic fixture changed")
    for row in json.loads(raw):
        if row["id"] == case_id:
            return json.dumps({k: row[k] for k in ("id", "field", "approved", "head")}, sort_keys=True).encode()
    raise ValueError("Unknown synthetic case")


def check_policy(info, image, scoped_file):
    """Reject unexpected effective daemon configuration before starting the worker."""
    host, config = info["HostConfig"], info["Config"]
    mounts = [mount for mount in info["Mounts"] if mount["Type"] != "tmpfs"]
    scratch_mounts = [mount for mount in info["Mounts"] if mount["Type"] == "tmpfs"]
    checks = (
        info["Image"] == image and config["User"] == "65532:65532",
        config["Cmd"] == ["/worker"] and not config["Entrypoint"],
        not config["Env"] and not config["OpenStdin"] and not config["Tty"],
        host["NetworkMode"] == "none" and not host["PortBindings"] and not host["PublishAllPorts"],
        not host["Privileged"] and not host["CapAdd"] and host["CapDrop"] == ["ALL"],
        not host["Devices"] and not host["DeviceRequests"] and not host["VolumesFrom"],
        host["ReadonlyRootfs"] and host["PidMode"] in ("", "private") and host["IpcMode"] == "none",
        host["CgroupnsMode"] == "private" and host["SecurityOpt"] in (["no-new-privileges"], ["no-new-privileges=true"]),
        host["PidsLimit"] == 32 and host["Memory"] == host["MemorySwap"] == MEMORY and host["NanoCpus"] == 500_000_000,
        host["RestartPolicy"]["Name"] in ("", "no") and not host["Binds"],
        host["LogConfig"]["Type"] == "none",
        set(host["Tmpfs"]) == {"/scratch"} and all(mount["Destination"] == "/scratch" for mount in scratch_mounts),
        len(mounts) == 1
        and mounts[0]["Type"] == "bind"
        and mounts[0]["RW"] is False
        and mounts[0]["Destination"] == INPUT
        and mounts[0]["Source"] == str(scoped_file),
    )
    fields = (
        "image/user",
        "command",
        "environment/stdio",
        "network",
        "capabilities",
        "devices",
        "rootfs/pid/ipc",
        "cgroup/security options",
        "resource limits",
        "restart/volumes",
        "log driver",
        "scratch",
        "input mount",
    )
    unexpected = [field for field, valid in zip(fields, checks, strict=True) if not valid]
    if unexpected:
        raise ValueError("Unexpected container isolation configuration: " + ", ".join(unexpected))


def imported_files(binary):
    """No build context, repository checkout, base image, mounts or operator config enter the image."""
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as archive:
        for directory in ("input", "scratch"):
            entry = tarfile.TarInfo(directory)
            entry.type, entry.mode = tarfile.DIRTYPE, 0o555
            archive.addfile(entry)
        for name, data, mode in (("worker", binary, 0o555), ("input/case.json", b"", 0o444)):
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode = len(data), mode
            archive.addfile(entry, io.BytesIO(data))
    return out.getvalue()


def verify_result(report, packet, binary):
    case = json.loads(packet)
    required = {
        "nonroot",
        "no_capabilities",
        "no_new_privileges",
        "seccomp",
        "loopback_only",
        "root_readonly",
        "fixture_readonly",
        "only_one_input",
        "scratch_bounded",
        "scratch_hardened",
        "secrets_absent",
        "environment_allowlisted",
    }
    if set(report["checks"]) != required or not all(v is True for v in report["checks"].values()):
        raise ValueError("Containment probe failed")
    expected = {
        "id": case["id"],
        "finding": case["approved"] != case["head"],
        "approved": case["approved"],
        "observed": case["head"],
    }
    if (
        report["review"] != expected
        or report["fixture_sha256"] != hashlib.sha256(packet).hexdigest()
        or report["worker_sha256"] != hashlib.sha256(binary).hexdigest()
    ):
        raise ValueError("Worker output does not match the admitted fixture and runtime")


def run(case_id):
    packet = scoped_case(case_id)
    if sys.platform != "linux":
        raise RuntimeError("This boundary requires Linux and a local Docker daemon")
    docker, go = shutil.which("docker"), shutil.which("go")
    if not docker or not go:
        raise RuntimeError("Local Docker and a Go toolchain are required")
    with tempfile.TemporaryDirectory(prefix="airc-sandbox-") as tmp:
        stage = Path(tmp).resolve()
        env = {"PATH": os.defpath + ":" + str(Path(go).parent), "HOME": str(stage), "LANG": "C"}
        config_dir = stage / "docker-config"
        config_dir.mkdir()
        cli = [docker, "--host", SOCKET, "--config", str(config_dir)]

        def command(args, *, stdin=None, timeout=30):
            return subprocess.run(args, input=stdin, capture_output=True, timeout=timeout, env=env, cwd=stage, check=True).stdout

        binary_path = stage / "worker"
        build_env = dict(
            env,
            GOENV="off",
            GOTOOLCHAIN="local",
            GO111MODULE="off",
            GOWORK="off",
            GOPROXY="off",
            GOSUMDB="off",
            CGO_ENABLED="0",
            GOCACHE=str(stage / "go-cache"),
        )
        subprocess.run(
            [go, "build", "-trimpath", "-buildvcs=false", "-o", str(binary_path), str(HERE / "sandbox_worker.go")],
            cwd=stage,
            env=build_env,
            check=True,
            timeout=150,
        )
        binary = binary_path.read_bytes()
        scoped = stage / "case.json"
        scoped.write_bytes(packet)
        scoped.chmod(0o444)
        # A neighboring file is deliberately excluded from the sole input bind.
        (stage / "host-secret-canary").write_text("synthetic-canary")
        nonce = str(uuid.uuid4())
        image = command([*cli, "import", "--change", "LABEL airc.synthetic=" + nonce, "-"], stdin=imported_files(binary)).decode().strip()
        container = None
        try:
            args = [
                *cli,
                "create",
                "--pull=never",
                "--name",
                NAME,
                "--label",
                "airc.synthetic=" + nonce,
                "--network",
                "none",
                "--ipc",
                "none",
                "--cgroupns",
                "private",
                "--user",
                "65532:65532",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--read-only",
                "--pids-limit",
                "32",
                "--cpus",
                "0.5",
                "--memory",
                "64m",
                "--memory-swap",
                "64m",
                "--ulimit",
                "nofile=64:64",
                "--ulimit",
                "fsize=1048576:1048576",
                "--log-driver",
                "none",
                "--tmpfs",
                "/scratch:rw,noexec,nosuid,nodev,size=4m,mode=0700,uid=65532,gid=65532",
                "--mount",
                f"type=bind,src={scoped},dst={INPUT},readonly",
                image,
                "/worker",
            ]
            container = command(args).decode().strip()
            (info,) = json.loads(command([*cli, "inspect", container]))
            check_policy(info, image, scoped)
            raw = command([*cli, "start", "--attach", container], timeout=15)
            if len(raw) > 8192:
                raise ValueError("Unexpected worker output size")
            (state,) = json.loads(command([*cli, "inspect", container]))
            if state["State"]["Running"] or state["State"]["ExitCode"] != 0:
                raise RuntimeError("Container worker did not exit successfully")
            report = json.loads(raw)
            verify_result(report, packet, binary)
            return {
                "version": "airc-synthetic-isolation-v1",
                "worker": "deterministic-literal-fact-check",
                "model_invocations": 0,
                "corpus_sha256": CORPUS_PIN,
                "image_id": image,
                **report,
            }
        finally:
            # Only IDs created by this call are removed. A busy instance is never evicted.
            if container:
                command([*cli, "rm", "--force", container])
            command([*cli, "image", "rm", image])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, help="ID in the frozen marketing fixture, e.g. H01")
    print(json.dumps(run(parser.parse_args().case), sort_keys=True))
