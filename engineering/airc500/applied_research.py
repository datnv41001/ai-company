"""Manually collect a bounded public bibliography for two enrolled AMC research cards."""
import argparse
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from hmac import compare_digest
from http.client import HTTPException
import json
from pathlib import Path
import re
import time
from urllib.parse import unquote, urlsplit

from public_research import MAX_BYTES, TTL, PublisherRestriction, VisibleText, _fetch_reviewed, hash_bytes, utc

MANIFEST = Path(__file__).with_name("applied-sources-v1.json")
POLICY = json.loads(MANIFEST.read_bytes())
SOURCES = POLICY["sources"]
CARDS = sorted({s["card"] for s in SOURCES})
AGENT = "amc-publicresearch"
MAX_ROBOTS = 512_000
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
GAPS = {"robots_unavailable", "robots_denied", "document_unavailable", "publisher_restricted", "approved_text_absent"}


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


POLICY_PIN = hash_bytes(canonical(POLICY))


def check_policy():
    origins = {"Google Search Central": "developers.google.com", "Google Analytics Help": "support.google.com"}
    if POLICY["version"] != 1 or len(SOURCES) > 3 or len({s["id"] for s in SOURCES}) != len(SOURCES):
        raise ValueError("Invalid applied source enrollment")
    for source in SOURCES:
        url = urlsplit(source["url"])
        if (url.scheme != "https" or url.netloc != origins.get(source["publisher"]) or
                url.query not in {"", "hl=en"} or url.fragment or not url.path.startswith("/") or
                source["card"] not in {"K-06", "K-08"}):
            raise ValueError("Invalid approved source or card")
        if source["rights"] == "identifier_metadata_only" and not source["excerpt"]:
            continue
        if (source["rights"] != "cc_by_4_0_short_attributed_excerpt" or source["publisher"] != "Google Search Central"
                or source["match"] != source["excerpt"] or not 0 < len(source["excerpt"].split()) <= 16):
            raise ValueError("Missing or unsupported rights for this excerpt")


def permits(robots, url):
    """Conservative subset: every matching Disallow wins, including wildcard groups."""
    if len(robots) > MAX_ROBOTS:
        return False
    target = urlsplit(url)
    path = unquote(target.path + ("?" + target.query if target.query else ""))
    participants, has_rule, saw_agent = [], False, False
    for line in robots.decode("utf-8-sig").splitlines():
        clean = line.split("#", 1)[0].strip()
        if not clean:
            continue
        field, sep, value = clean.partition(":")
        field, value = field.strip().lower(), value.strip()
        if not sep:
            return False
        if field == "user-agent":
            if has_rule:
                participants = []
                has_rule = False
            if not value:
                return False
            participants.append(value.lower())
            saw_agent = True
            continue
        if field == "sitemap":
            continue
        if not participants:
            return False
        has_rule = True
        if not any(a == "*" or a in AGENT for a in participants):
            continue
        if field not in {"allow", "disallow"}:
            return False
        if field == "disallow" and value:
            if not value.startswith("/") or len(value) > 512:
                return False
            # fnmatch supports [] and ?. Robots supports only * and a trailing $.
            pattern = unquote(value).replace("[", "[[]").replace("?", "[?]")
            if fnmatchcase(path, pattern[:-1] if pattern.endswith("$") else pattern + "*"):
                return False
    return saw_agent


class Section(VisibleText):
    """Match within a named heading and its nested sections. Retain only a boolean."""
    def __init__(self, locator):
        super().__init__()
        self.locator = locator.casefold()
        self.level = None
        self.heading = None
        self.sections = []
        self.restricted = False

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        if self.skip:
            return
        values = dict(attrs)
        if tag == "meta" and (values.get("name") or "").lower() in {"robots", "googlebot", AGENT}:
            self.restricted |= (values.get("content") or "").lower().strip() not in {"all", "index", "follow", "index, follow"}
        if re.fullmatch("h[1-6]", tag):
            if self.level and int(tag[1]) <= self.level:
                self.level = None
            self.heading = []

    def handle_endtag(self, tag):
        if self.heading is not None and re.fullmatch("h[1-6]", tag):
            if " ".join(" ".join(self.heading).split()).casefold() == self.locator:
                self.level = int(tag[1])
                self.sections.append([])
            self.heading = None
        super().handle_endtag(tag)

    def handle_data(self, data):
        if self.skip:
            return
        if self.heading is not None:
            self.heading.append(data)
        elif self.level:
            self.sections[-1].append(data)

    def matches(self, phrase):
        return not self.restricted and any(phrase.casefold() in " ".join(" ".join(parts).split()).casefold()
                                           for parts in self.sections)


def metadata(source):
    row = {k: source[k] for k in ("publisher", "url", "locator", "reference", "rights", "limitation")}
    if source["excerpt"]:
        row.update(excerpt=source["excerpt"], license=LICENSE, excerpt_sha256=hash_bytes(source["excerpt"].encode()))
    return row


def evidence(source, data):
    section = Section(source["locator"])
    section.feed(data.decode("utf-8"))
    section.close()
    if section.restricted:
        raise PublisherRestriction("Publisher restricts indexing or reuse")
    if not section.matches(source["match"]):
        return {}
    return metadata(source) | {"raw_sha256": hash_bytes(data), "bytes": len(data), "untrusted": True}


def collect(cards, *, transport=_fetch_reviewed, now=lambda: datetime.now(timezone.utc)):
    check_policy()
    if not cards or set(cards) - set(CARDS) or len(cards) != len(set(cards)):
        raise ValueError("Choose unique enrolled card IDs")
    total = time.monotonic() + 75
    robots_cache, rows = {}, []
    for source in SOURCES:
        if source["card"] not in cards:
            continue
        url = source["url"]
        origin = "https://" + urlsplit(url).netloc
        if origin not in robots_cache:
            try:
                robots_cache[origin] = transport(origin + "/robots.txt", min(total, time.monotonic() + 12),
                                                 media_type="text/plain", byte_limit=MAX_ROBOTS)
            except (OSError, ValueError, HTTPException):
                robots_cache[origin] = None
        controls = robots_cache[origin]
        row = {"source": source["id"], "card": source["card"], "status": "absent", "reason": "robots_unavailable"}
        if controls is not None:
            row["robots_sha256"] = hash_bytes(controls)
            row["reason"] = "robots_denied"
            try:
                if permits(controls, url):
                    row["reason"] = "document_unavailable"
                    data = transport(url, min(total, time.monotonic() + 15), check_directives=True)
                    observed = evidence(source, data) if 0 < len(data) <= MAX_BYTES else {}
                    if observed:
                        del row["reason"]
                        row.update(status="observed", evidence=observed)
                    else:
                        row["reason"] = "approved_text_absent"
            except PublisherRestriction:
                row["reason"] = "publisher_restricted"
            except (OSError, ValueError, HTTPException):
                pass
        row["checked_utc"] = now().isoformat()
        rows.append(row)
    return {"adapter": POLICY["adapter"], "version": 1, "policy_sha256": POLICY_PIN,
            "cards": sorted(cards), "receipts": rows}


def packet(receipt, pin, card, as_of):
    """The digest is supplied independently by the enrolling reviewer or handoff."""
    check_policy()
    if not compare_digest(hash_bytes(canonical(receipt)), pin):
        raise ValueError("Receipt digest differs from enrollment")
    cards = receipt.get("cards")
    if (set(receipt) != {"adapter", "version", "policy_sha256", "cards", "receipts"} or
            receipt["adapter"] != POLICY["adapter"] or receipt["version"] != 1 or
            receipt["policy_sha256"] != POLICY_PIN or not isinstance(cards, list) or
            cards != sorted(set(cards)) or set(cards) - set(CARDS) or card not in cards):
        raise ValueError("Unknown or incomplete applied research enrollment")
    selected = [s for s in SOURCES if s["card"] in cards]
    if len(selected) != len(receipt["receipts"]):
        raise ValueError("Missing source receipt")
    out = {"card": card, "observations": [], "gaps": []}
    for source, row in zip(selected, receipt["receipts"]):
        if row["source"] != source["id"] or row["card"] != source["card"]:
            raise ValueError("Receipt order, source or card mismatch")
        base = {"source", "card", "checked_utc", "status"}
        stamp = utc(row["checked_utc"])
        robots = "robots_sha256" in row
        if robots and not re.fullmatch("[0-9a-f]{64}", row["robots_sha256"]):
            raise ValueError("Invalid access-control digest")
        if row["status"] == "absent":
            if (row.get("reason") not in GAPS or robots == (row["reason"] == "robots_unavailable")
                    or set(row) != base | {"reason"} | ({"robots_sha256"} if robots else set())):
                raise ValueError("Invalid absence receipt")
            if source["card"] == card:
                out["gaps"].append({"source": source["id"], "reason": row["reason"]})
            continue
        e = row.get("evidence", {})
        allowed = metadata(source)
        if (row["status"] != "observed" or set(row) != base | {"evidence", "robots_sha256"}
                or set(e) != set(allowed) | {"raw_sha256", "bytes", "untrusted"} or e["untrusted"] is not True
                or any(e[k] != v for k, v in allowed.items()) or not re.fullmatch("[0-9a-f]{64}", e["raw_sha256"])
                or type(e["bytes"]) is not int or not 0 < e["bytes"] <= MAX_BYTES):
            raise ValueError("Invalid or unapproved observation")
        if source["card"] == card:
            age = (as_of - stamp).total_seconds()
            if 0 <= age < TTL.total_seconds():
                out["observations"].append({"source": source["id"], "checked_utc": row["checked_utc"], **e})
            else:
                out["gaps"].append({"source": source["id"], "reason": "outside_freshness_window"})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    gather = commands.add_parser("collect")
    gather.add_argument("output", type=Path)
    gather.add_argument("cards", choices=CARDS, nargs="+")
    replay = commands.add_parser("packet")
    replay.add_argument("receipt", type=Path)
    replay.add_argument("--sha256", required=True)
    replay.add_argument("--card", choices=CARDS, required=True)
    args = parser.parse_args()
    if args.action == "collect":
        if args.output.exists():
            parser.error("Choose a fresh receipt path")
        receipt = collect(args.cards)
        with args.output.open("x", encoding="utf8", newline="\n") as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(hash_bytes(canonical(receipt)))
    else:
        receipt = json.loads(args.receipt.read_bytes())
        print(json.dumps(packet(receipt, args.sha256, args.card, datetime.now(timezone.utc)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
