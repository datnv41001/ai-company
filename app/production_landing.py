"""A self-contained local page with an allow-listed bridge to the authenticated parent."""

from html import escape
from decimal import Decimal

CSS = """
:root{color-scheme:light;--bg:#f6f6ed;--ink:#152f26;--panel:#fffef7;--line:#b4c3af;--lime:#d8f282}
*{box-sizing:border-box}body{background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif;margin:0}
main{max-width:76rem;margin:auto;padding:clamp(1rem,5vw,4rem)}.banner{font-size:.83rem;margin:0 0 1.5rem}
header,section,form{background:var(--panel);border:1px solid var(--line);border-radius:1rem;padding:clamp(1rem,3vw,2rem);overflow-wrap:anywhere}
header{background:#153d30;color:#fffef7;margin-bottom:1rem}header h1{font-size:clamp(2rem,7vw,4.7rem);max-width:19ch;line-height:1.09;margin:.3em 0}
h2{font-size:1.28rem;margin:0 0 .5rem}p{margin:.5em 0;white-space:pre-line}.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
form{margin-top:1rem}label{display:grid;gap:.2rem;margin:.6rem 0;max-width:32rem}input,select,button,a{font:inherit;min-height:44px}
input,select{padding:.5rem;border:1px solid var(--line);border-radius:.4rem;width:100%;background:var(--panel);color:var(--ink)}
button,a{display:inline-flex;align-items:center;padding:.5rem 1rem;color:#143221;background:var(--lime);border:1px solid #778455;border-radius:.6rem;font-weight:650}
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #629423;outline-offset:2px}
@media(max-width:660px){.grid{grid-template-columns:1fr}}@media(prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#10251e;--panel:#1b342a;--ink:#f2f5e9;--line:#526958}}
"""
# The iframe has an opaque sandbox origin. It never knows an API token or an external URL.
BRIDGE = """
const form=document.querySelector('form'), output=document.querySelector('[role=status]');
let pending=false;
form.addEventListener('submit', e=>{
 e.preventDefault(); if(pending||!form.reportValidity())return;
 if(parent===window){output.textContent='Mở bản này trong Studio để gửi dữ liệu thử.';return}
 pending=true; form.querySelector('button').disabled=true;
 parent.postMessage(__AMC_SELECTIONS__,'*')
});
window.addEventListener('message',e=>{if(e.source===parent&&e.data?.type==='amc-landing-result/1'){
 output.textContent=String(e.data.message);pending=Boolean(e.data.ok);form.querySelector('button').disabled=pending;
}});
"""


# Legacy exports keep their original bytes. New exports ask only the fields approved in this plan.
def approved_form(contract, cta):
    controls = []
    for field in contract["fields"]:
        name = escape(field["id"])
        required = " required" if field["required"] else ""
        attrs = f'name="{name}" data-answer{required}'
        label = escape(field["label"])
        if not field["required"]:
            label += " (tùy chọn)" if contract["locale"] == "vi-VN" else " (optional)"
        if field["type"] == "integer":
            label += f' ({escape(field.get("unit_label", field["unit"]))})'
            control = f'<input {attrs} type="number" step="1" min="{field["minimum"]}" max="{field["maximum"]}">'
        else:
            options = "".join(f'<option value="{escape(o["value"])}">{escape(o["label"])}</option>' for o in field["options"])
            control = f'<select {attrs}><option value=""></option>{options}</select>'
        controls.append(f"<label>{label}{control}</label>")
    note = ""
    vi = contract["locale"] == "vi-VN"
    qualification = contract["qualification"]
    minimums = qualification["minimum_order_quantities"]
    if contract["action"] == "appointment":
        note = ("Người phụ trách sẽ đối chiếu đề nghị trước khi xác nhận lịch." if vi
                else "Staff will review your request before confirming an appointment.")
    elif qualification["accept_inquiries"] and len(minimums) == 1 and Decimal(minimums[0]) > 1:
        note = ("Nếu cần ít hơn mức tối thiểu, bạn vẫn có thể gửi nhu cầu để được tư vấn. Yêu cầu này chưa đủ điều kiện báo giá."
                if vi else "Below the minimum order, you can still send an inquiry for advice. It does not yet qualify for a quote.")
    return (f'<form id="request" data-contract="{escape(contract["digest"])}"><h2>{escape(cta)}</h2>'
            + (f'<p>{escape(note)}</p>' if note else "")
            + "".join(controls) + f'<label><input type="checkbox" name="consent" required>{escape(contract["consent"]["label"])}</label>'
            + f'<button type="submit">{escape(cta)}</button><p role="status" aria-live="polite"></p></form>')


def produce(groups, plan, projection):
    copy = groups["copy"]
    seo = groups["seo"]
    cta = copy["call_to_action"]
    action = plan["buyer_action"]
    vi = projection["locale"] == "vi-VN"

    def t(local, en):
        return local if vi else en

    panel = t("Dịch vụ và quyền lợi", "Service and benefit") if action == "appointment" else t("Sản phẩm và ứng dụng", "Product and use")
    sections = [(panel, copy["benefit"]), (t("Điều kiện áp dụng", "Applicable terms"), copy["commercial_terms"])]

    def safe(value):
        return escape(str(value), quote=True)  # only text nodes and quoted attributes

    contract = plan.get("intake_contract")
    if contract:
        form = approved_form(contract, cta)
        message = """{type:'amc-landing-submit/2',contract_digest:form.dataset.contract,consent:form.consent.checked,
 answers:Object.fromEntries(Array.from(form.querySelectorAll('[data-answer]')).filter(el=>el.value!=='')
 .map(el=>[el.name,el.type==='number'?Number(el.value):el.value]))}"""
    else:
        message = "{type:'amc-landing-submit/1',quantity:Number(form.quantity.value),place:form.place.value,days:Number(form.days.value)}"
        form = f"""<form id="request"><h2>{safe(cta)}</h2><label>{t("Số lượng", "Quantity")} ({safe(plan["selling_unit"])})<input type="number" name="quantity" required min="1" max="100" step="1" value="1"></label>
<label>{t("Địa điểm thử", "Synthetic location")}<select name="place"><option value="north">{t("Cơ sở thử A", "Test site A")}</option><option value="south">{t("Cơ sở thử B", "Test site B")}</option></select></label>
<label>{t("Lịch dịch vụ dự kiến" if action == "appointment" else "Ngày cần hàng", "Requested service slot" if action == "appointment" else "Required delivery date")}<select name="days"><option value="2">{t("Sau hai ngày", "In two days")}</option><option value="7">{t("Sau một tuần", "In one week")}</option></select></label>
<button type="submit">{t("Gửi yêu cầu tổng hợp", "Submit test request")}</button><p role="status" aria-live="polite"></p></form>"""
    bridge = BRIDGE.replace("__AMC_SELECTIONS__", message)
    html = f"""<!doctype html><html lang="{"vi" if vi else "en"}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; form-action 'none'; base-uri 'none';">
<title>{safe(seo["page_title"])}</title><meta name="description" content="{safe(seo["meta_description"])}"><style>{CSS}</style></head><body><main>
<p class="banner">{t("Trang thử nghiệm nội bộ · Chỉ dùng lựa chọn tổng hợp", "Internal test page · Synthetic selections only")}</p>
<header><h1>{safe(copy["headline"])}</h1><p>{safe(copy["value_proposition"])}</p><a href="#request">{safe(cta)}</a></header>
<div class="grid">{"".join("<section><h2>" + safe(name) + "</h2><p>" + safe(text) + "</p></section>" for name, text in sections)}</div>
{form}
</main><script>{bridge}</script></body></html>"""
    return {
        "contract": "amc.sandbox-landing/2" if contract else "amc.sandbox-landing/1",
        **({"intake_contract": contract} if contract else {}),
        "kind": action,
        "seo": seo,
        "sections": copy,
        "product_id": plan["product_id"],
        "unit": plan["selling_unit"],
        "scope": "synthetic_local",
        "public_tracking": False,
    }, {"landing.html": ("text/html", html.encode())}
