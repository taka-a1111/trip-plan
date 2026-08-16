# 旅のしおり ビルドシステム

## 仕組み

- `tools/template.html` … 全しおり共通のテンプレート（CSS・天気ウィジェット・地図JS・LINE対策・PWA登録を含む）
- `trips/<旅名>.json` … 旅ごとのデータ（タイトル・日程・スポット・座標・営業バッジ・注意書き）
- `assets/hero_<旅名>.jpg` … ヒーロー写真（権利クリアのもの。ビルド時にbase64で埋め込まれる）
- `tools/build.py` … JSON＋テンプレート → `<旅名>.html` を生成
- `tools/qa.py` … 生成物を 1000/430/380px で検査（横スクロール・地図・JSエラー）

## 新しい旅を作る

1. `trips/kiso.json` をコピーして中身を書き換える
2. ヒーロー写真を `assets/` に置く（1440px幅・JPEG品質60程度に圧縮）
3. ビルドとQA:

```
python3 tools/build.py <旅名> <BUILD_TAG>
python3 tools/qa.py <旅名>.html
```

4. `index.html` の `var trips=[...]` に新しい旅の行を追加（name / s / e / a / color / thumb）
5. 生成された `<旅名>.html` と `index.html` をコミット → Vercelが自動デプロイ

## 共通部分を直したいとき

`tools/template.html` を修正 → 各旅を `build.py` で再生成すれば全ページに反映される。
（過去の旅 okinawa.html / wakayama.html はテンプレート化前の手作りページなので対象外・アーカイブ扱い）

## PWA

- `manifest.json` / `sw.js` / `icons/` でホーム画面追加とオフライン表示に対応
- Service Worker はHTMLをネット優先（更新が最優先）、圏外時のみキャッシュ表示
- 天気API（Open-Meteo / 気象庁）はキャッシュしない（古い天気を出さないため）
- `sw.js` の `CORE` に新しい旅のHTMLを追加すると、初回アクセス時から圏外対応になる

## BUILD_TAG

`YYYY-MM-DD` ＋ 英小文字（同日2回目は b, c …）。`<head>` のコメントと `console.log` に入る。
デプロイ後はハードリフレッシュしてタグを確認する。
