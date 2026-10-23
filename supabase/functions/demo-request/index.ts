// Public demo request endpoint. Deploy as a Supabase Edge Function with
// SUPABASE_URL and the built-in SUPABASE_SECRET_KEYS configured by Supabase.
// Do not expose the service-role key to the Windows client or browser.
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

function getSecretKey(): string | null {
  const raw = Deno.env.get("SUPABASE_SECRET_KEYS");
  if (raw) {
    try {
      const keys: unknown = JSON.parse(raw);
      if (keys && typeof keys === "object" && "default" in keys) {
        const key = (keys as Record<string, unknown>).default;
        if (typeof key === "string" && key.length > 0) return key;
      }
    } catch {
      // Fall back to the legacy service-role key for older projects.
    }
  }
  return Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
}

function normalizePhone(value: string) {
  return value.replace(/[^\d+]/g, "").slice(0, 32);
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Geçersiz JSON." }, 400);
  }

  // Basic anti-bot honeypot. Real deployments should also enable platform-level
  // rate limits/CAPTCHA and monitor abuse; CORS is not an access control.
  if (typeof body.website === "string" && body.website.trim() !== "") {
    return json({ ok: true, message: "Talep alındı." });
  }

  const companyName = typeof body.company_name === "string" ? body.company_name.trim() : "";
  const contactPerson = typeof body.contact_person === "string" ? body.contact_person.trim() : "";
  const phone = typeof body.phone === "string" ? normalizePhone(body.phone) : "";
  const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : null;

  if (companyName.length < 2 || companyName.length > 160) return json({ error: "Firma adı 2-160 karakter olmalı." }, 400);
  if (contactPerson.length < 2 || contactPerson.length > 120) return json({ error: "Yetkili kişi adı 2-120 karakter olmalı." }, 400);
  if (phone.length < 7) return json({ error: "Geçerli bir telefon numarası girin." }, 400);
  if (email && (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))) return json({ error: "E-posta adresini kontrol edin." }, 400);

  const url = Deno.env.get("SUPABASE_URL");
  const serviceKey = getSecretKey();
  if (!url || !serviceKey) return json({ error: "Sunucu yapılandırması eksik." }, 500);

  const supabase = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });

  // Existing contact details trigger manual duplicate review. Company name alone
  // is not unique because different customers can share the same company name.
  let duplicateQuery = supabase.from("customers").select("id").eq("phone", phone).limit(1);
  if (email) duplicateQuery = supabase.from("customers").select("id").or(`phone.eq.${phone},email.eq.${email}`).limit(1);
  const { data: possibleMatches, error: matchError } = await duplicateQuery;
  if (matchError) return json({ error: "Mükerrerlik kontrolü yapılamadı." }, 500);

  const duplicateReviewRequired = (possibleMatches?.length ?? 0) > 0;

  const { data: customer, error: customerError } = await supabase
    .from("customers")
    .insert({
      company_name: companyName,
      contact_person: contactPerson,
      phone,
      email,
      status: "pending",
    })
    .select("id, customer_number")
    .single();

  if (customerError || !customer) return json({ error: "Müşteri kaydı oluşturulamadı." }, 500);

  const { data: demoRequest, error: requestError } = await supabase
    .from("demo_requests")
    .insert({
      customer_id: customer.id,
      status: "pending",
      duplicate_review_required: duplicateReviewRequired,
    })
    .select("id, status, requested_at")
    .single();

  if (requestError || !demoRequest) {
    // Preserve the customer record for admin audit; no trial is started here.
    return json({ error: "Demo talebi oluşturulamadı. Lütfen destekle iletişime geçin." }, 500);
  }

  return json({
    ok: true,
    customer_number: customer.customer_number,
    request_id: demoRequest.id,
    status: demoRequest.status,
    message: duplicateReviewRequired
      ? "Talebiniz alındı; mükerrer başvuru kontrolünden sonra yönetici inceleyecek."
      : "Talebiniz alındı. Deneme süresi yalnızca yönetici onayından sonra başlar.",
  }, 201);
});
