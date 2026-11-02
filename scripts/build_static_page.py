"""Write results/build_space/static/{index.html,README.md,pass_vs_level.png} from results/analyze. Free static Space bundle."""
import html
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "build_space" / "static"
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
shutil.copy(ROOT / "results/make_report/pass_vs_level_best.png", OUT / "pass_vs_level.png")
readme = (ROOT / "space/README.md").read_text()
body = readme.split("---", 2)[2]
t = pd.read_csv(ROOT / "results/analyze/table.csv")
cols = ["task", "model", "effort", "level", "runs", "pass_rate", "success", "api", "parity", "behavior", "rounds", "out_tokens"]
table = t[cols].to_html(index=False, border=0, classes="t")
# very small markdown to html: headings, bullets, tables and paragraphs from the README body
import re
lines, out, inlist, intable = body.strip().splitlines(), [], False, False
for ln in lines:
    if ln.startswith("# "):
        out.append(f"<h1>{html.escape(ln[2:])}</h1>")
    elif ln.startswith("## "):
        out.append(f"<h2>{html.escape(ln[3:])}</h2>")
    elif ln.startswith("* "):
        if not inlist:
            out.append("<ul>"); inlist = True
        out.append("<li>" + re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(ln[2:])) + "</li>")
    else:
        if inlist:
            out.append("</ul>"); inlist = False
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if set("".join(cells)) <= set("- "):
                continue
            if not intable:
                out.append("<table class='t'>"); intable = True; tag = "th"
            else:
                tag = "td"
            out.append("<tr>" + "".join(f"<{tag}>{re.sub(r'`([^`]+)`', r'<code>\1</code>', html.escape(c))}</{tag}>" for c in cells) + "</tr>")
            continue
        if intable:
            out.append("</table>"); intable = False
        if ln.strip():
            out.append("<p>" + re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(ln)) + "</p>")
if inlist: out.append("</ul>")
if intable: out.append("</table>")
PER_TASK = (ROOT / "results/make_report/per_task.html").read_text()
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Repo2Mini</title><style>
:root{{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#ddd}}@media(prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#eee;--mut:#aaa;--line:#333}}}}
body{{margin:0 auto;max-width:980px;padding:24px 16px;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}}
code{{background:rgba(127,127,127,.18);padding:1px 5px;border-radius:4px}}table.t{{border-collapse:collapse;width:100%;font-size:13px;display:block;overflow-x:auto}}
.t th,.t td{{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left;white-space:nowrap}}img{{max-width:100%}}
.m{{color:var(--mut)}}table.cmp{{border-collapse:collapse;width:100%;font-size:14px;margin:6px 0 22px}}.cmp th,.cmp td{{border:1px solid var(--line);padding:6px 10px;text-align:center}}.cmp thead th{{background:rgba(127,127,127,.12)}}.cmp tbody th{{text-align:left;font-weight:500;white-space:nowrap}}.cmp td span{{display:block;font-size:11px;color:var(--mut)}}.cmp td.best{{outline:2px solid #2a9d8f;outline-offset:-2px}}.cmp td.na{{color:var(--mut);font-size:12px}}h3{{margin:22px 0 4px}}</style></head><body>{''.join(out)}
<h2>Pass rate by context level</h2><p class="m">Each model is shown at its best variant: for every task and level, the reasoning effort with the highest mean pass rate. Only Beam was run at two efforts (low and medium, medium on 4 tasks), so this can only lift Beam slightly.</p><img src="pass_vs_level.png" alt="Best variant pass rate versus context level">
<h2>Models compared per task</h2><p class="m">Each cell is the mean hidden pass rate of the best variant, with the number of runs that passed every hidden test out of the runs. The best model in each row has a teal frame. Bug fix pools the two injected bug variants of the task.</p>{PER_TASK}
<p class="m">Data: <a href="https://huggingface.co/datasets/omkar334/repo2mini-results">omkar334/repo2mini-results</a></p></body></html>"""
(OUT / "index.html").write_text(page)
(OUT / "README.md").write_text("---\ntitle: Repo2Mini\nemoji: 🧩\ncolorFrom: indigo\ncolorTo: blue\nsdk: static\npinned: false\nlicense: apache-2.0\nshort_description: Does more repo context help Beam rebuild a library?\n---\n\nStatic results page for Repo2Mini. Open `index.html`.\n")
print("ok", len(page))
