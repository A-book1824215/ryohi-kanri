---
name: pre-deploy-check
description: 寮費管理システム(ryohi-kanri)で、残高計算・支払い処理・認証(auth.py, db.py)に関わるコードを変更した後、GitHubにpushして本番のStreamlit Cloudに反映する前に必ず使う。ローカルでStreamlitを起動し、実際の画面を見て動作確認してからpushする手順を型化したもの。「本番に反映して」「pushして」「デプロイして」「公開して」といった指示のとき、またはdb.py・auth.py・支払い確認.py・支払い入力.py・残高確認.py・月額管理.pyを変更したときに使う。
---

## なぜこれが必要か

このアプリは実在するスタッフの名前・支払い金額・残高を扱う本番システムです。
残高計算式（`stays（適用単価×泊数）の合計 − payments（金額）の合計`）や認証まわりにバグがあると、
実際の請求額を間違えたり、ログインできなくなったりする。コードを読んだだけでは気づきにくい種類のミス
（日付の境界条件、Noneのチェックアウト日、SQLの条件漏れなど）が多いので、画面を実際に動かして確認してから
本番に出す。

## 手順

1. **変更内容を確認する**
   `git diff` で差分を見て、金額計算・認証・DBスキーマに関わる変更かどうか判断する。
   影響が大きいファイル: `db.py`, `auth.py`, `pages/支払い確認.py`, `pages/支払い入力.py`,
   `pages/残高確認.py`, `pages/月額管理.py`, `pages/台帳出力.py`

2. **ローカルでStreamlitを起動する**
   Bashの`&`はシェル終了と同時にプロセスが死ぬので使わない。PowerShellで起動する:
   ```powershell
   Start-Process -WindowStyle Hidden -FilePath "python" -ArgumentList "-m","streamlit","run","app.py","--server.headless","true" -WorkingDirectory "C:\Users\user\iCloudDrive\dev\ryohi-kanri"
   ```
   数秒待ってから `http://localhost:8501` にアクセスする。

3. **Playwright MCPで画面を確認する**
   claude-in-chrome拡張はlocalhostへのアクセス権限がないため使えない。
   `mcp__plugin_playwright_playwright__browser_navigate` → `browser_snapshot` / `browser_take_screenshot` で確認する。
   - ログインが必要なら管理者パスワードでログイン
   - 変更したページを開き、数値・残高・一覧表示が正しいか目視確認
   - エラーメッセージやStreamlitの例外画面が出ていないか確認
   - 金額計算を変更した場合は、既存データで手計算した結果と画面表示を突き合わせる

4. **ローカルサーバーを止める**
   確認が終わったらPIDを指定して `Stop-Process` する。

5. **コミット前に機密ファイルを確認する**
   `git status` で `data/ryohi.db` や `.streamlit/secrets.toml` がステージされていないか必ず確認する
   （`.gitignore`済みだが、`git add -f` などで誤って追加していないかの二重チェック）。

6. **pushする**
   問題がなければ `git add` → `git commit` → `git push`。
   mainブランチへのpushでStreamlit Cloudが自動的に再デプロイする。

## 確認だけで終わっていい場合

「ちょっと見た目を確認したいだけ」など、pushを前提としない軽い確認のときは3番までで区切ってよい。
本番反映（push）に進む前には、必ずこの一連の確認を経ること。
