import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function configuredKey(value: string | undefined, legacy: string | undefined): string | null {
  if (value) {
    try {
      const parsed = JSON.parse(value);
      if (typeof parsed === "string") return parsed;
      if (parsed && typeof parsed === "object") {
        const item = parsed.default ?? Object.values(parsed)[0];
        if (typeof item === "string") return item;
      }
    } catch {
      return value;
    }
  }
  return legacy ?? null;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ success: false, error: "method_not_allowed" }, 405);

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const publishableKey = configuredKey(Deno.env.get("SUPABASE_PUBLISHABLE_KEYS"), Deno.env.get("SUPABASE_ANON_KEY"));
  const secretKey = configuredKey(Deno.env.get("SUPABASE_SECRET_KEYS"), Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"));
  const authHeader = req.headers.get("Authorization");
  if (!supabaseUrl || !publishableKey || !secretKey) return json({ success: false, error: "server_not_configured" }, 500);
  if (!authHeader?.startsWith("Bearer ")) return json({ success: false, error: "unauthorized" }, 401);

  const authClient = createClient(supabaseUrl, publishableKey, {
    global: { headers: { Authorization: authHeader } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: userData, error: userError } = await authClient.auth.getUser();
  if (userError || !userData.user) return json({ success: false, error: "unauthorized" }, 401);

  const admin = createClient(supabaseUrl, secretKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: adminRow, error: adminError } = await admin
    .from("admin_users")
    .select("role,is_active")
    .eq("user_id", userData.user.id)
    .maybeSingle();
  if (adminError) return json({ success: false, error: "authorization_check_failed" }, 500);
  if (!adminRow?.is_active || !["owner", "admin"].includes(adminRow.role)) {
    return json({ success: false, error: "forbidden" }, 403);
  }

  let body: { device_id?: unknown; release_note?: unknown };
  try {
    body = await req.json();
  } catch {
    return json({ success: false, error: "invalid_json" }, 400);
  }

  const deviceId = typeof body.device_id === "string" ? body.device_id : "";
  const releaseNote = typeof body.release_note === "string" ? body.release_note.trim().slice(0, 500) : "";
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  if (!uuidPattern.test(deviceId)) return json({ success: false, error: "invalid_device_id" }, 400);

  const { data, error } = await admin.rpc("release_license_device_atomic", {
    p_device_id: deviceId,
    p_released_by: userData.user.id,
    p_release_note: releaseNote || null,
  });
  if (error) {
    console.error("release_license_device_atomic failed", error.code, error.message);
    return json({ success: false, error: "device_release_failed" }, 500);
  }
  if (!data?.ok) return json({ success: false, error: data?.code ?? "device_release_failed" }, 404);
  return json({ success: true, status: data.code, device_id: data.device_id, license_id: data.license_id });
});
