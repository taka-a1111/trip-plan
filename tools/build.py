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
        plan = ('<span class="s-plan">%s</span>' % row["plan"]) if row.get("plan") else ""
        return ('<li class="spot-row is-move"><div class="s-rail">%s</div>'
                '<div class="s-node"><span class="mv-node"></span></div>'
                '<div class="spot-main"><div class="mv-line">'
                '<span class="mv-name">%s</span><span class="mv-dur">%s</span>%s</div>%s</div></li>'
                % (plan, row["name"], row["dur"], badges, note))
    p = points[row["key"]]
    counter[0] += 1
    no_cls = "sn-stay" if p["k"] == "stay" else "sn-spot"
    badges = "".join('<span class="bdg %s">%s</span>' % (c, t) for c, t in row.get("badges", []))
    time_html = ('<span class="s-time">%s</span>' % row["time"]) if (row.get("time") and not row.get("fields")) else ""
    links = '<a class="lnk" href="%s" target="_blank" rel="noopener">地図</a>' % gmap(p["q"])
    if p.get("official"):
        links += '<a class="lnk lnk-of" href="%s" target="_blank" rel="noopener">公式</a>' % p["official"]
    if p.get("reserve"):
        links += '<a class="lnk lnk-rsv" href="%s" target="_blank" rel="noopener">予約</a>' % p["reserve"]
    name = row.get("name_override") or p["n"]
    plan = ('<span class="s-plan">%s</span>' % row["plan"]) if row.get("plan") else ""
    main_cls = " is-main" if row.get("main") else ""
    star = '<span class="s-star">今日の目玉</span>' if row.get("main") else ""

    def _fv(v):
        """値がリストなら実店舗（名前＋地図リンク＋ひとこと）として描画する"""
        if isinstance(v, list):
            return "".join(
                '<span class="fshop-row">'
                '<a class="fshop" href="%s" target="_blank" rel="noopener">%s</a>'
                '<span class="fshop-meta">%s</span></span>'
                % (gmap(x["q"]), x["name"], x.get("meta", "")) for x in v)
        return v

    flds = ""
    if row.get("fields"):
        flds = '<div class="s-fields">%s</div>' % "".join(
            '<div class="fld"><span class="fk">%s</span><span class="fv">%s</span></div>'
            % (k, _fv(v)) for k, v in row["fields"])
    note_html = ('<div class="s-note">%s</div>' % row["note"]) if row.get("note") else ""
    return ('<li class="spot-row%s"><div class="s-rail">%s</div>'
            '<div class="s-node"><span class="spot-no %s cat-%s">%d</span></div>'
            '<div class="spot-main">'
            '<div class="spot-meta"><span class="s-name">%s</span>%s</div>'
            '<div class="s-facts"><span class="ctag cat-%s">%s</span>%s%s</div>'
            '%s%s<div class="spot-links">%s</div></div></li>'
            % (main_cls, plan, no_cls, row["cat"], counter[0], name, star,
               row["cat"], row["cat_lbl"], time_html, badges, note_html, flds, links))


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
            '<span class="day-badge">%s</span><div class="day-tags">%s</div>'
            '<span class="day-caret" aria-hidden="true"></span></div>'
            '<h2 class="day-theme">%s</h2><div class="day-in">%s%s'
            '<ul class="spot-list%s">%s</ul>%s'
            '<div class="daymap" id="daymap%d"></div></div></section>'
            % (d["id"], d["dd"], d["dw"], d["badge"], tags, d["theme"], photo, notice,
               ("" if any(r.get("plan") for r in d["rows"]) else " np"), rows, meals_html, i))
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
    past = {}
    for d_ in data["days"]:
        if d_.get("wxp"):
            past["%s-%s" % (year, _iso(d_["dd"]))] = d_["wxp"]
    past_js = json.dumps(past, ensure_ascii=False)
    seen, lats, lons = set(), [], []
    for w in day_wx:
        key = (w["lat"], w["lon"])
        if key not in seen:
            seen.add(key)
            lats.append(str(w["lat"]))
            lons.append(str(w["lon"]))

    hero = base64.b64encode(open(os.path.join(ROOT, data["hero_image"]), "rb").read()).decode()
    nights = sum(1 for d in data["days"][:-1])
    spots = len([k for k in data["rt_order"]
                 if points[k].get("k") == "spot" and points[k].get("cat_hint") != "onsen"])
    onsen_keys = {r["key"] for d_ in data["days"] for r in d_["rows"]
                  if r.get("type") == "spot" and r.get("cat") == "onsen"}
    spots = len([k for k in data["rt_order"]
                 if points[k].get("k") == "spot" and k not in onsen_keys])
    credit = ('<div class="hero-credit">%s</div>' % data["credit"]) if data.get("credit") else ""

    wear = data.get("wear")
    wear_html = ""
    if wear:
        wear_html = ('<div class="wear">'
                     '<span class="w-item"><span class="w-lb">昼</span><span>%s</span></span>'
                     '<span class="w-item"><span class="w-lb">朝晩</span><span>%s</span></span>'
                     '</div>') % (wear.get("day", ""), wear.get("night", ""))

    rep = {
        "{{TITLE}}": data["title"], "{{BUILD_TAG}}": tag, "{{HERO_B64}}": hero,
        "{{H1_TOP}}": data["h1_top"], "{{H1_SUB}}": data["h1_sub"],
        "{{DATES_LABEL}}": data["dates_label"],
        "{{STAT_DAYS}}": str(len(data["days"])), "{{STAT_NIGHTS}}": str(nights), "{{STAT_SPOTS}}": str(spots),
        "{{DATE_S}}": data["date_s"], "{{DATE_E}}": data["date_e"],
        "{{WX_LAT}}": ",".join(lats), "{{WX_LON}}": ",".join(lons),
        "{{LEGEND_EXTRA}}": ('<span class="lg lg-pin"><span class="mno" style="width:16px;height:16px;font-size:.62rem">A</span>食事の候補</span>' if has_meals else ""),
        "{{NAV_DAYS}}": nav, "{{WEAR}}": wear_html, "{{TRIP_KEY}}": data["name"], "{{DIRLINK}}": dirlink, "{{MAIN}}": main,
        "{{RT}}": json.dumps(RT, ensure_ascii=False),
        "{{DM}}": json.dumps(DM, ensure_ascii=False),
        "{{WX_DAYS}}": wxdays, "{{WX_PAST}}": past_js, "{{CREDIT}}": credit,
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
