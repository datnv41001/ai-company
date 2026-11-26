"""Version dispatcher for immutable WF-08/1 and the Content → Storyboard WF-08/2 release."""

import hashlib
import json
from pathlib import Path

from . import storyboard_brief as brief, video_storyboard as legacy
from .knowledge_store import canonical, digest
from .workforce_gateway import GatewayError

RELEASE = "WF-08/video-storyboard@2"
RELEASES = (legacy.RELEASE, RELEASE)
ADAPTER = "local-storyboard/2"
FIELDS = {"director": "assignment", "content": "handoff_json", "storyboard": "board_json"}
VERSIONS = {"director": 7, "content": 5, "storyboard": 2}
ASSIGNMENTS = {
    "director": "Assign the signed brief to Content, then pass its verified handoff to Storyboard.",
    "content": "Prepare a source-bound vertical-social script and production direction.",
    "storyboard": "Build the storyboard from the verified Content handoff and record brief coverage.",
}


def source_digest():
    code = [legacy.source_digest(), *(Path(f).read_text(encoding="utf8") for f in (brief.__file__, __file__))]
    return hashlib.sha256("\n".join(code).encode()).hexdigest()


def is_run(run):
    return run is not None and run.knowledge.get("registry", {}).get("workflow") in RELEASES


def adapter_for(run):
    return ADAPTER if run.knowledge["registry"]["workflow"] == RELEASE else legacy.ADAPTER


def compose(projection, ref, variant="direct", *, release):
    if release == legacy.RELEASE:
        return legacy.compose(projection, ref, variant)
    if release == RELEASE:
        return brief.compose(projection, ref, variant)
    raise ValueError("Unknown storyboard release")


def require_fulfillment(board, projection):
    if board["version"] == legacy.EXPORT:
        return
    result = brief.assessment(projection, board)
    if board["version"] != "amc.storyboard/2" or board["brief_fulfillment"] != result or not result["ready_for_qa"]:
        raise ValueError("Resolve each mandatory brief criterion against the current revision")


def request(run, model, *, node, predecessors=None, **_):
    body = legacy.request(run, model, node=node)
    stage = node.skill
    field = FIELDS[stage]
    body.update(local_adapter=ADAPTER, model=ADAPTER)
    schema = body["response_format"]["json_schema"]
    schema.update(name="wf08_v2_" + stage,
                  schema={"type": "object", "properties": {field: {"type": "string"}}, "required": [field], "additionalProperties": False})
    if stage == "storyboard":
        # The predecessor checkpoint stores a short digest in text; the complete
        # approved script remains auditable in sections without mailbox truncation.
        body["content_digest"] = (predecessors or {}).get("n01")
    return body


def execute(body):
    if body.get("local_adapter") == legacy.ADAPTER:
        return legacy.execute(body)
    stage = body.get("stage")
    if body.get("local_adapter") != ADAPTER or stage not in FIELDS:
        raise GatewayError("unknown_storyboard_adapter")
    if stage == "director":
        return {"assignment": ASSIGNMENTS[stage]}, 0, 0
    try:
        projection, ref = body["context"], body["manifest"]
        plan = brief.handoff(projection, ref)
        if stage == "content":
            return {"handoff_json": legacy.json_text(plan)}, 0, 0
        if body.get("content_digest") != digest(canonical(plan)):
            raise GatewayError("storyboard_invalid_checkpoint")
        board = brief.compose(projection, ref, plan=plan)
        return {"board_json": legacy.json_text(board)}, 0, 0
    except (ValueError, KeyError) as exc:
        raise GatewayError("storyboard_needs_revision") from exc


def validated(raw, body):
    if body.get("local_adapter") == legacy.ADAPTER:
        return legacy.validated(raw, body)
    expected = execute(body)[0]
    if raw != expected:
        raise GatewayError("invalid_storyboard_reply")
    field = FIELDS[body["stage"]]
    value = json.loads(raw[field])
    fingerprint = digest(canonical(value))
    if body["stage"] == "content":
        return {"text": fingerprint, "sections": {"content_handoff": raw[field]},
                "source_ids": [f["source_id"] for f in value["channel_copy"]["declarations"]], "handoff_digest": fingerprint}
    return {"text": raw[field], "sections": {"storyboard": raw[field]}, "source_ids": value["source_refs"]["facts"],
            "storyboard_digest": fingerprint}
