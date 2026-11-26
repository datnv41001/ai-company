"""Reconcile a completed synthetic comparison arm and renew only the enrolled lab accounts."""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

FIRST_SHA256 = "3980d268a6615850bf0505afe28fabd92635eea276c276f7ba9fba784d88b65d"
FIRST_RUN = 45727062233


class LabSessions:
    def __init__(self, api, actors):
        self.api = api
        self.actors = actors

    def __getattr__(self, verb):
        request = getattr(self.api, verb)
        if verb not in ("get", "post", "put", "patch", "delete"):
            return request

        def send(*args, **kwargs):
            response = request(*args, **kwargs)
            if response.status_code != 401:
                return response
            supplied = (kwargs.get("headers") or {}).get("Authorization")
            actor = next((a for a in self.actors if a["headers"].get("Authorization") == supplied), None)
            if actor is None:
                return response
            session = self.api.post("/api/auth/login", json={"email": actor["email"], "password": actor["password"]})
            session.raise_for_status()
            actor["headers"]["Authorization"] = "Bearer " + session.json()["access_token"]
            return request(*args, **{**kwargs, "headers": actor["headers"]})

        return send


def restore_small(path, out, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != FIRST_SHA256:
        raise ValueError("Unexpected source archive")
    with ZipFile(path) as archive:
        old = json.loads(archive.read("study.json"))
        if old["frozen_files"] != expected or old["checkout"] != "39945f660f8bc7f8d7b8eebcc0f7ae1d94c5e6fc":
            raise ValueError("Study revision differs")
        inputs = {}
        for case in ("index-tray", "receipt-map"):
            inputs[case] = json.loads(archive.read(case + "/control/approved-inputs.json"))
            for name in archive.namelist():
                if not name.startswith(case + "/qwen05/"):
                    continue
                target = out / Path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
        return old, inputs
