"""Read authenticated PR metadata. Only the approved synthetic source can enter a review."""

import argparse
import json
import os
from pathlib import Path
import re
import time
import urllib.request

from pilot_fixture import synthetic_pr
from generation_inbox import GenerationInbox, V3_REPO

PRODUCT_REPO = "datnv41001/ai-company"
SYNTHETIC_REPO = "fixture/marketing-exhibition"
LIMIT = 256_000
SHA = re.compile("[0-9a-f]{40}")
DELIVERY = re.compile("[A-Za-z0-9-]{1,100}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def github_head(repo, number):
    """Read only public PR metadata from GitHub. No redirects, proxies, token or source URLs."""
    if repo != PRODUCT_REPO or type(number) is not int or number < 1:
        raise ValueError("unsupported metadata lookup")
    url = f"https://api.github.com/repos/{PRODUCT_REPO}/pulls/{number}"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "AMC-AIRC-intake"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=8) as response:
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("metadata too large")
    result = json.loads(data)
    if result["number"] != number or result["base"]["repo"]["full_name"] != repo:
        raise ValueError("unrelated metadata")
    return result["state"], result["base"]["sha"], result["head"]["sha"], result["base"]["ref"], result["updated_at"]


def current_head(repo, number):
    if repo == SYNTHETIC_REPO and number == 1:
        manifest, _ = synthetic_pr()
        return "open", manifest["base_sha"], manifest["head_sha"]
    if repo == V3_REPO and number == 1:
        from union_cases import holdout, manifest

        m = manifest(holdout()[0])
        return "open", m["base"], m["head"], "main"
    return github_head(repo, number)


class Inbox(GenerationInbox):
    def __init__(self, file, secret, *, lookup=current_head, clock=time.time):
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("a separately provisioned webhook secret is required")
        self.file, self.secret, self.lookup, self.clock = str(file), secret, lookup, clock
        self.initialize()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--db", required=True)
    cli.add_argument("--delivery", required=True)
    sub = cli.add_subparsers(dest="action", required=True)
    event = sub.add_parser("receive")
    event.add_argument("--body", required=True)
    event.add_argument("--signature", required=True)
    draft = sub.add_parser("handoff")
    draft.add_argument("--directory", required=True)
    draft.add_argument("--archive-sha256", required=True)
    draft.add_argument("--trust-sha256", required=True)
    ack = sub.add_parser("ack")
    ack.add_argument("--outbox-key", required=True)
    args = cli.parse_args()
    box = Inbox(args.db, os.environ["AIRC_WEBHOOK_SECRET"].encode())
    if args.action == "receive":
        with Path(args.body).open("rb") as source:
            result = box.ingest(source.read(LIMIT + 1), args.signature, args.delivery, "pull_request")
    elif args.action == "ack":
        result = box.acknowledge(args.delivery, args.outbox_key)
    else:
        result = box.handoff(args.delivery, args.directory, args.archive_sha256, args.trust_sha256)
    print(json.dumps(result, indent=2))
