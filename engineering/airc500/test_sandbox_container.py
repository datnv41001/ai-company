import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import unittest
from unittest.mock import patch

import sandbox_container as sandbox


class ContainmentTests(unittest.TestCase):
    def test_fixture_allowlist_and_image_contents(self):
        for value in ["../.env", "https://example.com", "H999"]:
            with self.assertRaises(ValueError):
                sandbox.scoped_case(value)
        packet = json.loads(sandbox.scoped_case("H01"))
        self.assertEqual(set(packet), {"id", "field", "approved", "head"})
        with patch.object(sandbox, "CORPUS_PIN", "0" * 64), self.assertRaises(ValueError):
            sandbox.scoped_case("H01")
        with tarfile.open(fileobj=io.BytesIO(sandbox.imported_files(b"approved binary"))) as image:
            self.assertEqual(image.getnames(), ["input", "scratch", "worker", "input/case.json"])
            self.assertEqual(image.getmember("worker").mode, 0o555)
            self.assertEqual(image.extractfile("input/case.json").read(), b"")

    def test_daemon_drift_rejected_before_start(self):
        file = Path("/synthetic/case.json")
        image = "sha256:" + "f" * 64
        config = {"User": "65532:65532", "Cmd": ["/worker"], "Entrypoint": None, "Env": None, "OpenStdin": False, "Tty": False}
        volume = {"Type": "bind", "Source": str(file), "Destination": "/input/case.json", "RW": False}
        host = {
            "NetworkMode": "none",
            "PortBindings": {},
            "PublishAllPorts": False,
            "Privileged": False,
            "CapAdd": [],
            "CapDrop": ["ALL"],
            "Devices": [],
            "DeviceRequests": [],
            "VolumesFrom": [],
            "ReadonlyRootfs": True,
            "PidMode": "",
            "IpcMode": "none",
            "CgroupnsMode": "private",
            "SecurityOpt": ["no-new-privileges"],
            "PidsLimit": 32,
            "Memory": sandbox.MEMORY,
            "MemorySwap": sandbox.MEMORY,
            "NanoCpus": 500_000_000,
            "RestartPolicy": {"Name": "no"},
            "Binds": [],
            "LogConfig": {"Type": "none"},
            "Tmpfs": {"/scratch": "rw,noexec,size=4m"},
        }
        inspected = {"HostConfig": host, "Config": config, "Image": image, "Mounts": [volume]}
        sandbox.check_policy(inspected, image, file)
        for field, key, value in (
            ("HostConfig", "NetworkMode", "bridge"),
            ("HostConfig", "CapAdd", ["NET_ADMIN"]),
            ("Config", "Env", ["GITHUB_TOKEN=synthetic"]),
            ("HostConfig", "ReadonlyRootfs", False),
            ("HostConfig", "PidsLimit", -1),
            ("Config", "User", "0"),
            ("HostConfig", "Tmpfs", {}),
        ):
            changed = copy.deepcopy(inspected)
            changed[field][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                sandbox.check_policy(changed, image, file)
        for mounts in ([dict(volume, RW=True)], [volume, dict(volume, Destination="/repo")]):
            with self.assertRaises(ValueError):
                sandbox.check_policy(dict(inspected, Mounts=mounts), image, file)

    def test_verify_rejects_missing_probe_or_unbound_worker(self):
        packet, binary = sandbox.scoped_case("H01"), b"worker"
        checks = dict.fromkeys(
            (
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
            ),
            True,
        )
        expected = {"id": "H01", "approved": "USD 18", "observed": "USD 12", "finding": True}
        report = dict(checks=checks, fixture_sha256=hashlib.sha256(packet).hexdigest(), worker_sha256=hashlib.sha256(binary).hexdigest(), review=expected)
        sandbox.verify_result(report, packet, binary)
        for amended in [dict(checks={}), dict(checks=dict(checks, seccomp=False)), dict(worker_sha256="0" * 64), dict(review=dict(expected, finding=False))]:
            with self.assertRaises(ValueError):
                sandbox.verify_result(dict(report, **amended), packet, binary)

    @unittest.skipUnless(os.getenv("AIRC_TEST_LINUX_DOCKER") == "1", "real local Linux Docker daemon required")
    def test_real_container(self):
        with patch.dict(os.environ, {"AIRC_HOST_ONLY_CANARY": "synthetic"}):
            for case_id, mismatch in [("H01", True), ("H02", False)]:
                report = sandbox.run(case_id)
                self.assertIs(report["review"]["finding"], mismatch)
                self.assertEqual(report["model_invocations"], 0)
                print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
