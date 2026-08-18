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


def pin(points, ref):
    """refはキー文字列 or {"key":..., "lb":"A"}"""
    if isinstance(ref, dict):
        p = points[ref["key"]]
        out = {"n": p["n"], "lat": p["lat"], "lon": p["lon"], "k": p["k"]}
        if ref.get("lb"):
            out["lb"] = ref["lb"]
        return out
    p = points[ref]
    return {"n": p["n"], "lat": p["lat"], "lon": p["lon"], "k": p["k"]}


def render_row(points, row, counter):
    if row["type"] == "move":
        badges = "".join('<span class="bdg %s">%s</span>' % (c, t) for c, t in row.get("badges", []))
        note = ('<div class="s-note">%s</div>' % row["note"]) if row.get("note") else ""
        return ('<li class="spot-row"><div class="spot-main"><div class="spot-meta">'
                '<span class="ctag cat-move">移動</span><span class="s-name">%s</span>'
                '<span class="bdg b-move">%s</span>%s</div>%s</div></li>'
                % (row["name"], row["dur"], badges, note))
    p = points[row["key"]]
    counter[0] += 1
    no_cls = "sn-stay" if p["k"] == "stay" else "sn-spot"
    badges = "".join('<span class="bdg %s">%s</span>' % (c, t) for c, t in row.get("badges", []))
    time_html = ('<span class="s-time">%s</span>' % row["time"]) if row.get("time") else ""
    links = '<a class="lnk" href="%s" target="_blank" rel="noopener">地図</a>' % gmap(p["q"])
    if p.get("official"):
        links += '<a class="lnk lnk-of" href="%s" target="_blank" rel="noopener">公式</a>' % p["official"]
    if p.get("reserve"):
        links += '<a class="lnk lnk-rsv" href="%s" target="_blank" rel="noopener">予約</a>' % p["reserve"]
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

    def render_meals(meals):
        if not meals:
            return ""
        groups = ""
        for g in meals:
            items = ""
            for it in g["items"]:
                items += ('<li><div class="mtop"><span class="mno">%s</span>'
                          '<a class="mname" href="%s" target="_blank" rel="noopener">%s</a></div>'
                          '<span class="mmeta">%s</span></li>'
                          % (it["lb"], gmap(it["q"]), it["name"], it.get("meta", "")))
            lab_cls = "ml-l" if g.get("slot") == "昼" else "ml-d"
            groups += ('<div class="meal"><span class="mlab %s">%s</span>'
                       '<ul class="mlist">%s</ul></div>' % (lab_cls, g.get("slot", "夜"), items))
        return ('<div class="mhead">食事の候補<span class="mhint">A・B… は地図のオレンジのピン</span></div>'
                '<div class="meals">%s</div>' % groups)

    sections, DM, has_meals = [], {}, False
    for i, d in enumerate(data["days"]):
        counter = [0]
        rows = "".join(render_row(points, r, counter) for r in d["rows"])
        meals_html = render_meals(d.get("meals"))
        cost = d.get("cost")
        cost_html = ""
        if cost:
            amt = cost.get("total")
            label = "この日の有料費"
            val = ("0円" if amt == 0 else "約{:,}円".format(amt)) if isinstance(amt, int) else str(amt)
            bd = ('<span class="dc-b">%s</span>' % cost["note"]) if cost.get("note") else ""
            cost_html = ('<div class="daycost"><span class="dc-l">%s</span>'
                         '<span class="dc-v">%s</span>%s</div>' % (label, val, bd))
        if d.get("meals"):
            has_meals = True
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
            '<ul class="spot-list">%s</ul>%s%s'
            '<div class="daymap" id="daymap%d"></div></section>'
            % (d["id"], d["dd"], d["dw"], d["badge"], tags, d["theme"], photo, notice, rows, meals_html, cost_html, i))
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
    day_wx = [dict(wx, **d_.get("wx", {})) for d_ in data["days"]]
    wxdays = "[" + ",".join(
        "{d:'%s-%s',la:%s,lo:%s,jma:'%s',tk:'%s',nm:'%s',ja:'%s',js:'%s'}"
        % (year, _iso(d_["dd"]), w["lat"], w["lon"], w["jma"], w["tk"], w["nm"],
           w.get("jarea", ""), w.get("jstn", ""))
        for d_, w in zip(data["days"], day_wx)) + "]"
    seen, lats, lons = set(), [], []
    for w in day_wx:
        key = (w["lat"], w["lon"])
        if key not in seen:
            seen.add(key)
            lats.append(str(w["lat"]))
            lons.append(str(w["lon"]))

    hero = base64.b64encode(open(os.path.join(ROOT, data["hero_image"]), "rb").read()).decode()
    nights = sum(1 for d in data["days"][:-1])
    spots = len(data["rt_order"])
    credit = ('<div style="font-size:.62rem;opacity:.55;margin:4px 0 8px">%s</div>' % data["credit"]) if data.get("credit") else ""

    costs = [(d.get("dd"), d.get("id"), (d.get("cost") or {}).get("total")) for d in data["days"]]
    nums = [c for _, _, c in costs if isinstance(c, int)]
    cost_total = sum(nums) if nums else None
    tr = data.get("transport") or {}
    tr_total = (tr.get("fuel", 0) + tr.get("toll", 0)) if tr else 0
    cost_summary = ""
    stat_cost = ""
    if cost_total is not None:
        chips = "".join(
            '<a class="cs-item" href="#%s"><span class="cs-d">%s</span>'
            '<span class="cs-v">%s</span></a>'
            % (i_, dd, ("0円" if c == 0 else "{:,}円".format(c)))
            for dd, i_, c in costs if isinstance(c, int))
        grand = cost_total + tr_total
        tr_html = ""
        if tr:
            tr_html = ('<div class="cs-row"><span class="cs-rl">交通費（概算）</span>'
                       '<span class="cs-rv">約{:,}円</span>'
                       '<span class="cs-rb">{}</span></div>').format(tr_total, tr.get("note", ""))
        cost_summary = ('<div class="costsum"><div class="costsum-in">'
                        '<h3>旅の費用<span class="cs-total">合計 約{grand:,}円</span>'
                        '<span class="cs-sub">＋食費</span></h3>'
                        '<div class="cs-row"><span class="cs-rl">施設利用料</span>'
                        '<span class="cs-rv">約{fac:,}円</span></div>'
                        '<div class="cs-list">{chips}</div>'
                        '{tr}'
                        '<div class="cs-note">家族4人分。入場料・入浴料と、ガソリン代・高速代（ETC通常料金の目安）の合計です。'
                        '<b>食費は含みません</b>（別途かかります）。日付をタップするとその日の内訳へ移動します。</div>'
                        '</div></div>').format(grand=grand, fac=cost_total, chips=chips, tr=tr_html)
        stat_cost = ('<div><div class="num">%s</div><div class="lbl">費用(円)</div></div>'
                     % "{:,}".format(grand))

    rep = {
        "{{TITLE}}": data["title"], "{{BUILD_TAG}}": tag, "{{HERO_B64}}": hero,
        "{{H1_TOP}}": data["h1_top"], "{{H1_SUB}}": data["h1_sub"],
        "{{DATES_LABEL}}": data["dates_label"],
        "{{STAT_DAYS}}": str(len(data["days"])), "{{STAT_NIGHTS}}": str(nights), "{{STAT_SPOTS}}": str(spots),
        "{{DATE_S}}": data["date_s"], "{{DATE_E}}": data["date_e"],
        "{{WX_LAT}}": ",".join(lats), "{{WX_LON}}": ",".join(lons),
        "{{LEGEND_EXTRA}}": ('<span class="lg lg-pin"><span class="mno" style="width:16px;height:16px;font-size:.62rem">A</span>食事の候補</span>' if has_meals else ""),
        "{{NAV_DAYS}}": nav, "{{COST_SUMMARY}}": cost_summary, "{{STAT_COST}}": stat_cost, "{{DIRLINK}}": dirlink, "{{MAIN}}": main,
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
