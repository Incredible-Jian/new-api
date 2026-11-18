"""Exercise the running gateway with synthetic data and a short-lived local key."""
from urllib.error import HTTPError
from urllib.request import Request
import json
import secrets

from bootstrap import BASE, api, configure, opener


def run():
    admin = configure()
    name = "smoke-" + secrets.token_hex(5)
    api("POST", "/api/token/", {"name": name, "remain_quota": 500000,
        "expired_time": -1, "model_limits_enabled": True, "model_limits": "gpt-4o-mini"}, admin)
    records = api("GET", "/api/token/search?keyword=" + name, token=admin)["items"]
    key_id = next(r["id"] for r in records if r["name"] == name)
    try:
        key = api("POST", f"/api/token/{key_id}/key", {}, admin)["key"]
        headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
        models_request = Request(BASE + "/v1/models", headers=headers)
        with opener.open(models_request, timeout=30) as response:
            assert [item["id"] for item in json.load(response)["data"]] == ["gpt-4o-mini"]
        for stream in (False, True):
            body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "fixture"}],
                    "max_tokens": 16, "stream": stream}
            if stream:
                body["stream_options"] = {"include_usage": True}
            request = Request(BASE + "/v1/chat/completions", data=json.dumps(body).encode(), headers=headers)
            with opener.open(request, timeout=30) as response:
                if stream:
                    events = [line[6:].strip() for line in response if line.startswith(b"data: ")]
                    assert events[-1] == b"[DONE]"
                    chunks = [json.loads(event) for event in events[:-1]]
                    assert any(c["choices"] and c["choices"][0]["delta"].get("content") == "fixture-ok" for c in chunks)
                    assert any((c.get("usage") or {}).get("total_tokens") == 4 for c in chunks)
                else:
                    result = json.load(response)
                    assert result["choices"][0]["message"]["content"] == "fixture-ok"
                    assert result["usage"]["total_tokens"] == 4
    finally:
        api("DELETE", f"/api/token/{key_id}", token=admin)
    try:
        opener.open(models_request, timeout=10).close()
    except HTTPError as error:
        assert error.code in (401, 403)
    else:
        raise AssertionError("Revoked key accepted")
    print("PASS models, chat, SSE, usage and key revocation")


if __name__ == "__main__":
    run()
