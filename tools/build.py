# -*- coding: utf-8 -*-
"""旅のしおりビルダー
使い方:  python3 tools/build.py kiso [BUILD_TAG]
  trips/kiso.json と tools/template.html から kiso.html を生成する。
  BUILD_TAG 省略時は今日の日付 + "a"。
"""
import base64
import datetime
import json
import os
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def gmap(q):
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q)


def pin(points, key):
    p = points[key]
    return {"n": p["n"], "lat": p["lat"], "lon": p["lon"], "k": p["k"]}


def render_row(points, row, counter):
    if row["type"] == "move":
        return ('<li class="spot-row"><div class="spot-main"><div class="spot-meta">'
                '<span class="ctag cat-move">移動</span><span class="s-name">%s</span>'
                '<span class="bdg b-move">%s</span></div></div></li>'
                % (row["name"], row["dur"]))
    p = points[row["key"]]
    counter[0] += 1
    no_cls = "sn-stay" if p["k"] == "stay" else "sn-spot"
    badges = "".join('<span class="bdg %s">%s</span>' % (c, t) for c, t in row.get("badges", []))
    time_html = ('<span class="s-time">%s</span>' % row["time"]) if row.get("time") else ""
    links = '<a class="lnk" href="%s" target="_blank" rel="noopener">地図</a>' % gmap(p["q"])
    if p.get("official"):
        links += '<a class="lnk lnk-of" href="%s" target="_blank" rel="noopener">公式</a>' % p["official"]
    name = row.get("name_override") or p["n"]
    return ('<li class="spot-row"><div class="spot-main"><div class="spot-meta">'
            '<span class="spot-no %s">%d</span><span class="ctag cat-%s">%s</span>'
            '<span class="s-name">%s</span>%s%s</div>'
            '<div class="s-note">%s</div></div>'
            '<div class="spot-links">%s</div></li>'
            % (no_cls, counter[0], row["cat"], row["cat_lbl"], name, time_html, badges, row["note"], links))


def build(name, tag):
    data = json.load(open(os.path.join(ROOT, "trips", name + ".json"), encoding="utf-8"))
    tpl = open(os.path.join(ROOT, "tools", "template.html"), encoding="utf-8").read()
    points = data["points"]

    sections, DM = [], {}
    for i, d in enumerate(data["days"]):
        counter = [0]
        rows = "".join(render_row(points, r, counter) for r in d["rows"])
        tags = "".join('<span class="day-tag %s">%s</span>' % (c, t) for c, t in d["tags"])
        notice = '<div class="notice">%s</div>' % d["notice"] if d.get("notice") else ""
        photo = ""
        if d.get("photo"):
            ph = d["photo"]
            b64 = base64.b64encode(open(os.path.join(ROOT, ph["file"]), "rb").read()).decode()
            cr = ('<span class="ph-credit">%s</span>' % ph["credit"]) if ph.get("credit") else ""
            photo = ('<div class="day-photo"><img src="data:image/jpeg;base64,%s" alt="%s" loading="lazy">%s</div>'
                     % (b64, ph.get("alt", ""), cr))
        sections.append(
            '<section class="day reveal" id="%s"><div class="day-line">'
            '<div class="day-date"><span class="dd">%s</span><span class="dw">%s</span></div>'
            '<span class="day-badge">%s</span><div class="day-tags">%s</div></div>'
            '<h2 class="day-theme">%s</h2>%s%s'
            '<ul class="spot-list">%s</ul>'
            '<div class="daymap" id="daymap%d"></div></section>'
            % (d["id"], d["dd"], d["dw"], d["badge"], tags, d["theme"], photo, notice, rows, i))
        DM[str(i)] = [pin(points, k) for k in d["pins"]]

    memo = ('<div class="notice" style="margin-top:22px">%s</div>' % data["memo"]) if data.get("memo") else ""
    main = "".join(sections) + memo

    home = dict(data["home"], k="home")
    RT = {"pts": [home] + [pin(points, k) for k in data["rt_order"]],
          "days": [DM[str(i)] for i in range(len(data["days"]))]}
    wps = "|".join("%s,%s" % (points[k]["lat"], points[k]["lon"]) for k in data["visit_order"])
    dirlink = ("https://www.google.com/maps/dir/?api=1&origin={la},{lo}&destination={la},{lo}"
               "&travelmode=driving&waypoints={w}").format(la=home["lat"], lo=home["lon"], w=wps)

    nav = "".join('<a href="#%s">%s</a>' % (d["id"], d["badge"]) for d in data["days"])
    wx = data["wx"]
    year = data["date_s"][:4]
    wxdays = "[" + ",".join(
        "{d:'%s-%s',la:%s,lo:%s,jma:'%s',tk:'%s',nm:'%s'}"
        % (year, _iso(d_["dd"]), wx["lat"], wx["lon"], wx["jma"], wx["tk"], wx["nm"])
        for d_ in data["days"]) + "]"

    hero = base64.b64encode(open(os.path.join(ROOT, data["hero_image"]), "rb").read()).decode()
    nights = sum(1 for d in data["days"][:-1])
    spots = len(data["rt_order"])
    credit = ('<div style="font-size:.62rem;opacity:.55;margin:4px 0 8px">%s</div>' % data["credit"]) if data.get("credit") else ""

    rep = {
        "{{TITLE}}": data["title"], "{{BUILD_TAG}}": tag, "{{HERO_B64}}": hero,
        "{{H1_TOP}}": data["h1_top"], "{{H1_SUB}}": data["h1_sub"],
        "{{DATES_LABEL}}": data["dates_label"],
        "{{STAT_DAYS}}": str(len(data["days"])), "{{STAT_NIGHTS}}": str(nights), "{{STAT_SPOTS}}": str(spots),
        "{{DATE_S}}": data["date_s"], "{{DATE_E}}": data["date_e"],
        "{{WX_LAT}}": str(wx["lat"]), "{{WX_LON}}": str(wx["lon"]),
        "{{NAV_DAYS}}": nav, "{{DIRLINK}}": dirlink, "{{MAIN}}": main,
        "{{RT}}": json.dumps(RT, ensure_ascii=False),
        "{{DM}}": json.dumps(DM, ensure_ascii=False),
        "{{WX_DAYS}}": wxdays, "{{CREDIT}}": credit,
    }
    h = tpl
    for k, v in rep.items():
        assert k in h, "placeholder missing in template: " + k
        h = h.replace(k, v)
    assert "{{" not in h, "unresolved placeholder remains"
    out = os.path.join(ROOT, name + ".html")
    open(out, "w", encoding="utf-8").write(h)
    print("wrote", out, len(h.encode("utf-8")), "bytes / BUILD_TAG:", tag)


def _iso(dd):
    """'8/20' -> '2026-08-20' は build() 内で year と結合するため月日部分のみ返す"""
    m, d = dd.split("/")
    return "%02d-%02d" % (int(m), int(d))


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "kiso"
    tag = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().strftime("%Y-%m-%d") + "a"
    build(name, tag)
