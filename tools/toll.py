# -*- coding: utf-8 -*-
"""高速料金をドラぷらで調べる。
使い方:
  python3 tools/toll.py 出発IC 到着IC [YYYY-MM-DD] [HH]
日付を渡すとその日の料金で検索するので、休日割引などのETC割引が反映される。
日付を省略すると当日の料金になる（＝割引の判定ができないので、旅程に使うときは必ず日付を渡す）。
2026年度は3連休・GW・お盆・SW・年末年始が休日割引の適用除外日。
"""
import sys, re, html, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")


def fetch(dep, arr, ymd=None, hh="9", via=None):
    q = [("startPlaceKana", dep), ("arrivePlaceKana", arr),
         ("carType", "1"), ("priority", "3"), ("kind", "1")]
    if via:
        q.append(("keiyuPlaceKana", via))
    if ymd:
        y, m, d = ymd.split("-")
        q += [("searchYear", y), ("searchMonth", str(int(m))), ("searchDay", str(int(d))),
              ("searchHour", str(int(hh))), ("searchMinute", "0")]
    u = "https://www.driveplaza.com/dp/SearchQuick?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")


def parse(h):
    i = h.find("通常料金")
    if i < 0:
        return None, []
    t = html.unescape(re.sub(r"<[^>]+>", "|", h[max(0, i - 900):i + 3000]))
    t = re.sub(r"\|[\s\r\n]*", "|", t)
    dm = re.search(r"(\d{4}年\d{2}月\d{2}日)\|+(\d{2}:\d{2})", t)
    routes = []
    for m in re.finditer(r"ルート\|(\d)\|+([\d,]+)\|円\|+([\d,]+)\|円\|+([\d,]+)\|円\|+"
                         r"([^|]*)\|+([^|]*)\|+([\d.]+)km", t):
        routes.append({"no": int(m.group(1)),
                       "normal": int(m.group(2).replace(",", "")),
                       "etc": int(m.group(3).replace(",", "")),
                       "etc2": int(m.group(4).replace(",", "")),
                       "time": m.group(5), "km": float(m.group(7))})
    return (dm.group(1) + " " + dm.group(2)) if dm else None, routes


if __name__ == "__main__":
    dep, arr = sys.argv[1], sys.argv[2]
    ymd = sys.argv[3] if len(sys.argv) > 3 else None
    hh = sys.argv[4] if len(sys.argv) > 4 else "9"
    when, routes = parse(fetch(dep, arr, ymd, hh))
    print("%s → %s  %s" % (dep, arr, when or "（当日）"))
    if not routes:
        print("  取得できませんでした")
    for r in routes:
        mark = "  ←最安" if r["etc"] == min(x["etc"] for x in routes) else ""
        print("  ルート%d  通常%s円  ETC%s円  %.1fkm  %s%s"
              % (r["no"], format(r["normal"], ","), format(r["etc"], ","),
                 r["km"], r["time"], mark))
