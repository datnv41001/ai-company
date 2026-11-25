"""Bounded public-only editorial research. Intake accepts fixed public topic IDs."""

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
from http.client import HTTPSConnection, HTTPException
from ipaddress import IPv6Address, ip_address
import json
from pathlib import Path
import queue
import re
import socket
import ssl
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent / "research-v4"
POLICY = json.loads((ROOT / "sources.json").read_bytes())
SUPPLEMENT = json.loads((ROOT / "supplement.json").read_bytes())
BY_ID = {s["id"]: s for s in POLICY + SUPPLEMENT}
TOPICS = sorted({s["topic"] for s in POLICY})
MAX_BYTES = 2_000_000
TTL = timedelta(days=7)


def hash_bytes(data):
    return sha256(data).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf8", newline="\n")


def utc(value):
    dt = datetime.fromisoformat(value)
    if dt.utcoffset() != timedelta(0):
        raise ValueError("Expected UTC retrieval timestamp")
    return dt


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template", "svg", "noscript"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "template", "svg", "noscript"}:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def public_ip(value):
    addr = ip_address(value)
    return addr.is_global and not addr.is_multicast and not (isinstance(addr, IPv6Address) and (addr.ipv4_mapped or addr.sixtofour or addr.teredo))


def resolve_public(host, deadline):
    results = queue.Queue(maxsize=1)

    def resolve():
        try:
            results.put(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        except OSError:
            results.put([])

    threading.Thread(target=resolve, daemon=True).start()
    try:
        rows = results.get(timeout=min(5, remaining(deadline)))
    except queue.Empty:
        raise TimeoutError("Public DNS exceeded deadline") from None
    if not rows or not all(public_ip(r[4][0]) for r in rows):
        raise ValueError("Public DNS admission failed")
    return sorted(rows, key=lambda r: r[0] != socket.AF_INET)[0]


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise TimeoutError("Public retrieval deadline")
    return seconds


def get_page(source_id, deadline):
    return _fetch_reviewed(BY_ID[source_id]["url"], deadline)


class PublisherRestriction(ValueError):
    """The reviewed publisher has restricted reuse of this representation."""


def _fetch_reviewed(destination, deadline, *, media_type="text/html", byte_limit=MAX_BYTES, check_directives=False):
    """Internal transport. Callers choose destinations exclusively from their reviewed enrollment."""
    url = urlsplit(destination)
    if url.scheme != "https" or url.port or url.username or url.password or url.fragment:
        raise ValueError("Invalid reviewed destination")
    family, socktype, proto, _, address = resolve_public(url.hostname, deadline)
    # Connect only to the validated address; certificate and SNI use the original hostname.
    context = ssl.create_default_context()
    conn = HTTPSConnection(url.hostname, timeout=remaining(deadline), context=context)
    timer = None
    try:
        with socket.socket(family, socktype, proto) as raw:
            raw.settimeout(remaining(deadline))
            raw.connect(address)
            raw.settimeout(remaining(deadline))
            tls = context.wrap_socket(raw, server_hostname=url.hostname, do_handshake_on_connect=False)
            conn.sock = tls

            def interrupt():
                # A completeness or header read can block while a publisher trickles bytes.
                try:
                    tls.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

            timer = threading.Timer(remaining(deadline), interrupt)
            timer.daemon = True
            timer.start()
            tls.do_handshake()
            conn.request(
                "GET",
                url.path + ("?" + url.query if url.query else ""),
                headers={"Accept": media_type, "Accept-Encoding": "identity", "User-Agent": "AMC-PublicResearch/1.0"},
            )
            reply = conn.getresponse()
            if reply.status != 200 or reply.headers.get_content_type() != media_type or reply.getheader("Content-Encoding", "identity") != "identity":
                raise ValueError(f"Unexpected response status, type or encoding ({reply.status})")
            if check_directives:
                for directive in reply.headers.get_all("X-Robots-Tag", []):
                    if directive.strip().lower() not in {"all", "index", "follow", "index, follow"}:
                        raise PublisherRestriction("Publisher restricts indexing or reuse")
            # read1 returns after one underlying read and lets slow senders hit the total deadline.
            declared = reply.getheader("Content-Length")
            if declared is not None and (not declared.isdecimal() or int(declared) > byte_limit):
                raise ValueError("Invalid or excessive declared length")
            data = bytearray()
            while len(data) <= byte_limit:
                if conn.sock:
                    conn.sock.settimeout(remaining(deadline))
                remaining(deadline)
                part = reply.read1(min(65536, byte_limit + 1 - len(data)))
                if not part:
                    if declared is not None and len(data) != int(declared):
                        raise ValueError("Incomplete public page")
                    return bytes(data)
                data.extend(part)
            raise ValueError("Public page exceeds byte quota")
    finally:
        if timer:
            timer.cancel()
        conn.close()


QUALITY = {
    "platform_documentation": "first-party platform rule",
    "competitor_documentation": "first-party product description",
    "market_methodology": "official statistical methods",
    "market_study": "official release series",
    "community_feedback": "unverified anecdote",
    "marketing_discussion": "unverified anecdote",
}


def observe(source_id, data, when):
    spec = BY_ID[source_id]
    if len(data) > MAX_BYTES:
        raise ValueError("Public page exceeds byte quota")
    parser = VisibleText()
    parser.feed(data.decode("utf8"))
    visible = " ".join(" ".join(parser.parts).split()).casefold()
    if not all(quote.casefold() in visible for quote in spec["excerpts"]):
        raise ValueError("Approved excerpt absent; source needs fresh editorial review")
    return {
        **spec,
        "retrieved_utc": when.isoformat(),
        "bytes": len(data),
        "raw_sha256": hash_bytes(data),
        "excerpt_sha256": hash_bytes("\n".join(spec["excerpts"]).encode()),
        "quality": QUALITY[spec["kind"]],
        "retention": "Short approved quotations only; transient full body discarded",
        "untrusted": True,
    }


def collect(topics, transport=get_page, *, supplement=False):
    if not topics or set(topics) - set(TOPICS) or len(topics) != len(set(topics)):
        raise ValueError("Choose unique approved topics")
    observations, gaps = [], []
    deadline = time.monotonic() + 90
    for spec in SUPPLEMENT if supplement else POLICY:
        if spec["topic"] in topics:
            try:
                data = transport(spec["id"], min(deadline, time.monotonic() + 15))
                observations.append(observe(spec["id"], data, datetime.now(timezone.utc)))
            except (OSError, ValueError, HTTPException) as exc:
                gaps.append({"source": spec["id"], "reason": str(exc)[:200]})
    return {
        "version": 1,
        "policy_sha256": hash_bytes((ROOT / ("supplement.json" if supplement else "sources.json")).read_bytes()),
        "observations": observations,
        "gaps": gaps,
    }


def packet(snapshot, topic, now):
    policies = {hash_bytes((ROOT / name).read_bytes()): entries for name, entries in (("sources.json", POLICY), ("supplement.json", SUPPLEMENT))}
    allowed = {entry["id"] for entry in policies.get(snapshot["policy_sha256"], [])}
    if topic not in TOPICS or not allowed or snapshot["version"] != 1:
        raise ValueError("Unknown topic or policy")
    ids = [obs["id"] for obs in snapshot["observations"]] + [gap["source"] for gap in snapshot["gaps"]]
    if len(ids) != len(set(ids)) or set(ids) - allowed:
        raise ValueError("Unenrolled or duplicate public source")
    rows = []
    for obs in snapshot["observations"]:
        source = BY_ID[obs["id"]]
        if (
            obs["quality"] != QUALITY[source["kind"]]
            or obs["untrusted"] is not True
            or not re.fullmatch("[0-9a-f]{64}", obs["raw_sha256"])
            or not 0 < obs["bytes"] <= MAX_BYTES
        ):
            raise ValueError("Invalid evidence provenance")
        if source["topic"] != topic:
            continue
        if any(obs.get(k) != v for k, v in source.items()) or obs["excerpt_sha256"] != hash_bytes("\n".join(source["excerpts"]).encode()):
            raise ValueError("Unapproved source or text")
        age = now - utc(obs["retrieved_utc"])
        if timedelta(0) <= age < TTL:
            rows.append({k: obs[k] for k in ("id", "publisher", "url", "quality", "locator", "excerpts", "limitations", "untrusted")})
    return rows


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--supplement", action="store_true", help="Read the separately enrolled statistical release")
    p.add_argument("output", type=Path)
    p.add_argument("--fixture", choices=["public-marketing-v4"], help="Derive topics from the enrolled synthetic PR")
    p.add_argument("topics", nargs="*", metavar="TOPIC", help="Reviewed topics: " + ", ".join(TOPICS))
    a = p.parse_args()
    if a.fixture:
        if a.topics:
            p.error("Choose the enrolled fixture or explicit public topics")
        cases = json.loads((ROOT / "blind-cases.json").read_bytes())["cases"]
        a.topics = sorted({c["topic"] for c in cases})
    if not a.topics or set(a.topics) - set(TOPICS):
        p.error("Choose at least one enrolled public topic")
    if a.output.exists():
        p.error("Choose a fresh snapshot file")
    result = collect(a.topics, supplement=a.supplement)
    dump(a.output, result)
    print(f"Retrieved {len(result['observations'])} public pages. Gaps: {result['gaps']}")
