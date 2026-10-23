import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" },
});
function keyFromMap(name: string): string | null {
  const raw = Deno.env.get(name);
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && "default" in parsed) {
      const key = (parsed as Record<string, unknown>).default;
      if (typeof key === "string" && key) return key;
    }
  } catch { /* legacy single-key variables below */ }
  return null;
}
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed." }, 405);
  const url = Deno.env.get("SUPABASE_URL");
  const publicKey = keyFromMap("SUPABASE_PUBLISHABLE_KEYS") ?? Deno.env.get("SUPABASE_ANON_KEY");
  const secretKey = keyFromMap("SUPABASE_SECRET_KEYS") ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const auth = req.headers.get("Authorization");
  if (!url || !publicKey || !secretKey) return json({ error: "Sunucu yapılandırması eksik." }, 500);
  if (!auth?.startsWith("Bearer ")) return json({ error: "Giriş gerekli." }, 401);

  const userClient = createClient(url, publicKey, { global: { headers: { Authorization: auth } }, auth: { persistSession: false, autoRefreshToken: false } });
  const { data: userData, error: userError } = await userClient.auth.getUser();
  if (userError || !userData.user) return json({ error: "Oturum geçersiz." }, 401);
  const admin = createClient(url, secretKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: role, error: roleError } = await admin.from("admin_users").select("role,is_active").eq("user_id", userData.user.id).maybeSingle();
  if (roleError) return json({ error: "Yönetici yetkisi kontrol edilemedi." }, 500);
  if (!role?.is_active || !["owner", "admin"].includes(role.role)) return json({ error: "Yönetici yetkisi gerekli." }, 403);

  let body: Record<string, unknown>;
  try { body = await req.json(); } catch { return json({ error: "Geçersiz JSON." }, 400); }
  const action = typeof body.action === "string" ? body.action : "";
  const text = (v: unknown, max = 500) => typeof v === "string" ? v.trim().slice(0, max) : "";
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  const amount = (v: unknown) => typeof v === "number" || (typeof v === "string" && v.trim() !== "") ? Number(v) : NaN;

  if (action === "create-sale") {
    const customerId = text(body.customer_id, 80), total = amount(body.total_amount);
    const currency = text(body.currency, 3) || "TRY";
    if (!uuid.test(customerId) || !Number.isFinite(total) || total < 0 || !["TRY", "EUR", "USD"].includes(currency)) return json({ error: "Müşteri, geçerli tutar ve para birimi gerekli." }, 400);
    const { data: customer, error: ce } = await admin.from("customers").select("id,status").eq("id", customerId).maybeSingle();
    if (ce) return json({ error: "Müşteri kontrol edilemedi." }, 500);
    if (!customer || customer.status !== "active") return json({ error: "Satış yalnızca aktif müşteriye eklenebilir." }, 409);
    const licenseId = text(body.license_id, 80);
    if (licenseId && !uuid.test(licenseId)) return json({ error: "Lisans kimliği geçersiz." }, 400);
    if (licenseId) {
      const { data: license, error: le } = await admin.from("licenses").select("id,customer_id").eq("id", licenseId).maybeSingle();
      if (le || !license || license.customer_id !== customerId) return json({ error: "Lisans bu müşteriye ait değil." }, 400);
    }
    const saleDate = text(body.sale_date, 10) || new Date().toISOString().slice(0, 10);
    const dueDate = text(body.due_date, 10) || null;
    const { data, error } = await admin.from("sales").insert({
      customer_id: customerId, license_id: licenseId || null, sale_date: saleDate, total_amount: total,
      currency, payment_method: text(body.payment_method, 100) || null, due_date: dueDate, notes: text(body.notes, 1000) || null,
    }).select("id,customer_id,total_amount,currency,sale_date,due_date").single();
    if (error) { console.error("create-sale failed", error.message); return json({ error: "Satış kaydı oluşturulamadı." }, 500); }
    await admin.from("license_events").insert({ customer_id: customerId, license_id: licenseId || null, event_type: "sale_created", details: { sale_id: data.id, created_by: userData.user.id } });
    return json({ ok: true, sale: data }, 201);
  }

  if (action === "add-payment") {
    const saleId = text(body.sale_id, 80), paid = amount(body.amount);
    if (!uuid.test(saleId) || !Number.isFinite(paid) || paid <= 0) return json({ error: "Satış ve sıfırdan büyük tahsilat tutarı gerekli." }, 400);
    const { data: sale, error: se } = await admin.from("sales").select("id,customer_id,total_amount,currency").eq("id", saleId).maybeSingle();
    if (se) return json({ error: "Satış kontrol edilemedi." }, 500);
    if (!sale) return json({ error: "Satış bulunamadı." }, 404);
    const { data: previous, error: pe } = await admin.from("payments").select("amount").eq("sale_id", saleId);
    if (pe) return json({ error: "Önceki tahsilatlar okunamadı." }, 500);
    const outstanding = Number(sale.total_amount) - (previous ?? []).reduce((s, p) => s + Number(p.amount), 0);
    if (paid > outstanding + 0.0001) return json({ error: "Tahsilat kalan bakiyeden fazla olamaz." }, 409);
    const { data, error } = await admin.from("payments").insert({
      sale_id: saleId, amount: paid, paid_at: text(body.paid_at, 40) || new Date().toISOString(),
      payment_method: text(body.payment_method, 100) || null, reference_note: text(body.reference_note, 500) || null,
      created_by: userData.user.id,
    }).select("id,sale_id,amount,paid_at,payment_method,reference_note").single();
    if (error) { console.error("add-payment failed", error.message); return json({ error: "Tahsilat kaydedilemedi." }, 500); }
    await admin.from("license_events").insert({ customer_id: sale.customer_id, event_type: "payment_recorded", details: { sale_id: saleId, payment_id: data.id, created_by: userData.user.id } });
    return json({ ok: true, payment: data }, 201);
  }

  if (action === "customer-status") {
    const customerId = text(body.customer_id, 80), status = text(body.status, 20);
    if (!uuid.test(customerId) || !["active", "blocked", "rejected"].includes(status)) return json({ error: "Geçersiz müşteri veya durum." }, 400);
    const { data, error } = await admin.from("customers").update({ status, updated_at: new Date().toISOString() }).eq("id", customerId).select("id,customer_number,status").single();
    if (error || !data) return json({ error: "Müşteri durumu güncellenemedi." }, 500);
    await admin.from("license_events").insert({ customer_id: customerId, event_type: "customer_status_changed", details: { status, changed_by: userData.user.id } });
    return json({ ok: true, customer: data });
  }

  if (action === "license-status") {
    const licenseId = text(body.license_id, 80), status = text(body.status, 20);
    if (!uuid.test(licenseId) || !["suspended", "revoked", "active"].includes(status)) return json({ error: "Geçersiz lisans veya durum." }, 400);
    const { data: license, error: le } = await admin.from("licenses").select("id,customer_id,status").eq("id", licenseId).maybeSingle();
    if (le || !license) return json({ error: "Lisans bulunamadı." }, 404);
    if (status === "active" && license.status === "revoked") return json({ error: "İptal edilmiş lisans tekrar etkinleştirilemez; yeni lisans oluşturun." }, 409);
    const { data, error } = await admin.from("licenses").update({ status }).eq("id", licenseId).select("id,status").single();
    if (error || !data) return json({ error: "Lisans durumu güncellenemedi." }, 500);
    await admin.from("license_events").insert({ customer_id: license.customer_id, license_id: licenseId, event_type: "license_status_changed", details: { status, changed_by: userData.user.id } });
    return json({ ok: true, license: data });
  }
  return json({ error: "Desteklenmeyen yönetim işlemi." }, 400);
});
