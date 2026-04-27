# Mood Shop 直播廣告 LINE 通知

每 5 分鐘抓 Meta 廣告花費，遇到下列事件就推 LINE：

- 🟢 直播廣告開始花費
- 🟡 廣告花費達到預算門檻
- ⚪ 帳戶總花費每多 $1000
- 🔴 廣告已結束

## 架構

```
GitHub Actions (cron 每 5 分)
        ↓
    main.py
   /        \
Meta API   LINE Messaging API
        ↓
   state.json (記錄上次狀態，commit 回 repo)
```

## 檔案

| 檔案 | 用途 |
|---|---|
| `main.py` | 主程式 |
| `requirements.txt` | Python 套件 |
| `state.json` | 狀態記錄（自動更新） |
| `.github/workflows/check.yml` | GitHub Actions 排程 |
| `SETUP_GUIDE.md` | **完整設定步驟，先看這個** |

## 第一次使用

請打開 [`SETUP_GUIDE.md`](SETUP_GUIDE.md) 從頭開始。
