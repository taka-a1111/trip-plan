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



def _nth_monday(y, m, n):
    d = datetime.date(y, m, 1)
    d += datetime.timedelta(days=(7 - d.weekday()) % 7)  # 最初の月曜
    return d + datetime.timedelta(days=7 * (n - 1))


def holidays(year):
    """日本の祝日（振替休日・国民の休日を含む）を date の集合で返す"""
    fixed = [(1, 1), (2, 11), (2, 23), (4, 29), (5, 3), (5, 4), (5, 5),
             (8, 11), (11, 3), (11, 23)]
    hs = {datetime.date(year, m, d) for m, d in fixed}
    hs.add(_nth_monday(year, 1, 2))    # 成人の日
    hs.add(_nth_monday(year, 7, 3))    # 海の日
    hs.add(_nth_monday(year, 9, 3))    # 敬老の日
    hs.add(_nth_monday(year, 10, 2))   # スポーツの日
    # 春分・秋分（1980〜2099年の近似式）
    hs.add(datetime.date(year, 3, int(20.8431 + 0.242194 * (year - 1980) - (year - 1980) // 4)))
    hs.add(datetime.date(year, 9, int(23.2488 + 0.242194 * (year - 1980) - (year - 1980) // 4)))
    # 振替休日：日曜と重なったら次の平日
    for d in sorted(hs):
        if d.weekday() == 6:
            n = d + datetime.timedelta(days=1)
            while n in hs:
                n += datetime.timedelta(days=1)
            hs.add(n)
    # 国民の休日：祝日に挟まれた平日
    for d in sorted(hs):
        n = d + datetime.timedelta(days=2)
        mid = d + datetime.timedelta(days=1)
        if n in hs and mid not in hs and mid.weekday() < 6:
            hs.add(mid)
    return hs

def gmap(q):
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q)


def pin(points, ref):
    """refはキー文字列 or {"key":..., "lb":"A"}"""
    if isinstance(ref, dict):
        p = points[ref["key"]]
        out = {"n": p["n"], "lat": p["lat"], "lon": p["lon"], "k": p["k"], "c": p.get("c", "")}
        if ref.get("lb"):
            out["lb"] = ref["lb"]
        return out
    p = points[ref]
    return {"n": p["n"], "lat": p["lat"], "lon": p["lon"], "k": p["k"], "c": p.get("c", "")}


def render_row(points, row, counter):
    if row["type"] == "move":
        badges = "".join('<span class="bdg %s">%s</span>' % (c, t) for c, t in row.get("badges", []))
        # 移動行は説明文を出さない（区間・距離・所要のみ）。
        # フライトなど予約番号・締切を残す行だけ "keep_note": true で例外にする。
        note = ('<div class="s-note">%s</div>' % row["note"]) if (row.get("note") and row.get("keep_note")) else ""
        plan = ('<span class="s-plan">%s</span>' % row["plan"]) if row.get("plan") else ""
        return ('<li class="spot-row is-move"><div class="s-rail">%s</div>'
                '<div class="s-node"><span class="mv-node"></span></div>'
                '<div class="spot-head"><span class="mv-name">%s</span>'
                '<span class="mv-dur">%s</span>%s</div>'
                '<div class="spot-body">%s</div></li>'
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
    return ('<li class="spot-row is-fold row-%s%s"><div class="s-rail">%s</div>'
            '<div class="s-node"><span class="spot-no %s cat-%s">%d</span></div>'
            '<div class="spot-head" role="button" tabindex="0"><span class="s-name">%s</span>'
            '<span class="s-meta">%s<span class="ctag cat-%s">%s</span></span>'
            '<span class="s-caret" aria-hidden="true"></span></div>'
            '<div class="spot-body">'
            '<div class="s-facts">%s%s</div>'
            '%s%s<div class="spot-links">%s</div></div></li>'
            % (row["cat"], main_cls, plan, no_cls, row["cat"], counter[0], name, star,
               row["cat"], row["cat_lbl"], time_html, badges, note_html, flds, links))


def build(name, tag):
    data = json.load(open(os.path.join(ROOT, "trips", name + ".json"), encoding="utf-8"))
    tpl = open(os.path.join(ROOT, "tools", "template.html"), encoding="utf-8").read()
    points = data["points"]

    def render_meals(meals, pinned=False, d=None):
        if not meals:
            return ""
        blocks = ""
        for g in meals:
            rows = ""
            for it in g["items"]:
                mid = "%s-%s-%s" % ((d or {}).get("id", ""), g.get("slot", ""), it["name"])
                rows += ('<tr data-mk="%s" data-shop="%s" data-q="%s" data-la="%s" data-lo="%s"><td class="mt-ck"><span class="mck"></span></td>'
                         '<th scope="row"><a class="fshop" href="%s" target="_blank" rel="noopener">%s</a></th>'
                         '<td class="mt-rv">%s</td><td class="mt-bg">%s</td>'
                         '<td class="mt-hr">%s</td><td class="mt-off">%s</td></tr>'
                         % (mid, it.get("br") or it["name"], it["q"], it.get("la", ""), it.get("lo", ""), gmap(it["q"]), it["name"], it.get("rv") or "—", it.get("bg") or "—",
                            it.get("hr") or "—", it.get("off") or "—"))
            sl = g.get("slot", "夜")
            lab_cls = "ml-l" if sl == "昼" else ("ml-s" if sl == "買い出し" else "ml-d")
            lab = "スー<br>パー" if sl == "買い出し" else sl
            col1 = {"昼": "昼の候補", "夜": "夜の候補", "買い出し": "スーパーの候補"}.get(sl, "候補")
            blocks += ('<div class="mslot"><span class="mlab %s">%s</span>'
                       '<div class="mtable-wrap"><table class="mtable"><thead><tr>'
                       '<th class="mt-ck"></th><th>%s</th><th>口コミ</th><th>予算（1人あたり）</th><th>営業時間</th><th>定休日</th>'
                       '</tr></thead><tbody>%s</tbody></table></div></div>' % (lab_cls, lab, col1, rows))
        return ('<div class="mwrap is-fold"><div class="mhead" role="button" tabindex="0">'
                '食事と買い出しの候補<span class="mhint">タップで開く</span>'
                '<span class="s-caret" aria-hidden="true"></span></div>'
                '<div class="meals">%s</div></div>' % blocks)

    sections, DM, has_meals, has_meal_pins = [], {}, False, False
    for i, d in enumerate(data["days"]):
        counter = [0]
        rows = "".join(render_row(points, r, counter) for r in d["rows"])
        pinned = any(isinstance(x, dict) and x.get("lb") for x in d["pins"])
        meals_html = render_meals(d.get("meals"), pinned, d)
        if pinned:
            has_meal_pins = True
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
        spots_q = [points[r["key"]]["q"] for r in d["rows"] if r["type"] != "move"]

        def _stay(day):
            """その日の宿泊地（最後のstay行）"""
            last = ""
            for r in day["rows"]:
                if r["type"] != "move" and points[r["key"]].get("k") == "stay":
                    last = points[r["key"]]["q"]
            return last

        home_q = "%s,%s" % (data["home"]["lat"], data["home"]["lon"])
        org = _stay(data["days"][i - 1]) if i > 0 else home_q
        dst = _stay(d) or home_q
        if not org:
            org = home_q
        route = ('<div class="rtwrap"><button class="rtbtn" type="button" data-org="%s" data-dst="%s" '
                 'data-sp="%s">この日の動きを地図で開く</button></div>'
                 % (org, dst, "|".join(spots_q)))
        sections.append(
            '<section class="day reveal" id="%s"><div class="day-line">'
            '<div class="day-date"><span class="dd">%s</span><span class="dw">%s</span></div>'
            '<span class="day-badge">%s</span><div class="day-tags">%s</div></div>'
            '<h2 class="day-theme">%s</h2>%s%s'
            '<ul class="spot-list%s">%s</ul>'
            '<div class="daymap" id="daymap%d"></div>%s%s</section>'
            % (d["id"], d["dd"], d["dw"], d["badge"], tags, d["theme"], photo, notice,
               ("" if any(r.get("plan") for r in d["rows"]) else " np"), rows, i, meals_html, route))
        DM[str(i)] = [pin(points, k) for k in d["pins"]]

    memo = ('<div class="notice" id="memo" style="margin-top:22px">%s</div>' % data["memo"]) if data.get("memo") else ""
    rain = ""
    if data.get("rain"):
        cards = ""
        for i, x in enumerate(data["rain"], 1):
            rows_ = ''
            for lab, val in (("料金", x.get("fee")), ("", x.get("fam")), ("", x.get("park")),
                             ("営業", x.get("hr")), ("定休", x.get("off"))):
                if val:
                    rows_ += ('<div class="rfld"><span class="rk">%s</span><span class="rv">%s</span></div>'
                              % (lab, val))
            cards += ('<li class="rain-item"><span class="rno">%d</span><div class="rbody">'
                      '<a class="rname" href="%s" target="_blank" rel="noopener">%s</a>'
                      '<div class="rmeta">%s</div><div class="rnote">%s</div>'
                      '<div class="rfields">%s</div></div></li>'
                      % (i, gmap(x["q"]), x["n"], x.get("rv", ""), x.get("note", ""), rows_))
        rain = ('<section class="rain reveal" id="rain"><h2 class="rain-h">雨の日の候補</h2>'
                '<p class="rain-lead">名古屋から東尋坊までの間にある室内施設。'
                'その日の朝に雨なら、行き先をここへ振り替える。</p>'
                '<div class="daymap" id="daymaprain"></div>'
                '<ul class="rain-list">%s</ul></section>' % cards)
        DM["rain"] = [{"n": x["n"], "lat": x["la"], "lon": x["lo"], "k": "spot", "c": "play"}
                      for x in data["rain"]]
    main = "".join(sections) + memo + rain

    home = dict(data["home"], k="home")
    RT = {"pts": [home] + [pin(points, k) for k in data["rt_order"]],
          "days": [DM[str(i)] for i in range(len(data["days"]))]}
    wps = "|".join("%s,%s" % (points[k]["lat"], points[k]["lon"]) for k in data["visit_order"])
    dirlink = ("https://www.google.com/maps/dir/?api=1&origin={la},{lo}&destination={la},{lo}"
               "&travelmode=driving&waypoints={w}").format(la=home["lat"], lo=home["lon"], w=wps)

    nav = "".join('<a href="#%s">%s</a>' % (d["id"], d["badge"]) for d in data["days"])
    hs = holidays(int(data["date_s"][:4]))

    def dwcls(dd, dw):
        m, dy = [int(x) for x in dd.split("/")]
        dt = datetime.date(int(data["date_s"][:4]), m, dy)
        if dt in hs or dt.weekday() == 6:
            return " dw-sun"
        if dt.weekday() == 5:
            return " dw-sat"
        return ""

    daybar = "".join('<a href="#%s" data-day="%s">%s<small class="dwm%s">%s</small></a>'
                     % (d["id"], d["id"], d["dd"], dwcls(d["dd"], d["dw"]), d["dw"])
                     for d in data["days"])
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
    norm = {}
    for d_ in data["days"]:
        if d_.get("wxn"):
            norm["%s-%s" % (year, _iso(d_["dd"]))] = d_["wxn"]
    norm_js = json.dumps(norm, ensure_ascii=False)

    def _stay_q(day):
        last = ""
        for r in day["rows"]:
            if r["type"] != "move" and points[r["key"]].get("k") == "stay":
                last = points[r["key"]]["q"]
        return last

    home_q = "%s,%s" % (data["home"]["lat"], data["home"]["lon"])
    nav_stays = json.dumps(
        [{"d": "%s-%s" % (year, _iso(x["dd"])), "q": _stay_q(x) or home_q} for x in data["days"]],
        ensure_ascii=False)
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

    # ヘッダーに出す旅名と日付（h1_topの先頭語を旅名として使う。nav_titleがあればそちら）
    nav_title = data.get("nav_title") or data["h1_top"].split(" ")[0].split("\u3000")[0]
    def _md(iso):
        y, m, dd = iso.split("-")
        return "%d/%d" % (int(m), int(dd))
    nav_dates = "%s \u2013 %s" % (_md(data["date_s"]), _md(data["date_e"]))

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
        "{{NAV_TITLE}}": nav_title, "{{NAV_DATES}}": nav_dates,
        "{{WX_LAT}}": ",".join(lats), "{{WX_LON}}": ",".join(lons),
        "{{LEGEND_EXTRA}}": ('<span class="lg lg-pin"><span class="mno" style="width:16px;height:16px;font-size:.62rem">A</span>食事の候補</span>' if has_meal_pins else ""), "{{DAY_BAR}}": daybar, "{{WEAR}}": wear_html, "{{TRIP_KEY}}": data["name"], "{{DIRLINK}}": dirlink, "{{MAIN}}": main,
        "{{RT}}": json.dumps(RT, ensure_ascii=False),
        "{{DM}}": json.dumps(DM, ensure_ascii=False),
        "{{WX_DAYS}}": wxdays, "{{WX_PAST}}": past_js, "{{WX_NORM}}": norm_js, "{{NAV_STAYS}}": nav_stays, "{{CREDIT}}": credit,
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
