"""Two bounded live calls through the loopback gateway. Requires a transient mounted credential."""
import json
import secrets
from urllib.error import HTTPError
from urllib.request import Request

from bootstrap import BASE, api, configure, opener

MODELS = ("deepseek-v4-pro", "deepseek-v4-flash")


def run():
    admin = configure()
    channels = api("GET", "/api/channel/?p=1&page_size=100", token=admin)["items"]
    if not any(c["name"] == "deepseek-official-pilot" for c in channels):
        api("POST", "/api/channel/", {"mode": "single", "channel": {
            "name": "deepseek-official-pilot", "type": 43, "group": "default", "status": 1,
            "models": ",".join(MODELS), "key": "secret-ref:deepseek-pilot", "base_url": "https://api.deepseek.com"
        }}, admin)
    name = "live-" + secrets.token_hex(5)
    api("POST", "/api/token/", {"name": name, "remain_quota": 50000, "expired_time": -1,
        "model_limits_enabled": True, "model_limits": ",".join(MODELS)}, admin)
    records = api("GET", "/api/token/search?keyword=" + name, token=admin)["items"]
    key_id = next(r["id"] for r in records if r["name"] == name)
    try:
        key = api("POST", f"/api/token/{key_id}/key", {}, admin)["key"]
        for model in MODELS:
            stream = model.endswith("flash")
            body = {"model": model, "messages": [{"role": "user", "content": "Return only OK."}],
                    "max_tokens": 16, "stream": stream, "thinking": {"type": "disabled"}}
            if stream:
                body["stream_options"] = {"include_usage": True}
            req = Request(BASE + "/v1/chat/completions", data=json.dumps(body).encode(),
                          headers={"Content-Type":"application/json", "Authorization":"Bearer " + key})
            with opener.open(req, timeout=60) as response:
                if stream:
                    events = [line[6:].strip() for line in response if line.startswith(b"data: ")]
                    assert events[-1] == b"[DONE]"
                    parts = [json.loads(event) for event in events[:-1]]
                    reply = "".join(p["choices"][0]["delta"].get("content") or "" for p in parts if p.get("choices"))
                    usage = next(p["usage"] for p in parts if p.get("usage"))
                else:
                    result = json.load(response)
                    reply = result["choices"][0]["message"]["content"]
                    usage = result["usage"]
                assert reply.strip() == "OK" and usage["total_tokens"] > 0
                print(model, "stream" if stream else "chat", usage["prompt_tokens"], usage["completion_tokens"])
        def chat(model, messages, **options):
            body = {"model": model, "messages": messages, "max_tokens": 96,
                    "thinking": {"type": "disabled"}, **options}
            request = Request(BASE + "/v1/chat/completions", data=json.dumps(body).encode(),
                              headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
            with opener.open(request, timeout=60) as response:
                result = json.load(response)
            assert result["usage"]["total_tokens"] > 0
            print(model, "contract", result["usage"]["prompt_tokens"], result["usage"]["completion_tokens"])
            return result["choices"][0]["message"]

        history = [{"role": "user", "content": "Call read_fixture to get its value. Then return that value."}]
        tool = {"type": "function", "function": {"name": "read_fixture", "description": "Read test value",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}
        assistant = chat(MODELS[0], history, tools=[tool])
        call = assistant["tool_calls"][0]
        assert call["function"]["name"] == "read_fixture" and json.loads(call["function"]["arguments"]) == {}
        history.extend([assistant, {"role": "tool", "tool_call_id": call["id"], "content": "PILOT42"}])
        assert "PILOT42" in chat(MODELS[0], history, tools=[tool])["content"]
        message = chat(MODELS[1], [{"role": "user", "content": 'Return JSON {"ok": true}.'}],
                       response_format={"type": "json_object"})
        assert json.loads(message["content"]) == {"ok": True}
    finally:
        api("DELETE", f"/api/token/{key_id}", token=admin)


if __name__ == "__main__":
    try:
        run()
    except HTTPError as exc:
        message = json.load(exc).get("error", {})
        raise SystemExit(f"Gateway returned {exc.code}: {message.get('code')}")
