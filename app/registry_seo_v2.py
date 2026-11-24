"""SEO adapter 2 keeps the v1 output and QA contract, and refines the metadata prompt."""

from . import workforce_gateway as v1


def request(run, model, **kwargs):
    body = v1.request_body(run, model, **kwargs)
    body["messages"][0]["content"] += " Express search_intent as a literal search query suggested by the supplied landing page."
    return body


def validate(raw, stage, plan, sources, binding):
    fields = (*v1.SECTIONS["seo"], "source_ids")
    if not isinstance(raw, dict) or set(raw) != set(fields):
        raise v1.GatewayError("invalid_contract_output")
    return v1.validate_output(raw, stage, plan, sources)
