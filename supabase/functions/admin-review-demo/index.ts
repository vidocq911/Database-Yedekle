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
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
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

  const { data: demo, error: findError } = await adminClient
    .from("demo_requests")
    .select("id, customer_id, status")
    .eq("id", requestId)
    .maybeSingle();

  if (findError) return json({ error: "Demo talebi okunamadı." }, 500);
  if (!demo) return json({ error: "Demo talebi bulunamadı." }, 404);
  if (demo.status !== "pending") return json({ error: "Bu talep daha önce işleme alınmış." }, 409);

  const now = new Date().toISOString();
  const approved = decision === "approve";
  const patch = {
    status: approved ? "approved" : "rejected",
    reviewed_at: now,
    reviewed_by: userData.user.id,
    review_note: note,
    trial_starts_at: approved ? now : null,
    trial_ends_at: approved ? new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString() : null,
  };

  const { data: updated, error: updateError } = await adminClient
    .from("demo_requests")
    .update(patch)
    .eq("id", requestId)
    .eq("status", "pending")
    .select("id, status, reviewed_at, trial_starts_at, trial_ends_at")
    .maybeSingle();

  if (updateError) return json({ error: "Demo talebi güncellenemedi." }, 500);
  if (!updated) return json({ error: "Talep eşzamanlı olarak başka bir yönetici tarafından işlendi." }, 409);

  const { error: customerError } = await adminClient
    .from("customers")
    .update({ status: approved ? "active" : "rejected", updated_at: now })
    .eq("id", demo.customer_id);

  if (customerError) {
    return json({
      error: "Talep kararı kaydedildi ancak müşteri durumu güncellenemedi.",
      request_id: requestId,
      partial_update: true,
    }, 500);
  }

  const { error: eventError } = await adminClient.from("license_events").insert({
    customer_id: demo.customer_id,
    event_type: approved ? "demo_approved" : "demo_rejected",
    details: { request_id: requestId, reviewed_by: userData.user.id, note },
  });

  if (eventError) {
    return json({
      error: "Talep ve müşteri güncellendi ancak olay kaydı yazılamadı.",
      request_id: requestId,
      partial_update: true,
    }, 500);
  }

  return json({ ok: true, demo_request: updated });
});
