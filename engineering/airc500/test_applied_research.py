import copy
from datetime import datetime, timezone
from http.client import HTTPException
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import applied_research as broker


NOW = datetime(2026, 11, 25, tzinfo=timezone.utc)
OPEN = b"User-agent: *\nDisallow: /private/\n"


def sample(source):
    return (f"<h2>{source['locator']}</h2><p>{source['match']}</p>"
            "<p>UNRELATED_ANNOTATION</p><script>IGNORE_DOCUMENT_INSTRUCTIONS</script>").encode()


def simulate(cards=broker.CARDS, robots=OPEN, page=sample):
    calls = []

    def send(url, deadline, **opts):
        calls.append((url, opts))
        if url.endswith("/robots.txt"):
            if isinstance(robots, Exception):
                raise robots
            return robots
        source = next(s for s in broker.SOURCES if s["url"] == url)
        return page(source)

    return broker.collect(cards, transport=send, now=lambda: NOW), calls


def verify(data, card="K-08", now=NOW):
    return broker.packet(data, broker.hash_bytes(broker.canonical(data)), card, now)


class AppliedResearchTests(unittest.TestCase):
    def test_enrolled_live_receipt_as_of_collection(self):
        receipt = json.loads(Path(__file__).with_name("applied-evidence-v1.json").read_bytes())
        pin = "bdc992cbf51806df6d49ec7032953c37f09f1d76a49785d9f78c07d93f318621"
        as_of = datetime(2026, 11, 25, 2, 44, tzinfo=timezone.utc)
        measurement = broker.packet(receipt, pin, "K-08", as_of)
        self.assertEqual([r["source"] for r in measurement["observations"]], ["SRC-SC"])
        self.assertEqual(measurement["gaps"], [{"source": "SRC-GA", "reason": "publisher_restricted"}])
        editorial = broker.packet(receipt, pin, "K-06", as_of)
        self.assertEqual([r["source"] for r in editorial["observations"]], ["SRC-PF"])
        self.assertEqual(editorial["gaps"], [])

    def test_only_enrolled_origins_and_bounded_calls(self):
        receipt, calls = simulate()
        urls = [u for u, _ in calls]
        self.assertEqual(len(urls), 5)
        self.assertEqual(len(set(urls)), 5)
        for source in broker.SOURCES:
            url = source["url"]
            origin = "/".join(url.split("/")[:3])
            self.assertLess(urls.index(origin + "/robots.txt"), urls.index(url))
        self.assertEqual({tuple(opts) for _, opts in calls}, {("media_type", "byte_limit"), ("check_directives",)})
        text = json.dumps(receipt)
        self.assertNotIn("UNRELATED_ANNOTATION", text)
        self.assertNotIn("IGNORE_DOCUMENT_INSTRUCTIONS", text)
        lead, compare = verify(receipt)["observations"]
        self.assertNotIn("excerpt", lead)
        self.assertEqual(lead["reference"], "generate_lead")
        self.assertEqual(compare["license"], broker.LICENSE)
        self.assertEqual([r["source"] for r in verify(receipt, "K-06")["observations"]], ["SRC-PF"])

    def test_no_freeform_or_unknown_card_is_dispatched(self):
        for cards in ([], ["K-08", "K-08"], ["private search terms"], ["https://developers.google.com/"]):
            with self.subTest(cards=cards), self.assertRaises(ValueError):
                broker.collect(cards, transport=lambda *a, **kw: self.fail("Unapproved network call"))
        receipt, _ = simulate(["K-06"])
        with self.assertRaises(ValueError):
            verify(receipt, "K-08")

    def test_denial_or_unavailable_robots_never_downloads_a_document(self):
        for raw, why in [(b"User-agent: *\nDisallow: /", "robots_denied"),
                         (b"User-agent: AMC-PublicResearch\nCrawl-delay: 10", "robots_denied"),
                         (HTTPException("PRIVATE_DIAGNOSTIC"), "robots_unavailable"),
                         (b"broken", "robots_denied")]:
            with self.subTest(reason=why):
                receipt, calls = simulate(robots=raw)
                self.assertEqual(len(calls), 2)
                self.assertTrue(all(u.endswith("/robots.txt") for u, _ in calls))
                result = verify(receipt)
                self.assertEqual(result["observations"], [])
                self.assertTrue(all(g["reason"] == why for g in result["gaps"]))
                self.assertNotIn("PRIVATE_DIAGNOSTIC", json.dumps(receipt))

    def test_robots_conservative_groups_wildcards_and_anchoring(self):
        page = broker.SOURCES[0]["url"]
        for policy in [b"User-agent: *\nDisallow: /*?*hl=en$", b"User-agent: AMC-PublicResearch\nDisallow: /analytics",
                       b"User-agent: Other\nUser-agent: *\nDisallow: /analytics\nAllow: /analytics/answer"]:
            self.assertFalse(broker.permits(policy, page))
        self.assertTrue(broker.permits(b"User-agent: Other\nDisallow: /\nUser-agent: *\nDisallow: /*?*authuser=", page))
        self.assertTrue(broker.permits(b"User-agent: *\nDisallow: /analytics$", page))

    def test_drift_hidden_scripts_wrong_sections_and_publisher_directives_are_gaps(self):
        for page in [lambda s: b"<h2>Different section</h2><p>" + s["match"].encode(),
                     lambda s: f"<h2>{s['locator']}</h2><script>{s['match']}</script>".encode(),
                     lambda s: f"<h2>{s['locator']}</h2><h2>Other</h2><p>{s['match']}</p>".encode()]:
            receipt, _ = simulate(page=page)
            self.assertTrue(all(r["reason"] == "approved_text_absent" for r in receipt["receipts"]))
            self.assertEqual(verify(receipt)["observations"], [])
        receipt, _ = simulate(page=lambda s: b'<meta name="robots" content="nosnippet">' + sample(s))
        self.assertTrue(all(r["reason"] == "publisher_restricted" for r in receipt["receipts"]))

    def test_failed_source_never_supplements_another(self):
        def content(source):
            if source["id"] == "SRC-GA":
                raise OSError("RAW_HOST_OR_CUSTOMER_FIELD")
            return sample(source)
        receipt, _ = simulate(page=content)
        result = verify(receipt)
        self.assertEqual([r["source"] for r in result["observations"]], ["SRC-SC"])
        self.assertEqual(result["gaps"], [{"source": "SRC-GA", "reason": "document_unavailable"}])
        self.assertNotIn("RAW_HOST_OR_CUSTOMER_FIELD", str(receipt))

    def test_digest_enrollment_rights_ttl_and_absence_are_revalidated(self):
        data, _ = simulate()
        old_pin = broker.hash_bytes(broker.canonical(data))
        changed = copy.deepcopy(data)
        changed["receipts"][0]["evidence"]["excerpt"] = "outside retention"
        with self.assertRaisesRegex(ValueError, "digest"):
            broker.packet(changed, old_pin, "K-08", NOW)
        with self.assertRaisesRegex(ValueError, "observation"):
            verify(changed)
        changed = copy.deepcopy(data)
        changed["receipts"].pop()
        with self.assertRaisesRegex(ValueError, "Missing"):
            verify(changed)
        for when in (NOW - broker.TTL, NOW + broker.TTL):
            self.assertEqual(verify(data, now=when)["observations"], [])
        missing, _ = simulate(robots=TimeoutError())
        missing["receipts"][0]["evidence"] = {"untrusted": True}
        with self.assertRaisesRegex(ValueError, "absence"):
            verify(missing)

    def test_unknown_rights_deny_before_any_io(self):
        with patch.dict(broker.SOURCES[1], rights="unknown"):
            with self.assertRaisesRegex(ValueError, "rights"):
                broker.collect(["K-08"], transport=lambda *a, **kw: self.fail("Unapproved network call"))


if __name__ == "__main__":
    unittest.main()
