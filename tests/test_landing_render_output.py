"""Copy-approved text remains data in both HTML content and metadata."""

from app.production_landing import produce


def test_isolated_english_page_escapes_editorial_markup():
    groups = {
        "copy": {
            "headline": "Cartridge <sample>",
            "benefit": "Review both sizes.",
            "commercial_terms": "Box, tax included.",
            "call_to_action": "Request a quote",
            "value_proposition": "Compare sizes.",
        },
        "seo": {"page_title": "<sample>", "meta_description": 'A "sample" & its terms'},
    }
    model, files = produce(groups, {"buyer_action": "rfq", "product_id": "p", "selling_unit": "box"}, {"locale": "en-US"})
    page = files["landing.html"][1].decode()
    assert model["sections"] == groups["copy"] and '<html lang="en">' in page
    assert "<title>&lt;sample&gt;</title>" in page and "Cartridge &lt;sample&gt;" in page
    assert 'content="A &quot;sample&quot; &amp; its terms"' in page and "form-action 'none'" in page
