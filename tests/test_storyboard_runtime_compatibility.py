"""Registry identities pinned before the review of the draft WF-08/2 release."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app import registry, storyboard_runtime, video_storyboard
from app.knowledge_store import canonical, digest
from app.registry_adapters import resolve
from app.registry_compatibility import validate_manifest
from app.storyboard_contract import release_manifest
from test_registry import PG

CATALOG = Path(__file__).resolve().parents[1] / "catalog"
ACCEPTED_V1 = "4dd698583db731fc5e02dfba95eeb92c028466a885266b92a48367c8978ad40e"
REVIEWED_DRAFT = "25bd28157c9b48a49de070857e929acbe5cebeec9fd2b34951c53e5766e44405"
REVIEWED_ADAPTER = "9909b2b2d302e9ba87cb89a6006031cad8fc61183b21a77271ac129cb2a6f73c"


def test_published_v1_and_superseded_draft_bindings():
    legacy, current = (release_manifest(v) for v in (1, 2))
    assert legacy == json.loads((CATALOG / "video-storyboard-v1.json").read_text(encoding="utf8"))
    assert digest(canonical(legacy)) == ACCEPTED_V1
    assert current == json.loads((CATALOG / "video-storyboard-v2.json").read_text(encoding="utf8"))
    assert digest(canonical(current)) != REVIEWED_DRAFT
    archived = deepcopy(current)
    for contract in archived["contracts"].values():
        contract["adapter_digest"] = REVIEWED_ADAPTER
    assert digest(canonical(archived)) == REVIEWED_DRAFT

    assert all(resolve(c) is None for c in archived["contracts"].values())
    with pytest.raises(ValueError, match="differs from the installed capability"):
        validate_manifest(archived)
    db = Mock()
    db.scalar.return_value = {"workflow": storyboard_runtime.RELEASE, "manifest_digest": REVIEWED_DRAFT, "contracts": archived["contracts"]}
    with pytest.raises(HTTPException) as blocked:
        registry.pin(db, SimpleNamespace(tenant_id="synthetic", campaign_id="synthetic"), storyboard_runtime.RELEASE)
    assert blocked.value.status_code == 409


@PG
def test_reviewed_runtime_resolves_both_published_manifests():
    for version, adapter in ((1, video_storyboard), (2, storyboard_runtime)):
        manifest = release_manifest(version)
        validate_manifest(manifest)
        assert all(resolve(c).digest == adapter.source_digest() for c in manifest["contracts"].values())
