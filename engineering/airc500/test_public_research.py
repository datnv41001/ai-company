"""Offline broker policy tests. No network or model calls."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from http.client import RemoteDisconnected
import socket
import time
import unittest
from unittest.mock import MagicMock, patch

from public_research import BY_ID, MAX_BYTES, POLICY, TOPICS, TTL, collect, get_page, observe, packet, public_ip, resolve_public

NOW = datetime.now(timezone.utc)


def example(key):
    return ("<main>" + " ".join(BY_ID[key]["excerpts"]) + "</main>").encode()


class PublicResearchTest(unittest.TestCase):
    def test_public_topics_are_the_only_egress_input(self):
        calls = []

        def transport(key, deadline):
            self.assertGreater(deadline, time.monotonic())
            calls.append(key)
            return example(key)

        for topics in ([], ["catalog", "catalog"], ["client XYZ budget 15000"], ["catalog", "file"]):
            with self.assertRaises(ValueError):
                collect(topics, transport)
        self.assertEqual(calls, [])
        result = collect(TOPICS, transport)
        self.assertEqual(calls, [s["id"] for s in POLICY])
        for _ in range(3):
            self.assertEqual(len(packet(result, "analytics", datetime.now(timezone.utc))), 1)
        self.assertEqual(len(calls), len(POLICY))

    def test_drops_unreviewed_text_and_preserves_anecdote_status(self):
        raw = b"<b>Unapproved suggestion; unrelated private name</b>" + example("S")
        obs = observe("S", raw, NOW)
        self.assertNotIn("Unapproved", str(obs))
        self.assertTrue(obs["untrusted"])
        self.assertEqual(obs["quality"], "unverified anecdote")
        self.assertNotEqual(obs["raw_sha256"], obs["excerpt_sha256"])
        with self.assertRaises(ValueError):
            observe("S", b"<script>" + example("S") + b"</script>", NOW)
        with self.assertRaises(ValueError):
            observe("S", b" " * (MAX_BYTES + 1), NOW)

    def test_error_is_a_gap_and_no_unreviewed_fallback(self):
        def fail(key, deadline):
            raise RemoteDisconnected("No response")

        result = collect(["community"], fail)
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["gaps"][0]["source"], "S")
        self.assertEqual(packet(result, "community", NOW), [])

    def test_pins_ttl_deduplication_and_authority(self):
        result = collect(["community"], lambda key, _: example(key))
        for mutation in ("quality", "url", "untrusted", "raw_sha256", "duplicate", "policy", "excerpt"):
            changed = deepcopy(result)
            obs = changed["observations"][0]
            if mutation == "duplicate":
                changed["observations"].append(obs)
            elif mutation == "policy":
                changed["policy_sha256"] = "x" * 64
            elif mutation == "excerpt":
                obs["excerpts"] = ["unsupported"]
            else:
                obs[mutation] = "altered"
            with self.assertRaises(ValueError, msg=mutation):
                packet(changed, "community", NOW)
        when = datetime.fromisoformat(result["observations"][0]["retrieved_utc"])
        self.assertEqual(packet(result, "community", when + TTL), [])
        self.assertEqual(packet(result, "community", when - timedelta(seconds=1)), [])
        self.assertEqual(packet(result, "analytics", when), [])

    def test_dns_rejects_nonpublic_or_mixed_resolution(self):
        for address in ("127.0.0.1", "169.254.1.1", "10.1.1.1", "::1", "ff02::1", "::ffff:127.0.0.1"):
            self.assertFalse(public_ip(address))
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 443)), (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.1.2.3", 443))]
        with patch("socket.getaddrinfo", return_value=addresses), self.assertRaisesRegex(ValueError, "DNS admission"):
            resolve_public("unused.example", time.monotonic() + 1)


class TransportPolicyTest(unittest.TestCase):
    def response(self, status, content_type, headers, chunks):
        conn = MagicMock()
        reply = conn.getresponse.return_value
        reply.status = status
        reply.headers.get_content_type.return_value = content_type
        reply.getheader.side_effect = lambda key, default=None: headers.get(key, default)
        reply.read1.side_effect = chunks
        with (
            patch("public_research.resolve_public", return_value=(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 443))),
            patch("public_research.HTTPSConnection", return_value=conn),
            patch("public_research.socket.socket") as sock,
            patch("public_research.ssl.create_default_context") as ctx,
        ):
            result = get_page("G", time.monotonic() + 2)
            sock.return_value.__enter__.return_value.connect.assert_called_once_with(("8.8.8.8", 443))
            self.assertEqual(ctx.return_value.wrap_socket.call_args.kwargs["server_hostname"], "support.google.com")
            args = conn.request.call_args
            self.assertEqual(args.args, ("GET", "/analytics/answer/12195621?hl=en"))
            self.assertEqual(set(args.kwargs["headers"]), {"Accept", "Accept-Encoding", "User-Agent"})
            return result

    def test_only_preapproved_get_with_pinned_transport(self):
        self.assertEqual(self.response(200, "text/html", {"Content-Length": "2"}, [b"ok", b""]), b"ok")

    def test_redirect_binary_encoding_short_or_large_body_fails(self):
        for status, typ, headers, chunks in [
            (302, "text/html", {"Location": "https://example.org/"}, []),
            (200, "text/plain", {}, []),
            (200, "text/html", {"Content-Encoding": "gzip"}, []),
            (200, "text/html", {"Content-Length": "4"}, [b"no", b""]),
            (200, "text/html", {"Content-Length": str(MAX_BYTES + 1)}, []),
        ]:
            with self.subTest(status=status, typ=typ, headers=headers), self.assertRaises(ValueError):
                self.response(status, typ, headers, chunks)
