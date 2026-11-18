"""Verify customer A's key remains inaccessible to customer B through management APIs."""
import secrets
from pathlib import Path
from urllib.error import HTTPError

from bootstrap import api, configure


def run():
    admin = configure()
    values = dict(line.split("=", 1) for line in Path(__file__).with_name(".env").read_text().splitlines())
    sessions = []
    for suffix in ("A", "B"):
        username = "pilot_" + suffix.lower()
        login = {"username": username, "password": values[f"LOCAL_CUSTOMER_{suffix}_PASSWORD"]}
        entries = api("GET", "/api/user/search?keyword=" + username, token=admin)["items"]
        if not any(u["username"] == username for u in entries):
            api("POST", "/api/user/", {**login, "role": 1}, admin)
        sessions.append(api("POST", "/api/user/login", login)["access_token"])
    owner, other = sessions
    name = "isolate-" + secrets.token_hex(4)
    api("POST", "/api/token/", {"name": name, "remain_quota": 100, "expired_time": -1}, owner)
    key_id = api("GET", "/api/token/search?keyword=" + name, token=owner)["items"][0]["id"]
    try:
        assert not api("GET", "/api/token/search?keyword=" + name, token=other)["items"]
        for method, path in [("GET", f"/api/token/{key_id}"), ("POST", f"/api/token/{key_id}/key"),
                             ("GET", "/api/channel/")]:
            try:
                api(method, path, {} if method == "POST" else None, other)
            except HTTPError as error:
                assert error.code in (401, 403, 404)
            except RuntimeError:
                pass  # Management API returned success=false.
            else:
                raise AssertionError(f"Unexpected cross-account success on {path}")
        assert api("GET", f"/api/token/{key_id}", token=owner)["id"] == key_id
    finally:
        api("DELETE", f"/api/token/{key_id}", token=owner)
    print("PASS separate customer accounts, key listing, detail, secret and admin access")


if __name__ == "__main__":
    run()
