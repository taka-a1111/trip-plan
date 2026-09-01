# -*- coding: utf-8 -*-
"""ドラぷら（NEXCO）から高速料金を取得する
使い方: python3 tools/toll.py 出発IC 到着IC [経由IC ...]
出力: 通常料金 / ETC料金 / 距離 / 所要
"""
import sys, re, time, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def fetch(dep, arr, via=None):
    q = [("startPlaceKana", dep), ("arrivePlaceKana", arr)]
    if via:
        q.append(("keiyuPlaceKana", via))
    url = "https://www.driveplaza.com/dp/SearchQuick?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")

def parse(html):
    m = re.search(r'<!--ルートi-->(.*?)</tr>', html, re.S)
    if not m:
        return None
    seg = m.group(1)
    yen = [int(x.replace(",", "")) for x in re.findall(r'<em>([\d,]+)</em>円', seg)]
    km = re.search(r'<em>([\d.]+)</em>km', seg)
    tm = re.findall(r'<em>(\d+)</em>時間<em>(\d+)</em>分', seg)
    return {
        "normal": yen[0] if yen else None,
        "etc": yen[1] if len(yen) > 1 else None,
        "km": float(km.group(1)) if km else None,
        "time": ("%s時間%s分" % tm[0]) if tm else None,
    }

if __name__ == "__main__":
    dep, arr = sys.argv[1], sys.argv[2]
    via = sys.argv[3] if len(sys.argv) > 3 else None
    r = parse(fetch(dep, arr, via))
    print(dep, "→", arr, r)
