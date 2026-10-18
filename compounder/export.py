"""Export one order as a single self-contained HTML report (and PDF).

  python -m compounder.export            # writes docs/samples/*.html and *.pdf for all orders

The HTML draws the evidence graph with viz.js. When Playwright is available,
the page is rendered once, the finished SVG is inlined and the script removed,
so the saved HTML works offline, and a PDF is printed from it.
"""
import html
import re
from pathlib import Path

from compounder import db
from compounder import queries as Q
from compounder.report import order_report
from compounder.viz import COLORS, order_dot

VIZ_JS = "https://cdn.jsdelivr.net/npm/@viz-js/viz@3.30.0/dist/viz-global.js"
OUT = Path(__file__).resolve().parents[1] / "docs" / "samples"

CSS = """
:root { --ink:#1f2328; --muted:#59636e; --line:#d1d9e0; --bg:#ffffff; --soft:#f6f8fa;
        --block:#d1242f; --warn:#9a6700; --info:#0969da; --ok:#1a7f37; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:14px/1.5 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 32px 24px 48px; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 17px; margin: 28px 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }
.sub { color: var(--muted); margin: 0 0 8px; }
.tag { display:inline-block; font-size:12px; padding:1px 8px; border-radius:10px; background:var(--soft); border:1px solid var(--line); margin-right:6px; }
.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.card { border:1px solid var(--line); border-radius:8px; padding:10px 12px; background:var(--soft); }
.card .k { font-size:12px; color:var(--muted); } .card .v { font-size:20px; font-weight:600; }
.label { border-left: 4px solid var(--ok); background:#dafbe1; padding:10px 12px; border-radius:6px; margin: 12px 0; }
pre { white-space: pre-wrap; background: var(--soft); border:1px solid var(--line); border-radius:6px; padding:12px; font:12.5px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; }
ul, ol { margin: 6px 0 6px 20px; padding: 0; } li { margin: 2px 0; }
.f { border-left: 4px solid; padding: 8px 12px; border-radius:6px; margin: 8px 0; background: var(--soft); }
.f.block { border-color: var(--block); } .f.warn { border-color: var(--warn); } .f.info { border-color: var(--info); }
.f b.block { color: var(--block); } .f b.warn { color: var(--warn); } .f b.info { color: var(--info); }
.f code { font-size:12px; color: var(--muted); }
.graph { border:1px solid var(--line); border-radius:8px; padding:8px; overflow-x:auto; }
.graph svg { max-width: 100%; height: auto; }
.legend span { margin-right: 10px; font-size: 12px; }
.trace div { margin: 6px 0; } .muted { color: var(--muted); font-size: 12px; }
.two { display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 720px) { .two { grid-template-columns: 1fr; } main { padding: 20px 16px; } }
@media print { main { padding: 0; } h2 { break-after: avoid; } .f, .card, pre, .graph { break-inside: avoid; } }
"""


def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def _list(items, ordered=False) -> str:
    if not items:
        return "<p class='muted'>None.</p>"
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{_e(i)}</li>" for i in items) + f"</{tag}>"


def html_report(order_id: str) -> str:
    rep = order_report(order_id)
    p, d, rx, f, doc, cov = (rep["patient"], rep["drug"], rep["rx"], rep["formulation"],
                             rep["prescriber"], rep.get("coverage") or {})
    if not p:
        return (f"<!doctype html><html><head><meta charset='utf-8'><title>Order {_e(order_id)}</title></head>"
                f"<body><p>Order {_e(order_id)} is not resolved yet ({_e(rep['order'].get('status'))}). "
                "No report is available.</p></body></html>")
    prof = db.run(Q.PATIENT_PROFILE, {"patient_id": p["id"]})[0]
    conditions = [c["name"] for c in prof["conditions"] if c.get("name")]
    dose = f"{rx.get('dose_mg'):g} mg" if rx.get("dose_mg") is not None else f"{rx.get('concentration_pct'):g}%"
    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
           f"<title>{_e(d.get('name'))} for {_e(p.get('name'))} · Compounder</title><style>{CSS}</style></head><body><main>"]

    out.append(f"<h1>{_e(d.get('name'))} for {_e(p.get('name'))}</h1>"
               f"<p class='sub'>Order {_e(order_id)} · {_e(rep['order'].get('status'))} · prescribed by {_e(doc.get('name'))}</p>"
               f"<p><span class='tag'>Rx: {_e(dose)}, {_e(rx.get('frequency_per_day'))}×/day, {_e(rx.get('duration_days'))} days, {_e(rx.get('route'))}</span>"
               f"<span class='tag'>{_e(p.get('age_years'))} y · {_e(p.get('weight_kg'))} kg</span>"
               + (f"<span class='tag'>{_e(cov.get('plan'))}</span>" if cov else "") + "</p>")
    out.append("<div class='two'><div><b>Conditions</b>" + _list(conditions) + "</div><div><b>Allergies / avoids</b>"
               + _list(prof["allergies"] + prof["avoids"]) + "<b>Current medicines</b>" + _list(prof["meds"]) + "</div></div>")

    if f:
        out.append("<h2>Proposed formulation</h2><div class='grid'>"
                   f"<div class='card'><div class='k'>Strength</div><div class='v'>{_e(f['concentration'])}</div></div>"
                   f"<div class='card'><div class='k'>Make</div><div class='v'>{_e(f['quantity'])} {_e(f['quantity_unit'])}</div></div>"
                   f"<div class='card'><div class='k'>Beyond-use date</div><div class='v'>{_e(f['bud_days'])} days</div></div></div>"
                   f"<p><b>{_e(f['form'])}</b> in <b>{_e(f['base'])}</b> · {_e(f['dose_text'])}</p>"
                   f"<div class='label'><b>Label:</b> {_e(f['directions'])}</div>"
                   f"<p class='muted'>Beyond-use date source: {_e(f['bud_source'])}</p>")
        if f.get("excluded"):
            out.append("<b>Bases ruled out</b>" + _list(f["excluded"]))

    if cov:
        out.append(f"<h2>Insurance coverage</h2><p class='sub'>{_e(cov.get('plan'))} · member {_e(cov.get('member_id'))} · synthetic demo plan</p>")
        if cov.get("route") != "none":
            out.append("<div class='grid'>"
                       f"<div class='card'><div class='k'>Recommended</div><div class='v'>{_e(cov['recommended'])}</div></div>"
                       f"<div class='card'><div class='k'>Patient copay</div><div class='v'>"
                       f"{'$' + format(cov['copay_usd'], 'g') if cov.get('copay_usd') is not None else '?'}</div></div>"
                       f"<div class='card'><div class='k'>Prior authorization</div><div class='v'>{'Needed' if cov.get('prior_auth') else 'Not needed'}</div></div></div>")
        out.append("<b>Covered options</b>" + _list(cov.get("options")) + "<b>Denied or unsuitable</b>" + _list(cov.get("denied")))
        if cov.get("prescriber_message"):
            out.append(f"<b>Message to prescriber</b><pre>{_e(cov['prescriber_message'])}</pre>")
        if cov.get("pa_request"):
            out.append(f"<b>Prior authorization request</b><pre>{_e(cov['pa_request'])}</pre>")

    if f and f.get("procedure"):
        out.append("<h2>Compounding procedure</h2><div class='two'><div><b>Ingredients</b>" + _list(f.get("ingredients"))
                   + "</div><div><b>Equipment</b>" + _list(f.get("equipment")) + "</div></div>"
                   + "<b>Steps</b>" + _list(f["procedure"], ordered=True)
                   + "<div class='two'><div><b>Quality checks</b>" + _list(f.get("qc")) + "</div><div><b>Label text</b>"
                   + _list(f.get("label_text")) + "</div></div>"
                   + "<p class='muted'>Demo only. A licensed pharmacist must verify every step.</p>")

    out.append("<h2>Safety findings</h2>")
    for x in rep["findings"]:
        ev = "".join(f"<br><code>{_e(e)}</code>" for e in (x.get("evidence") or [])[:5])
        out.append(f"<div class='f {_e(x['severity'])}'><b class='{_e(x['severity'])}'>{_e(x['severity']).upper()} · "
                   f"{_e(x['category'])}</b> — {_e(x['message'])}{ev}</div>")

    legend = "".join(f"<span><span style='color:{c}'>■</span> {'Excluded base' if k == 'Excluded' else k}</span>"
                     for k, c in COLORS.items())
    out.append("<h2>Evidence graph</h2><p class='muted'>What the agents looked at in FalkorDB.</p>"
               f"<div class='graph' id='graph'></div><p class='legend'>{legend}</p>"
               f"<script type='text/plain' id='dot'>{order_dot(order_id).replace('</', '<' + chr(92) + '/')}</script>")

    out.append("<h2>Agent trace</h2><div class='trace'>" + "".join(
        f"<div><b>{_e(s['agent'])}</b> · <i>{_e(s['action'])}</i><br>{_e(s['summary'])}</div>" for s in rep["steps"]) + "</div>")
    out.append("<p class='muted' style='margin-top:32px'>Generated by Compounder (FalkorDB + agents). Demo only, not for "
               "clinical use. All patients and insurance plans are synthetic.</p></main>")
    out.append(f"<script src='{VIZ_JS}' id='vizjs'></script><script id='vizrun'>"
               "Viz.instance().then(v=>{const dot=document.getElementById('dot').textContent;"
               "document.getElementById('graph').appendChild(v.renderSVGElement(dot));"
               "document.body.dataset.ready='1';});</script></body></html>")
    return "".join(out)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def export_all(pdf: bool = True) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    orders = db.run(Q.LIST_ORDERS)
    pages = []
    for o in orders:
        if not o["patient"]:
            continue
        name = _slug(f"{o['patient']}-{o['drug']}")
        path = OUT / f"{name}.html"
        path.write_text(html_report(o["order_id"]))
        pages.append(path)
    if pdf:
        _render(pages)
    return pages


def _viz_source() -> bytes:
    """viz.js fetched once by Python (respects proxy settings), served to the browser locally."""
    import urllib.request
    cache = OUT.parent / ".viz-standalone.js"
    if not cache.exists():
        with urllib.request.urlopen(VIZ_JS, timeout=60) as r:
            cache.write_bytes(r.read())
    return cache.read_bytes()


def _render(pages: list[Path]):
    """Inline the rendered SVG (offline HTML) and print a PDF of each page."""
    import os
    from playwright.sync_api import sync_playwright
    exe = "/opt/pw-browsers/chromium" if os.path.isfile("/opt/pw-browsers/chromium") else None
    viz = _viz_source()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=exe)
        page = browser.new_page(viewport={"width": 1100, "height": 1400})
        page.route(VIZ_JS, lambda route: route.fulfill(body=viz, content_type="application/javascript"))
        for path in pages:
            page.goto(path.as_uri())
            page.wait_for_selector("body[data-ready='1']", state="attached", timeout=30000)
            page.evaluate("for (const id of ['vizjs','vizrun','dot']) document.getElementById(id)?.remove()")
            path.write_text("<!doctype html>" + page.evaluate("document.documentElement.outerHTML"))
            page.pdf(path=str(path.with_suffix(".pdf")), format="A4", print_background=True,
                     margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"})
        browser.close()


if __name__ == "__main__":
    for p in export_all():
        print(p.relative_to(OUT.parents[1]))
