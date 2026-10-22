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

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
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
      // Some deployments may expose a direct key string.
      return value;
    }
  }
  return legacy ?? null;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ success: false, error: "method_not_allowed" }, 405);

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const secretKey = configuredKey(Deno.env.get("SUPABASE_SECRET_KEYS"), Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"));
  if (!supabaseUrl || !secretKey) return json({ success: false, error: "server_not_configured" }, 500);

  let body: { license_key?: unknown; device_fingerprint?: unknown; device_label?: unknown };
  try {
    body = await req.json();
  } catch {
    return json({ success: false, error: "invalid_json" }, 400);
  }

  const licenseKey = typeof body.license_key === "string" ? body.license_key.trim() : "";
  const fingerprint = typeof body.device_fingerprint === "string" ? body.device_fingerprint.trim() : "";
  const deviceLabel = typeof body.device_label === "string" ? body.device_label.trim().slice(0, 120) : "";

  if (licenseKey.length < 16 || licenseKey.length > 256 || fingerprint.length < 16 || fingerprint.length > 512) {
    return json({ success: false, error: "invalid_request" }, 400);
  }

  const admin = createClient(supabaseUrl, secretKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const keyHash = await sha256(licenseKey);
  const deviceHash = await sha256(fingerprint);
  const { data, error } = await admin.rpc("activate_license_atomic", {
    p_key_hash: keyHash,
    p_device_hash: deviceHash,
    p_device_label: deviceLabel || null,
  });

  if (error) {
    console.error("activate_license_atomic failed", error.code, error.message);
    return json({ success: false, error: "activation_unavailable" }, 500);
  }
  if (!data?.ok) {
    const code = data?.code ?? "activation_denied";
    const status = code === "invalid_license" ? 404
      : code === "device_conflict" ? 409
      : code === "customer_inactive" ? 403
      : 403;
    return json({ success: false, error: code }, status);
  }

  return json({
    success: true,
    status: data.code,
    license_id: data.license_id,
    starts_at: data.starts_at,
    expires_at: data.expires_at,
    device_id: data.device_id,
    verification_interval_hours: 168,
    offline_grace_hours: 168,
    signed_response: false,
    message: "Lisans doğrulandı. Bu yanıt henüz imzalı değildir; çevrimdışı lisans güvenliği tamamlanmış sayılmaz.",
  });
});
