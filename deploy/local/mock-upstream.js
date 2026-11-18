const model = "gpt-4o-mini";
const usage = {prompt_tokens: 3, completion_tokens: 1, total_tokens: 4};
Bun.serve({
  port: 8080,
  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (path === "/v1/models") return Response.json({object: "list", data: [{id: model, object: "model"}]});
    if (path !== "/v1/chat/completions" || request.method !== "POST") return new Response(null, {status: 404});
    const body = await request.json();
    if (body.model !== model) return Response.json({error: {message: "unknown test model"}}, {status: 400});
    const base = {id: "chatcmpl-local", created: Math.floor(Date.now()/1000), model};
    if (!body.stream) return Response.json({...base, object: "chat.completion", choices: [
      {index: 0, message: {role: "assistant", content: "fixture-ok"}, finish_reason: "stop"}
    ], usage});
    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        for (const chunk of [
          {choices: [{index: 0, delta: {role: "assistant", content: "fixture-ok"}, finish_reason: null}]},
          {choices: [{index: 0, delta: {}, finish_reason: "stop"}]},
          {choices: [], usage}
        ]) controller.enqueue(encoder.encode("data: " + JSON.stringify({...base, object: "chat.completion.chunk", ...chunk}) + "\n\n"));
        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
        controller.close();
      }
    });
    return new Response(stream, {headers: {"Content-Type":"text/event-stream"}});
  }
});
