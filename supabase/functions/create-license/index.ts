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

function keyFromMap(name: string): string | null {
  const raw = Deno.env.get(name);
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && "default" in parsed) {
      const value = (parsed as Record<string, unknown>).default;
      return typeof value === "string" && value ? value : null;
    }
  } catch {
    // Older Supabase projects may expose a single legacy key instead.
  }
  return null;
}

function randomLicenseKey(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let out = "";
  for (const byte of bytes) out += alphabet[byte % alphabet.length];
  return out.match(/.{1,6}/g)?.join("-") ?? out;
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const url = Deno.env.get("SUPABASE_URL");
  const publishableKey = keyFromMap("SUPABASE_PUBLISHABLE_KEYS") ?? Deno.env.get("SUPABASE_ANON_KEY");
  const secretKey = keyFromMap("SUPABASE_SECRET_KEYS") ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !publishableKey || !secretKey) return json({ error: "Sunucu yapılandırması eksik." }, 500);

  const authorization = req.headers.get("Authorization");
  if (!authorization?.startsWith("Bearer ")) return json({ error: "Giriş gerekli." }, 401);

  const userClient = createClient(url, publishableKey, {
    global: { headers: { Authorization: authorization } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: userData, error: userError } = await userClient.auth.getUser();
  if (userError || !userData.user) return json({ error: "Oturum geçersiz." }, 401);

  const adminClient = createClient(url, secretKey, {
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

  const customerId = typeof body.customer_id === "string" ? body.customer_id.trim() : "";
  const notes = typeof body.notes === "string" ? body.notes.trim().slice(0, 1000) : null;
  const expiresAt = typeof body.expires_at === "string" && body.expires_at.trim() ? body.expires_at : null;

  if (!customerId) return json({ error: "customer_id gerekli." }, 400);
  if (expiresAt && (!Number.isFinite(Date.parse(expiresAt)) || Date.parse(expiresAt) <= Date.now())) {
    return json({ error: "expires_at gelecekte geçerli bir tarih olmalı." }, 400);
  }

  const { data: customer, error: customerError } = await adminClient
    .from("customers")
    .select("id, customer_number, status")
    .eq("id", customerId)
    .maybeSingle();

  if (customerError) return json({ error: "Müşteri kontrol edilemedi." }, 500);
  if (!customer) return json({ error: "Müşteri bulunamadı." }, 404);
  if (customer.status !== "active") return json({ error: "Yalnızca aktif müşteriye lisans oluşturulabilir." }, 409);

  const rawKey = randomLicenseKey();
  const keyHash = await sha256(rawKey);
  const { data: license, error: licenseError } = await adminClient
    .from("licenses")
    .insert({
      customer_id: customer.id,
      license_key_hash: keyHash,
      status: "issued",
      starts_at: null,
      expires_at: expiresAt,
      max_devices: 1,
      created_by: userData.user.id,
      notes,
    })
    .select("id, status, issued_at, starts_at, expires_at, max_devices")
    .single();

  if (licenseError || !license) return json({ error: "Lisans oluşturulamadı." }, 500);

  const { error: eventError } = await adminClient.from("license_events").insert({
    customer_id: customer.id,
    license_id: license.id,
    event_type: "license_issued",
    details: { issued_by: userData.user.id, expires_at: expiresAt },
  });

  if (eventError) {
    // Remove the newly-created license so we never return a key without its audit event.
    await adminClient.from("licenses").delete().eq("id", license.id);
    return json({ error: "Lisans işlem geçmişi kaydedilemedi; lisans oluşturma geri alındı." }, 500);
  }

  return json({
    ok: true,
    customer_number: customer.customer_number,
    license,
    license_key: rawKey,
    warning: "Lisans anahtarı yalnızca bu yanıtta gösterilir. Güvenli biçimde müşteriye iletin.",
  }, 201);
});
