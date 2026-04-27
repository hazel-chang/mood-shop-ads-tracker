"""
Mood Shop 直播廣告監控
每 5 分鐘檢查 Meta 廣告花費，遇到事件就推送 LINE 通知。

事件：
  🟢 直播廣告開始花費（廣告首次有花費）
  🟡 廣告花費達到門檻（spend ≥ 預算）
  ⚪ 廣告已花費 $1000（帳戶總花費每跨過 1000 一次）
  🔴 廣告已結束（廣告狀態從 ACTIVE 變成非 ACTIVE）
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# ============ 環境變數 ============
META_ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
META_AD_ACCOUNT_ID = os.environ["META_AD_ACCOUNT_ID"]  # 不含 act_ 前綴
LINE_CHANNEL_TOKEN = os.environ["LINE_CHANNEL_TOKEN"]
LINE_USER_ID = os.environ.get("LINE_USER_ID", "").strip()
LINE_GROUP_ID = os.environ.get("LINE_GROUP_ID", "").strip()

# 預算單位除數（TWD/JPY/KRW = 1，USD/EUR = 100）
CURRENCY_DIVISOR = float(os.environ.get("CURRENCY_DIVISOR", "1"))

# ============ 常數 ============
STATE_FILE = Path(__file__).parent / "state.json"
TZ = timezone(timedelta(hours=8))  # Asia/Taipei
META_API = "https://graph.facebook.com/v19.0"
MILESTONE_STEP = 1000  # 帳戶總花費每多 $1000 通知一次


# ============ 工具函式 ============
def now_tw() -> datetime:
    return datetime.now(TZ)


def fmt_amount(x) -> str:
    if x is None:
        return "—"
    return f"${int(round(float(x)))} 元"


def fmt_time(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ============ LINE ============
def line_push(text: str) -> None:
    """推送到個人 + 群組（兩者都會收到）"""
    targets = [t for t in [LINE_USER_ID, LINE_GROUP_ID] if t]
    if not targets:
        print("[WARN] 沒設定 LINE_USER_ID / LINE_GROUP_ID，跳過推送", file=sys.stderr)
        return
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
        "Content-Type": "application/json",
    }
    for to in targets:
        payload = {"to": to, "messages": [{"type": "text", "text": text}]}
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            json=payload,
            timeout=20,
        )
        if r.status_code >= 300:
            print(
                f"[ERR] LINE push to {to[:6]}... failed "
                f"({r.status_code}): {r.text}",
                file=sys.stderr,
            )
        else:
            print(f"[OK] LINE pushed to {to[:6]}...")


# ============ Meta API ============
def fetch_insights() -> list:
    """抓今天每支廣告的花費（level=ad）"""
    url = f"{META_API}/act_{META_AD_ACCOUNT_ID}/insights"
    params = {
        "level": "ad",
        "fields": "ad_id,ad_name,spend",
        "date_preset": "today",
        "limit": 500,
        "access_token": META_ACCESS_TOKEN,
    }
    items = []
    while url:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        items.extend(body.get("data", []))
        url = body.get("paging", {}).get("next")
        params = None  # next URL 已包含參數
    return items


def fetch_ads_meta(ad_ids: list) -> dict:
    """抓每支廣告的目前狀態與預算（adset 與 campaign 兩處皆查）"""
    if not ad_ids:
        return {}
    out = {}
    for i in range(0, len(ad_ids), 50):
        batch = ad_ids[i : i + 50]
        params = {
            "ids": ",".join(batch),
            "fields": (
                "id,name,effective_status,"
                "adset{daily_budget,lifetime_budget},"
                "campaign{daily_budget,lifetime_budget}"
            ),
            "access_token": META_ACCESS_TOKEN,
        }
        r = requests.get(META_API, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        for ad_id, info in body.items():
            adset = info.get("adset") or {}
            campaign = info.get("campaign") or {}
            raw_budget = (
                adset.get("daily_budget")
                or adset.get("lifetime_budget")
                or campaign.get("daily_budget")
                or campaign.get("lifetime_budget")
            )
            budget = (
                float(raw_budget) / CURRENCY_DIVISOR if raw_budget else None
            )
            out[ad_id] = {
                "name": info.get("name"),
                "effective_status": info.get("effective_status"),
                "budget": budget,
            }
    return out


# ============ 主邏輯 ============
def main() -> None:
    today = now_tw().strftime("%Y-%m-%d")
    state = load_state()

    # 跨日重置
    if state.get("date") != today:
        print(f"[INFO] 日期切換為 {today}，重置狀態")
        state = {"date": today, "total_milestone": 0, "ads": {}}

    insights = fetch_insights()
    ad_ids_today = [it["ad_id"] for it in insights]
    extra_ids = [
        aid for aid in state.get("ads", {}).keys() if aid not in ad_ids_today
    ]
    meta = fetch_ads_meta(list(set(ad_ids_today + extra_ids)))

    notifications = []
    new_ads_state = {}
    total_spend = 0.0

    # ----- 處理今天有 insights 的廣告 -----
    for it in insights:
        ad_id = it["ad_id"]
        spend = float(it.get("spend", 0) or 0)
        total_spend += spend

        info = meta.get(ad_id, {})
        name = it.get("ad_name") or info.get("name") or "(未知)"
        budget = info.get("budget")
        eff_status = info.get("effective_status")

        prev = state.get("ads", {}).get(ad_id, {})
        started_notified = prev.get("started_notified", False)
        threshold_notified = prev.get("threshold_notified", False)
        ended_notified = prev.get("ended_notified", False)

        # 🟢 開始花費
        if (not started_notified) and spend > 0:
            notifications.append(
                f"🟢直播廣告開始花費！\n"
                f"━━━━━━━━━━━━━━\n"
                f"▫️廣告名稱：{name}\n"
                f"▫️目前花費：{fmt_amount(spend)}\n"
                f"▫️時間：{fmt_time(now_tw())}"
            )
            started_notified = True

        # 🟡 達到門檻
        if (not threshold_notified) and budget and spend >= budget:
            notifications.append(
                f"🟡廣告花費達到門檻！\n"
                f"━━━━━━━━━━━━━━\n"
                f"▫️廣告名稱：{name}\n"
                f"▫️廣告預算：{fmt_amount(budget)}\n"
                f"▫️目前花費：{fmt_amount(spend)}\n"
                f"🕐 時間：{fmt_time(now_tw())}"
            )
            threshold_notified = True

        # 🔴 結束（狀態從 ACTIVE 變成非 ACTIVE，且確實有過花費）
        is_ended = eff_status is not None and eff_status != "ACTIVE"
        if (not ended_notified) and is_ended and spend > 0:
            notifications.append(
                f"🔴廣告已結束！\n"
                f"━━━━━━━━━━━━━━\n"
                f"▫️廣告名稱：{name}\n"
                f"▫️花費金額：{fmt_amount(spend)}"
            )
            ended_notified = True

        new_ads_state[ad_id] = {
            "name": name,
            "spend": spend,
            "budget": budget,
            "effective_status": eff_status,
            "started_notified": started_notified,
            "threshold_notified": threshold_notified,
            "ended_notified": ended_notified,
        }

    # ----- 處理之前有花費、現在不在 insights 裡的廣告（補捕『已結束』）-----
    for ad_id in extra_ids:
        prev = state.get("ads", {}).get(ad_id, {})
        info = meta.get(ad_id, {})
        eff_status = info.get("effective_status")
        ended_notified = prev.get("ended_notified", False)
        prev_spend = float(prev.get("spend", 0))

        is_ended = eff_status is not None and eff_status != "ACTIVE"
        if (not ended_notified) and is_ended and prev_spend > 0:
            notifications.append(
                f"🔴廣告已結束！\n"
                f"━━━━━━━━━━━━━━\n"
                f"▫️廣告名稱：{prev.get('name', '(未知)')}\n"
                f"▫️花費金額：{fmt_amount(prev_spend)}"
            )
            ended_notified = True

        new_ads_state[ad_id] = {
            **prev,
            "effective_status": eff_status,
            "ended_notified": ended_notified,
        }

    # ----- ⚪ 帳戶總花費每 $1000 -----
    new_milestone = int(total_spend // MILESTONE_STEP)
    prev_milestone = int(state.get("total_milestone", 0))
    if new_milestone > prev_milestone:
        for m in range(prev_milestone + 1, new_milestone + 1):
            notifications.append(
                f"⚪廣告已花費${m * MILESTONE_STEP}！\n"
                f"━━━━━━━━━━━━━━\n"
                f"🕐 時間：{fmt_time(now_tw())}"
            )

    # ----- 推送 -----
    for msg in notifications:
        line_push(msg)

    # ----- 儲存新狀態 -----
    new_state = {
        "date": today,
        "total_spend": round(total_spend, 2),
        "total_milestone": new_milestone,
        "ads": new_ads_state,
        "last_run": now_tw().isoformat(),
    }
    save_state(new_state)
    print(
        f"[OK] 完成：總花費 ${total_spend:.2f}, "
        f"廣告數 {len(new_ads_state)}, 通知 {len(notifications)} 則"
    )


if __name__ == "__main__":
    main()
