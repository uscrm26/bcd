// Supabase Edge Function: ai-summary
// 部署後環境變數需設 ARK_API_KEY 與 ARK_MODEL（endpoint id）
import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

const ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions";

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "authorization,x-client-info,content-type",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
    }});
  }
  try {
    const { text } = await req.json();
    const key = Deno.env.get("ARK_API_KEY");
    const model = Deno.env.get("ARK_MODEL") || "doubao-pro-4k";
    const r = await fetch(ARK_URL, {
      method: "POST",
      headers: { "Authorization": "Bearer " + key, "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: "你是海關擔保 bond 代辦助手。用繁體中文摘要信件，3 行內：對方要什麼、目前進展、建議下一步。" },
          { role: "user", content: String(text || "").slice(0, 4000) },
        ],
      }),
    });
    const j = await r.json();
    const summary = j?.choices?.[0]?.message?.content || JSON.stringify(j);
    return new Response(JSON.stringify({ summary }), { headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }});
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), { status: 500, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }});
  }
});
