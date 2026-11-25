"""Produce labeled-by-case but arm-masked packets from actual completed local runs."""
import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path


def write_packet(root):
    cases_path = Path(__file__).with_name("cases.json")
    cases = json.loads(cases_path.read_text(encoding="utf8"))["cases"]
    conditions = [json.loads((root / f"{arm}-conditions.json").read_text(encoding="utf8")) for arm in ("legacy","projected")]
    for field in ("model_sha256","build","case_file_sha256","seed","workers_per_case","provider"):
        if conditions[0][field] != conditions[1][field]:
            raise ValueError(f"Comparison conditions differ at {field}")
    if conditions[0]["case_file_sha256"] != sha256(cases_path.read_bytes()).hexdigest():
        raise ValueError("Case file differs from recorded conditions")
    out = root / "review"
    packet_dir = out / "packets"
    packet_dir.mkdir(parents=True, exist_ok=True)
    key = {}
    articles = []
    for case in cases:
        for workflow in ("WF-03","WF-13"):
            pair = []
            for arm in ("legacy","projected"):
                folder = root / arm / case["id"] / workflow
                record = json.loads((folder/"result.json").read_text(encoding="utf8"))
                assert record["arm"] == arm and record["case"] == case["id"] and record["workflow"].startswith(workflow + "/")
                pid = sha256(("AMC-C3-" + record["run_id"]).encode()).hexdigest()[:12]
                assert pid not in key
                draft = record.get("deliverable")
                body = draft["title"] + "\n\n" + draft["body"] if draft else "(Không có bản giao)"
                file = packet_dir / (pid + ".md")
                file.write_text(f"# {pid} · {case['id']} · {workflow}\n\n" + body + "\n", encoding="utf8")
                key[pid] = {"case":case["id"],"release":record["workflow"],"arm":arm,
                            "run":record["run_id"],"packet_sha256":sha256(file.read_bytes()).hexdigest()}
                title = "Workflow cũ" if arm == "legacy" else "Workflow dùng hồ sơ C3"
                usage = f'{record["input_tokens"]} token vào · {record["output_tokens"]} token ra · {record["runtime_s"]} giây'
                safe_body = "".join("<p>" + escape(block).replace("\n", "<br>") + "</p>" for block in body.split("\n\n"))
                fingerprint = escape(draft["digest"]) if draft else "Chưa có bản giao"
                pair.append(f"<section><h3>{title}</h3><small>{escape(usage)}</small>{safe_body}<footer>SHA-256 <code>{fingerprint}</code></footer></section>")
            label = escape(case["company"] + " · " + workflow)
            anchor = escape(case["id"] + "-" + workflow)
            articles.append((anchor,label,f'<article id="{anchor}"><h2>{label}</h2><div class="pair">'+"".join(pair)+"</div></article>"))
    (out/"key.json").write_text(json.dumps(key,indent=2)+"\n",encoding="utf8")
    nav = " ".join(f'<a href="#{anchor}">{label}</a>' for anchor,label,_ in articles)
    css = """body{font:16px/1.6 system-ui,sans-serif;color:#172922;background:#f6f7f2;max-width:108rem;margin:auto;padding:clamp(1rem,3vw,3rem)}
h1,h2,h3{line-height:1.2}h1{font-size:clamp(2rem,4vw,3.5rem)}h2{margin-top:3rem}a{color:#205b48}
nav{display:flex;flex-wrap:wrap;gap:0.4rem 1.3rem}nav a{padding:.35rem 0}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}
section{padding:1.25rem;background:white;border:1px solid #bac8bf;border-radius:.6rem}small,footer{color:#45594d}footer{border-top:1px solid #cad3cd;padding-top:.75rem}code{overflow-wrap:anywhere}
@media(max-width:52rem){.pair{grid-template-columns:1fr}}@media print{nav{display:none}body{background:white;padding:0}article{break-before:page}}"""
    document = ('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>AMC · Bản giao Marketing</title><style>'+css+'</style><main><h1>Bản giao Marketing</h1>'
                '<p>Hai phiên bản của mỗi workflow dùng cùng hồ sơ tổng hợp. Nội dung dưới đây được đọc từ bản giao do API trả về. '
                'Số token và thời gian tính cho cả workflow. Các tài sản đang được đánh giá nội bộ.</p><nav aria-label="Chọn ca">'+nav+
                '</nav>'+''.join(html for _,_,html in articles)+'</main></html>')
    (out/"BAN-GIAO-MARKETING.html").write_text(document,encoding="utf8")
    return len(key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    print("Review packets:", write_packet(parser.parse_args().root))
