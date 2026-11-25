# Public documentation receipts for applied knowledge cards

An AMC researcher can use this engineering CLI to check the public definitions behind two cards. A fresh receipt for the GA4 lead event can support its event definition. A client’s instrumentation, consent, lead qualification and revenue each require evidence from that client. Decisions, proposed product features and editorial interpretations remain in the research card.

| Card | Source | What the receipt can carry | Publisher |
| --- | --- | --- | --- |
| K-08 | SRC-GA | The public event identifier and its locator. The lookup phrase is reviewed in the manifest. The output retains only metadata and the identifier. | [Google Analytics recommended events](https://support.google.com/analytics/answer/9267735?hl=en) |
| K-08 | SRC-SC | One short attributed phrase about how the two systems calculate metrics. | [Google Search Central on Analytics and Search Console](https://developers.google.com/search/docs/monitor-debug/google-analytics-search-console) |
| K-06 | SRC-PF | One short attributed editorial question about originality. | [Google Search Central on people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) |

The Search Central pages identify their default text license as CC BY 4.0. Each approved excerpt travels with its publisher, exact source URL, section and license link. Both excerpts retain the publisher’s wording. GA Help is enrolled for public event identifiers and metadata. Its text is used transiently to locate the reviewed event definition. Access restrictions and quotation rights have separate checks. The operator must review changes in terms, access or scope before changing the enrollment. [Google Developers site policies](https://developers.google.com/terms/site-policies) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Observed on 25 November 2026

The internet-enabled operator retrieved SRC-SC and SRC-PF at 02:43 UTC. Their observed pages contained the approved phrases under the enrolled headings. SRC-GA returned `publisher_restricted`. Its receipt contains the check time and robots digest, with zero evidence fields. At handoff a second operator checked both card packets offline using the canonical digest `bdc992cbf51806df6d49ec7032953c37f09f1d76a49785d9f78c07d93f318621`. The historical regression uses the original collection time. Running the packet CLI after the freshness window reports the expired observations as gaps. [Archived receipt](applied-evidence-v1.json)

## Run and replay

From the repository root with Python 3.12+, use a fresh local output path. The first command prints a SHA-256 digest of the canonical receipt JSON. Pass that digest to the person reviewing the run through the handoff. The second command reads the receipt offline and returns observations and gaps for one card.

~~~sh
python engineering/airc500/applied_research.py collect receipt.json K-06 K-08
python engineering/airc500/applied_research.py packet receipt.json --sha256 REVIEWED_RECEIPT_DIGEST --card K-08
python -m unittest discover -s engineering/airc500 -p "test_*research.py" -v
~~~

The collection command accepts only enrolled card IDs. A reviewed manifest maps each one to fixed public document URLs. The collector sends the fixed path, a public User-Agent and HTTP format headers. It uses the original broker’s public DNS admission, pinned socket, hostname-verified TLS and bounded reads. One run has at most two robots requests and three document requests, with a 75-second total deadline, a 12-second robots deadline per origin, a 15-second document deadline, 512,000 bytes per robots file and 2 MB per document. Requests are sequential and have no automatic retry.

Each origin needs an accessible text/plain robots policy. Every applicable disallow rule wins, including global wildcard rules; a more specific allow may therefore still give a gap. Unsupported applicable directives, such as crawl delay, cause a gap. The collector closes on redirects, failed access checks, unsupported representations and restrictive page-level or HTTP robots directives. For approved pages the collector checks the reviewed phrase within the named heading; scripts and templates are excluded. Only the allowlisted metadata and optional short excerpt enter a receipt. Page bodies, cookies and error text remain outside the file.

Every requested source has an observation or a reason for absence. The receipt records UTC, policy and adapter version, plus hashes for the fetched robots file and observed page where available. The packet verifies the supplied digest, card-to-source membership, allowed fields and rights, then checks the seven-day freshness window. Stale material and unavailable pages yield gaps. A changed source requires a new retrieval and a new pin. Keep prior receipts and their original policy commit for historical review.

A local receipt digest protects comparison against the handoff pin. Independent publisher signatures, browser-rendered visibility, a persistent collection service, and verification of client results are outside this CLI’s evidence. A researcher who reads a page through a browser can cite that separately, with its own method and date. The original v4 study and signed Qwen outputs continue to use their archived enrollment and replay commands in [PUBLIC-RESEARCH.md](PUBLIC-RESEARCH.md).
