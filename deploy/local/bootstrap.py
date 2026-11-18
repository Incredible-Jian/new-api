"""Configure only the loopback Compose project and its synthetic upstream."""
import json
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler

BASE = "http://127.0.0.1:33080"
opener = build_opener(ProxyHandler({}))


def api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(BASE + path, data=None if data is None else json.dumps(data).encode(),
                      headers=headers, method=method)
    with opener.open(request, timeout=30) as response:
        result = json.load(response)
    if not result.get("success"):
        raise RuntimeError(f"{method} {path}: {result.get('message', 'failed')}")
    return result.get("data")


def configure():
    values = dict(line.split("=", 1) for line in Path(__file__).with_name(".env").read_text().splitlines())
    login = {"username": "pilotadmin", "password": values["LOCAL_ADMIN_PASSWORD"]}
    if not api("GET", "/api/setup")["status"]:
        api("POST", "/api/setup", {**login, "confirmPassword": login["password"]})
    admin = api("POST", "/api/user/login", login)["access_token"]
    for key, value in {"RegisterEnabled": "false", "PasswordRegisterEnabled": "false",
                       "quota_setting.trust_quota_usd": "0", "RetryTimes": "0"}.items():
        api("PUT", "/api/option/", {"key": key, "value": value}, admin)
    channels = api("GET", "/api/channel/?p=1&page_size=100", token=admin)["items"]
    if not any(channel["name"] == "local-fixture" for channel in channels):
        api("POST", "/api/channel/", {"mode": "single", "channel": {
            "name": "local-fixture", "type": 1, "group": "default", "status": 1,
            "models": "gpt-4o-mini", "key": "fixture-only", "base_url": "http://fixture:8080"
        }}, admin)
    return admin


if __name__ == "__main__":
    configure()
    print("Local administrator, invitation-only registration and fixture channel configured.")
