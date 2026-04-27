# Mood Shop 直播廣告 LINE 通知 — 設定指南

從頭設定到第一條通知大概 30–60 分鐘。請依序完成。

---

## 你需要準備好的東西

| # | 項目 | 狀態 |
|---|---|---|
| 1 | Meta Marketing API Access Token | 你已有 ✅ |
| 2 | GitHub 帳號 | 你已有 ✅ |
| 3 | LINE OA Channel Access Token | 待取得 |
| 4 | 個人 LINE User ID | 待取得 |
| 5 | LINE 群組 ID | 待取得 |
| 6 | Meta 廣告帳號 ID | 待取得 |

---

## Part 1：取得 LINE Channel Access Token

1. 前往 https://developers.line.biz/console/ 用 LINE 登入
2. 選你的 Provider → 選你的 Mood Shop OA channel（必須是 Messaging API 類型）
3. 上方分頁切到 **「Messaging API」**
4. 滑到頁面最下面 **「Channel access token」** 區塊
5. 點 **「Issue」** 產生 Long-lived token（如果已有就直接複製）
6. 複製整串 token（很長）

> 記下來：這就是 `LINE_CHANNEL_TOKEN`

---

## Part 2：取得個人 LINE User ID 和群組 ID

LINE 不直接顯示 User ID / Group ID，要透過 webhook 接到一次訊息才能拿到。
最簡單的方法是用 https://webhook.site/

### 2-1. 開一個臨時 webhook

1. 開 https://webhook.site/
2. 頁面會自動產生一個 **「Your unique URL」**，複製整串 URL
   （長得像 `https://webhook.site/abcd1234-5678-...`）
3. **這個分頁先不要關**

### 2-2. 把 webhook 設給 LINE OA

1. 回到 LINE Developers Console 你的 channel → **「Messaging API」** 分頁
2. 找到 **「Webhook URL」**，按 **Edit**，貼上 webhook.site 的 URL → **Update**
3. 把 **「Use webhook」** 開關打開（綠色）
4. 滑到上面找到 **「LINE Official Account features」**：
   - **Auto-reply messages**：點 Edit → 關掉（避免機器人自動回應蓋掉訊息）
   - **Greeting messages**：可開可關

### 2-3. 拿個人 User ID

1. 在 **「Messaging API」** 分頁找到 **QR code**
2. 用你個人 LINE 掃 QR code → 加 OA 為好友
3. 在跟 OA 的聊天視窗 **隨便傳一句話**（例：「test」）
4. 回到 webhook.site 分頁，會看到一筆新的 POST 紀錄
5. 點開該筆紀錄，看 **Body**，找這段：
   ```json
   "source": {
     "type": "user",
     "userId": "U1234567890abcdef..."
   }
   ```
6. 複製 `userId` 的值（**U** 開頭）

> 記下來：這就是 `LINE_USER_ID`

### 2-4. 拿群組 ID

1. 把 OA 加進你的 Mood Shop LINE 群組
   （在群組裡：右上選單 → 邀請 → 搜尋 OA 名稱 → 加入）
2. **在群組裡隨便傳一句話**（例：「hi」）
3. 回 webhook.site，會看到新的紀錄，裡面：
   ```json
   "source": {
     "type": "group",
     "groupId": "Cabcdef1234567890..."
   }
   ```
4. 複製 `groupId`（**C** 開頭）

> 記下來：這就是 `LINE_GROUP_ID`

### 2-5. 拿完之後可以把 webhook 關掉

回 LINE Developers Console，把 **「Use webhook」** 關掉就好（這個專案不需要 webhook，只需要主動推播）。

---

## Part 3：取得 Meta 廣告帳號 ID

1. 進 https://business.facebook.com/adsmanager
2. 確認左上角選的是 **Mood Shop** 的廣告帳號
3. 廣告帳號名稱旁邊會有一串：`act_1234567890`
4. 複製 **`act_` 後面的數字**（不含 `act_`）

> 記下來：這就是 `META_AD_ACCOUNT_ID`（例如 `1234567890`）

---

## Part 4：把專案傳到 GitHub

### 4-1. 建一個 GitHub 私人倉庫

1. 開 https://github.com/new
2. Repository name：`mood-shop-ads-tracker`
3. 選 **Private**
4. 不要勾任何 Initialize 選項（README、.gitignore、license 都不要）
5. 按 **Create repository**

### 4-2. 把這個資料夾推上去

打開 Terminal（Mac/Linux）或 PowerShell（Windows），切換到這個 `mood-shop-ads-tracker` 資料夾：

```bash
cd 路徑/到/mood-shop-ads-tracker
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的帳號/mood-shop-ads-tracker.git
git push -u origin main
```

如果沒裝 git，也可以用 GitHub Desktop 圖形介面拖檔上傳。

---

## Part 5：設定 GitHub Secrets

1. 在 GitHub 你的 repo 頁 → 上方 **Settings**
2. 左邊選單 → **Secrets and variables** → **Actions**
3. 按 **New repository secret**，依序加入下面 5 個（CURRENCY_DIVISOR 預設不用加，除非帳號是 USD/EUR）：

| Name | Value |
|---|---|
| `META_ACCESS_TOKEN` | 你的 Meta API token |
| `META_AD_ACCOUNT_ID` | Part 3 取得的數字（不含 `act_`） |
| `LINE_CHANNEL_TOKEN` | Part 1 取得的 token |
| `LINE_USER_ID` | Part 2-3 的 U 開頭字串 |
| `LINE_GROUP_ID` | Part 2-4 的 C 開頭字串 |

> 如果你的廣告帳號幣別是 **USD / EUR**（有小數的貨幣），多加一個 secret：
> `CURRENCY_DIVISOR` = `100`
> TWD/JPY/KRW 帳號不用加，預設就是 1。

---

## Part 6：啟用 GitHub Actions 並測試

1. 回 repo 首頁 → 上方 **Actions** 分頁
2. 第一次進入會顯示「Workflows aren't being run on this forked repo / I understand my workflows...」
   → 點藍色按鈕啟用
3. 左邊應該會看到 **「Check Meta Ads」** 工作流程，點進去
4. 右邊有 **「Run workflow」** 下拉 → 按下去手動觸發一次
5. 等約 30 秒，點進剛跑的那次 run，看每個 step 是不是綠勾
   - 如果 **Run tracker** 步驟顯示 `[OK] 完成：總花費 $X` → 設定成功 🎉
   - 之後每 5 分鐘會自動跑

### 試一下通知會不會通

如果現在剛好沒在跑直播廣告，可以：
1. 暫時把 `main.py` 裡 `MILESTONE_STEP = 1000` 改成 `MILESTONE_STEP = 1`，push 上去
2. 手動觸發 workflow，看 LINE 有沒有收到訊息
3. 確認後改回 1000

---

## 常見問題

**Q: 沒收到 LINE 通知，但 Action 顯示綠勾？**
- 確認你個人有加 OA 為好友、OA 有在群組裡
- 看 Action log 是不是有 `[OK] LINE pushed to ...` 訊息
- LINE OA 免費方案每月 200 則訊息，可能用完了 → 升級方案或先用付費方案

**Q: Action 紅字，KeyError: 'META_ACCESS_TOKEN'？**
- 回 Part 5 確認 5 個 secret 名稱完全正確（區分大小寫）

**Q: Meta API 回 token 過期？**
- Meta access token 有效期不一定，可能要重新生成
- 進 [Graph API Explorer](https://developers.facebook.com/tools/explorer/) 重生成 long-lived token

**Q: GitHub 排程不是每 5 分鐘準時跑？**
- 正常，GitHub Actions 排程在尖峰時段可能延遲 1–10 分鐘
- 加上 Meta API 本身有 5–15 分延遲，整體通知延遲約 10–25 分

**Q: state.json 一直被自動 commit，看起來很亂？**
- 正常的，每 5 分鐘會自動 commit 一次最新狀態
- 這些 commit 都帶 `[skip ci]` 不會觸發其他 action
- 用 GitHub UI 看 commit 列表時可以靠作者名 `github-actions[bot]` 過濾掉

**Q: 我想暫停監控（例如沒在直播的日子）？**
- repo → Actions → 「Check Meta Ads」→ 右邊 ⋯ → **Disable workflow**
- 要恢復就 **Enable workflow**

**Q: 廣告預算抓不到（顯示 —）？**
- 可能是預算設在 Campaign Budget Optimization (CBO) 而非 adset
- 程式已同時查 adset 和 campaign，仍抓不到的話檢查 token 權限是否包含 `ads_read`

---

## 想客製化什麼？

| 想改 | 改哪裡 |
|---|---|
| 通知間隔（例如改 3 分鐘） | `.github/workflows/check.yml` 的 `cron: "*/5 * * * *"` 改成 `*/3` |
| 每多少錢通知一次（不要 $1000） | `main.py` 的 `MILESTONE_STEP = 1000` |
| 訊息格式 | `main.py` 裡四段 `notifications.append(...)` |
| 只發到群組不發個人 | GitHub Secrets 把 `LINE_USER_ID` 刪掉 |
