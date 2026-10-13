import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = json.load(open(os.path.join(ROOT, "trips", "hokkaido_fares.json"), encoding="utf-8"))
f = lambda n: format(n, ",")

GF = "https://www.google.com/travel/flights?q=Flights%%20from%%20%s%%20to%%20%s%%20on%%20%s%%20oneway&hl=ja&curr=JPY"
LEGS = {
 "12": [("行き", "12/12（土）", "中部 → 新千歳", "NGO-CTS-2026-12-12", "18:00"),
        ("帰り", "12/19（土）", "新千歳 → 中部", "CTS-NGO-2026-12-19", "15:30")],
 "19": [("行き", "12/19（土）", "中部 → 新千歳", "NGO-CTS-2026-12-19", "18:00"),
        ("帰り", "12/27（日）", "新千歳 → 中部", "CTS-NGO-2026-12-27", "10:35")],
}


def pick(key, dep):
    return next(r for r in F[key] if r["dep"] == dep)


def table(key, shiori_dep):
    rows = F[key]
    low = min(r["fam"] for r in rows)
    h = []
    for r in rows:
        tags = ""
        if r["dep"] == shiori_dep:
            tags += '<span class="tg tg-s">しおり</span>'
        if r["fam"] == low:
            tags += '<span class="tg tg-l">最安</span>'
        price = "%s円" % f(r["fam"])
        if r["kind"] == "child25":
            price = "約" + price
        sub = "大人%s円・子ども%s円" % (f(r["adult"]), f(r["child"])) if r["kind"] == "child25" else "1人%s円×4" % f(r["adult"])
        bag = '<span class="bag">＋荷物代</span>' if r["al"] == "Peach" else ""
        cls = ' class="hl"' if r["dep"] == shiori_dep else ""
        h.append('<tr%s><td class="tm">%s<span class="ar">→%s</span></td><td class="al">%s%s</td>'
                 '<td class="pr"><b>%s</b><span class="sub">%s</span>%s</td></tr>'
                 % (cls, r["dep"], r["arr"], r["al"], tags, price, sub, bag))
    return '<table><thead><tr><th>出発→到着</th><th>航空会社</th><th>4人合計</th></tr></thead><tbody>%s</tbody></table>' % "".join(h)


def plan(pid, title, page):
    legs = LEGS[pid]
    a = pick(legs[0][3], legs[0][4]); b = pick(legs[1][3], legs[1][4])
    out = ['<section class="plan"><h2>%s</h2>' % title,
           '<div class="sum"><div><span class="k">しおりの便で往復</span><span class="v">約%s円</span></div>'
           '<div class="d">行き %s %s %s発・帰り %s %s %s発</div>'
           '<a class="lk" href="./%s">このプランのしおりを開く →</a></div>'
           % (f(a["fam"] + b["fam"]), legs[0][1], a["al"], a["dep"], legs[1][1], b["al"], b["dep"], page)]
    for lab, day, route, key, dep in legs:
        o, d, dt = key.split("-", 2)
        out.append('<h3><span class="lb">%s</span>%s %s</h3>' % (lab, day, route))
        out.append(table(key, dep))
        out.append('<a class="gf" href="%s" target="_blank" rel="noopener">Googleフライトでこの日の便を見る</a>' % (GF % (o, d, dt)))
    out.append("</section>")
    return "".join(out)


html = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>北海道の飛行機｜旅のしおり</title>
<meta name="robots" content="noindex">
<style>
:root{--ink:#16282d;--paper:#f6f2ea;--card:#fffdf8;--line:#e3dccd;--teal:#0c7c8c;--navy:#2c5a86;--coral:#e8693f;--gold:#c39327;--slate:#62757b;--hl:#eaf2f8}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:"游ゴシック","Yu Gothic","メイリオ","Meiryo","Noto Sans JP","Noto Sans CJK JP",sans-serif;line-height:1.6;-webkit-text-size-adjust:100%}
.wrap{max-width:720px;margin:0 auto;padding:20px 16px 48px}
h1{font-size:1.35rem;margin:6px 0 4px;color:var(--navy)}
.lead{color:var(--slate);font-size:.88rem;margin:0 0 14px}
.note{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;font-size:.84rem;margin-bottom:22px}
.note ul{margin:0;padding-left:1.2em}.note li{margin:3px 0}
.plan{margin-top:26px}
h2{font-size:1.15rem;margin:0 0 10px;padding-left:10px;border-left:5px solid var(--navy)}
.sum{background:var(--navy);color:#fff;border-radius:14px;padding:14px 16px}
.sum .k{display:block;font-size:.8rem;opacity:.85}.sum .v{font-size:1.6rem;font-weight:800;letter-spacing:.02em}
.sum .d{font-size:.82rem;opacity:.92;margin-top:2px}
.sum .lk{display:inline-block;margin-top:8px;color:#fff;font-size:.82rem;font-weight:700}
h3{font-size:.98rem;margin:20px 0 8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.lb{background:var(--teal);color:#fff;font-size:.75rem;padding:2px 9px;border-radius:99px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:.86rem}
th{background:#efe6d6;font-size:.74rem;color:var(--slate);text-align:left;padding:6px 8px;font-weight:700}
td{border-top:1px solid var(--line);padding:8px;vertical-align:top}
tr.hl td{background:var(--hl)}
.tm{white-space:nowrap;font-weight:700;font-variant-numeric:tabular-nums}
.ar{display:block;font-weight:400;color:var(--slate);font-size:.78rem}
.al{word-break:keep-all;overflow-wrap:anywhere}
.pr{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.pr b{font-size:.95rem}
.sub{display:block;color:var(--slate);font-size:.7rem}
.bag{display:block;color:var(--coral);font-size:.7rem;font-weight:700}
.tg{display:inline-block;font-size:.66rem;font-weight:700;padding:0 6px;border-radius:99px;margin:2px 0 0 4px;vertical-align:1px}
.tg-s{background:var(--navy);color:#fff}.tg-l{background:var(--gold);color:#fff}
.gf{display:inline-block;margin-top:8px;font-size:.8rem;color:var(--teal);font-weight:700}
.links{margin-top:30px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;font-size:.85rem}
.links h2{border:0;padding:0;font-size:1rem}
.links a{color:var(--teal);font-weight:700}
.links li{margin:4px 0}
.foot{margin-top:24px;font-size:.78rem;color:var(--slate)}
</style></head><body><div class="wrap">
<h1>北海道の飛行機 便と料金</h1>
<p class="lead">中部（セントレア）⇔新千歳の直行便。大人2人・子ども2人（小学2年・年長）の4人で、片道ずつの合計額。12/19出発で決めた（10/13）。値段は12/19発が10月13日、12/12発が10月12日に調べたもので、予約するまで変わります。</p>
<div class="note"><ul>
<li>スカイマーク・ピーチは、割引運賃が大人も子どもも同じ額。</li>
<li>ANA・JAL・AIRDOは、2〜11歳の子どもが25%ほど安くなるので、その分を引いた「約」の額。正確な額は予約画面で人数を入れると出る。</li>
<li>ピーチは預け荷物が別料金（1個約1,950円から）。ほかは預け荷物20kgまで無料。</li>
<li>JALは行きも帰りもJALにすると、往復割引でさらに安くなることがある。</li>
<li><span class="tg tg-s">しおり</span>は今のしおりに入れている便、<span class="tg tg-l">最安</span>はその日いちばん安い便。</li>
</ul></div>
@@P19@@
@@P12@@
<div class="links"><h2>予約するところ</h2><ul>
<li><a href="https://www.skymark.co.jp/ja/" target="_blank" rel="noopener">スカイマーク</a></li>
<li><a href="https://www.flypeach.com/ja" target="_blank" rel="noopener">ピーチ</a></li>
<li><a href="https://www.ana.co.jp/" target="_blank" rel="noopener">ANA</a>（AIRDOの共同運航便もここで買える）</li>
<li><a href="https://www.jal.co.jp/" target="_blank" rel="noopener">JAL</a></li>
<li><a href="https://www.airdo.jp/" target="_blank" rel="noopener">AIRDO</a></li>
</ul></div>
<p class="foot"><a href="./index.html">旅のしおり トップへ</a></p>
</div></body></html>
""".replace("@@P12@@", plan("12", "参考：12/12発の案（12/12〜19）", "hokkaido12.html")).replace("@@P19@@", plan("19", "12/19発（決定）12/19〜27", "hokkaido.html"))

open(os.path.join(ROOT, "hokkaido-flights.html"), "w", encoding="utf-8").write(html)
print("ok")
