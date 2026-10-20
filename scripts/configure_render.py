"""Inspect or migrate the existing clinic Python service via Render's REST API.

Authentication: RENDER_API_KEY, or a hidden terminal prompt. No OAuth required.
The default is read-only; --apply updates this exact service and starts a deploy.
"""

import argparse
import getpass
import json
import os
import re
import sys

import httpx

API_URL = "https://api.render.com/v1/"
SERVICE_URL = "https://physiotherapy-consultation.onrender.com"
REPOSITORY = "https://github.com/foxicall/Physiotherapy_consultation"
BUILD_COMMAND = "pip install -r requirements-api.txt"
START_COMMAND = "uvicorn server:api --host 0.0.0.0 --port $PORT --workers 1 --no-access-log"


class RenderError(Exception):
    """Safe operator-facing error without credentials or upstream response text."""


def request(client, method, path, **kwargs):
    try:
        response = client.request(method, path, **kwargs)
    except httpx.RequestError:
        raise RenderError("Render 連線失敗；若正在寫入，請先在控制台確認結果再重試。") from None
    if not 200 <= response.status_code < 300:
        raise RenderError(f"Render API 回傳 HTTP {response.status_code}；請確認帳號權限或控制台狀態。")
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        raise RenderError("Render 回應格式不符預期；請在控制台確認操作狀態。") from None


def find_service(client):
    cursor = None
    matches = []
    seen = set()
    for _ in range(100):
        params = {"limit": 100, "includePreviews": "false"}
        if cursor:
            params["cursor"] = cursor
        page = request(client, "GET", "services", params=params)
        if not isinstance(page, list):
            raise RenderError("無法讀取 Render 服務清單。")
        for item in page:
            service = item["service"]
            if service.get("serviceDetails", {}).get("url", "").rstrip("/") == SERVICE_URL:
                matches.append(service)
        if len(page) < 100:
            break
        cursor = page[-1].get("cursor")
        if not cursor or cursor in seen:
            raise RenderError("服務分頁資料不完整，未執行任何變更。")
        seen.add(cursor)
    else:
        raise RenderError("服務數量超出檢查範圍，未執行任何變更。")
    if len(matches) != 1:
        raise RenderError("此帳號中未找到唯一符合診所網址的服務，未執行任何變更。")
    service = request(client, "GET", f"services/{matches[0]['id']}")
    validate_service(service)
    return service


def validate_service(service):
    details = service.get("serviceDetails", {})
    repo = service.get("repo", "").rstrip("/").removesuffix(".git")
    if (details.get("url", "").rstrip("/") != SERVICE_URL
            or repo != REPOSITORY or service.get("type") != "web_service"
            or not re.fullmatch(r"srv-[A-Za-z0-9]+", service.get("id", ""))):
        raise RenderError("服務網址、類型或 GitHub 來源不符，未執行任何變更。")
    if details.get("runtime", details.get("env")) != "python":
        raise RenderError("此工具只處理既有 Python 服務；其他執行環境需另行檢查。")
    if service.get("suspended") != "not_suspended" or service.get("buildSourceId"):
        raise RenderError("服務已暫停或使用共用 Build Source，需先由管理員確認設定。")


def desired_settings():
    return {
        "branch": "main",
        "rootDir": "",
        "serviceDetails": {
            "healthCheckPath": "/api/health",
            "envSpecificDetails": {"buildCommand": BUILD_COMMAND, "startCommand": START_COMMAND},
        },
    }


def migrate(client, service, commit):
    validate_service(service)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RenderError("請指定已測試的完整 40 位 commit 雜湊值。")
    service_path = f"services/{service['id']}"
    updated = request(client, "PATCH", service_path, json=desired_settings())
    validate_service(updated)
    details = updated["serviceDetails"]
    commands = details.get("envSpecificDetails", {})
    if (updated.get("branch") != "main" or updated.get("rootDir") != ""
            or details.get("healthCheckPath") != "/api/health"
            or commands.get("buildCommand") != BUILD_COMMAND
            or commands.get("startCommand") != START_COMMAND):
        raise RenderError("設定更新尚未確認；未觸發部署，請先檢查 Render 控制台。")
    return request(client, "POST", service_path + "/deploys", json={"commitId": commit, "clearCache": "do_not_clear"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="更新設定並觸發部署；預設僅檢查")
    parser.add_argument("--commit", help="要部署的已測試完整 Git commit 雜湊值")
    args = parser.parse_args()
    if args.apply and (not args.commit or not re.fullmatch(r"[0-9a-f]{40}", args.commit)):
        parser.error("--apply 需搭配 --commit 與完整 40 位雜湊值")
    token = os.getenv("RENDER_API_KEY", "").strip()
    if not token and sys.stdin.isatty():
        token = getpass.getpass("Render API Key（隱藏輸入，不會儲存）：").strip()
    if not token:
        print("缺少 RENDER_API_KEY。請透過工作環境 Secrets 設定，或在本機互動終端執行。", file=sys.stderr)
        return 1
    try:
        with httpx.Client(base_url=API_URL, headers={"Authorization": "Bearer " + token, "Accept": "application/json"}, timeout=30, follow_redirects=False) as client:
            service = find_service(client)
            print(json.dumps({"service_id": service["id"], "url": SERVICE_URL, "settings": desired_settings()}, ensure_ascii=False, indent=2))
            if not args.apply:
                print("檢查完成；尚未修改設定或觸發部署。")
                return 0
            deploy = migrate(client, service, args.commit)
            print(json.dumps({"deploy_id": (deploy or {}).get("id"), "status": (deploy or {}).get("status", "queued")}, ensure_ascii=False))
            print("部署請求已送出；尚不代表部署成功。完成後需檢查 /api/health、PWA 及 AI 設定。")
            print("本工具保留環境變數。AI 需要在 Render 設定 GEMINI_API_KEY 與 CLINIC_ACCESS_CODE。")
    except RenderError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
