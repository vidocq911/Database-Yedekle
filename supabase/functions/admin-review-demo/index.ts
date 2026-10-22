import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" },
  });
}

function readKeyMap(name: string): Record<string, string> | null {
  const raw = Deno.env.get(name);
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && "default" in parsed) {
      const key = (parsed as Record<string, unknown>).default;
      if (typeof key === "string" && key.length > 0) return { default: key };
    }
  } catch {
    // Older projects may expose only the legacy single-key variables.
  }
  return null;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const url = Deno.env.get("SUPABASE_URL");
  const publishableKey = readKeyMap("SUPABASE_PUBLISHABLE_KEYS")?.default
    ?? Deno.env.get("SUPABASE_ANON_KEY");
  const serviceKey = readKeyMap("SUPABASE_SECRET_KEYS")?.default
    ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  if (!url || !publishableKey || !serviceKey) {
    return json({ error: "Sunucu yapılandırması eksik." }, 500);
  }

  const authorization = req.headers.get("Authorization");
  if (!authorization?.startsWith("Bearer ")) return json({ error: "Giriş gerekli." }, 401);

  // Validate the caller's access token; never trust a user ID supplied in the body.
  const userClient = createClient(url, publishableKey, {
    global: { headers: { Authorization: authorization } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: userData, error: userError } = await userClient.auth.getUser();
  if (userError || !userData.user) return json({ error: "Oturum geçersiz." }, 401);

  const adminClient = createClient(url, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: admin, error: adminError } = await adminClient
    .from("admin_users")
    .select("role, is_active")
    .eq("user_id", userData.user.id)
    .maybeSingle();

  if (adminError) return json({ error: "Yönetici yetkisi kontrol edilemedi." }, 500);
  if (!admin || !admin.is_active || !["owner", "admin"].includes(admin.role)) {
    return json({ error: "Bu işlem için yönetici yetkisi gerekiyor." }, 403);
  }

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Geçersiz JSON." }, 400);
  }

  const requestId = typeof body.request_id === "string" ? body.request_id.trim() : "";
  const decision = body.decision;
  const note = typeof body.note === "string" ? body.note.trim().slice(0, 1000) : null;
  if (!requestId || !["approve", "reject"].includes(String(decision))) {
    return json({ error: "request_id ve approve/reject kararı gerekli." }, 400);
  }

  // The RPC performs the request/customer/event updates in one database transaction.
  const { data: reviewed, error: reviewError } = await adminClient.rpc("review_demo_request_atomic", {
    p_request_id: requestId,
    p_decision: decision,
    p_reviewed_by: userData.user.id,
    p_note: note,
  });

  if (reviewError) {
    if (reviewError.code === "P0002") return json({ error: "Demo talebi bulunamadı." }, 404);
    if (reviewError.code === "40001") return json({ error: "Bu talep daha önce işleme alınmış." }, 409);
    if (reviewError.code === "22023") return json({ error: "Geçersiz karar." }, 400);
    return json({
      error: "Demo talebi güvenli biçimde işlenemedi. Atomic review migration uygulanmış mı kontrol edin.",
    }, 500);
  }

  return json({ ok: true, demo_request: reviewed });
});
