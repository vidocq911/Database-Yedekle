import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
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
      if (typeof value === "string" && value) return value;
    }
  } catch {
    // Legacy single-key environment variables are supported below.
  }
  return null;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (!["GET", "POST"].includes(req.method)) return json({ error: "Method not allowed." }, 405);

  const url = Deno.env.get("SUPABASE_URL");
  const publishableKey = keyFromMap("SUPABASE_PUBLISHABLE_KEYS") ?? Deno.env.get("SUPABASE_ANON_KEY");
  const secretKey = keyFromMap("SUPABASE_SECRET_KEYS") ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const authorization = req.headers.get("Authorization");
  if (!url || !publishableKey || !secretKey) return json({ error: "Supabase sunucu yapılandırması eksik." }, 500);
  if (!authorization?.startsWith("Bearer ")) return json({ error: "Giriş gerekli." }, 401);

  const userClient = createClient(url, publishableKey, {
    global: { headers: { Authorization: authorization } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: userData, error: userError } = await userClient.auth.getUser();
  if (userError || !userData.user) return json({ error: "Oturum geçersiz." }, 401);

  const admin = createClient(url, secretKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: role, error: roleError } = await admin
    .from("admin_users").select("role,is_active").eq("user_id", userData.user.id).maybeSingle();
  if (roleError) return json({ error: "Yönetici yetkisi kontrol edilemedi." }, 500);
  if (!role?.is_active || !["owner", "admin"].includes(role.role)) return json({ error: "Yönetici yetkisi gerekli." }, 403);

  const [customers, demos, licenses, devices, sales, payments] = await Promise.all([
    admin.from("customers").select("id,customer_number,company_name,contact_person,phone,email,status,created_at,updated_at").order("created_at", { ascending: false }).limit(500),
    admin.from("demo_requests").select("id,customer_id,status,requested_at,reviewed_at,review_note,trial_starts_at,trial_ends_at,duplicate_review_required").order("requested_at", { ascending: false }).limit(500),
    admin.from("licenses").select("id,customer_id,status,issued_at,starts_at,expires_at,max_devices,last_verified_at,notes").order("issued_at", { ascending: false }).limit(500),
    admin.from("license_devices").select("id,license_id,device_label,first_activated_at,last_verified_at,released_at,release_note").order("first_activated_at", { ascending: false }).limit(500),
    admin.from("sales").select("id,customer_id,license_id,sale_date,total_amount,currency,payment_method,due_date,notes,created_at").order("sale_date", { ascending: false }).limit(500),
    admin.from("payments").select("id,sale_id,amount,paid_at,payment_method,reference_note").order("paid_at", { ascending: false }).limit(1000),
  ]);

  const failed = [customers, demos, licenses, devices, sales, payments].find((item) => item.error);
  if (failed?.error) {
    console.error("admin-dashboard query failed", failed.error.message);
    return json({ error: "Panel verileri alınamadı. Veritabanı migration'larını kontrol edin." }, 500);
  }

  const customerById = new Map((customers.data ?? []).map((c) => [c.id, c]));
  const licenseById = new Map((licenses.data ?? []).map((l) => [l.id, l]));
  const saleById = new Map((sales.data ?? []).map((s) => [s.id, s]));
  const paidBySale = new Map<string, number>();
  for (const p of payments.data ?? []) paidBySale.set(p.sale_id, (paidBySale.get(p.sale_id) ?? 0) + Number(p.amount));

  return json({
    user: { id: userData.user.id, email: userData.user.email, role: role.role },
    customers: (customers.data ?? []).map((c) => ({
      ...c,
      demo_requests: (demos.data ?? []).filter((d) => d.customer_id === c.id),
      licenses: (licenses.data ?? []).filter((l) => l.customer_id === c.id).map((l) => ({
        ...l, devices: (devices.data ?? []).filter((d) => d.license_id === l.id),
      })),
      sales: (sales.data ?? []).filter((s) => s.customer_id === c.id).map((s) => ({
        ...s, paid_amount: paidBySale.get(s.id) ?? 0,
        balance: Math.max(0, Number(s.total_amount) - (paidBySale.get(s.id) ?? 0)),
        payments: (payments.data ?? []).filter((p) => p.sale_id === s.id),
      })),
    })),
    demo_requests: (demos.data ?? []).map((d) => ({ ...d, customer: customerById.get(d.customer_id) ?? null })),
    licenses: (licenses.data ?? []).map((l) => ({
      ...l, customer: customerById.get(l.customer_id) ?? null,
      devices: (devices.data ?? []).filter((d) => d.license_id === l.id),
    })),
    devices: (devices.data ?? []).map((d) => ({ ...d, license: licenseById.get(d.license_id) ?? null })),
    sales: (sales.data ?? []).map((s) => ({
      ...s, customer: customerById.get(s.customer_id) ?? null,
      paid_amount: paidBySale.get(s.id) ?? 0,
      balance: Math.max(0, Number(s.total_amount) - (paidBySale.get(s.id) ?? 0)),
      payments: (payments.data ?? []).filter((p) => p.sale_id === s.id),
    })),
    summary: {
      customers: (customers.data ?? []).length,
      active_customers: (customers.data ?? []).filter((c) => c.status === "active").length,
      pending_demos: (demos.data ?? []).filter((d) => d.status === "pending").length,
      active_licenses: (licenses.data ?? []).filter((l) => ["issued", "active"].includes(l.status)).length,
      outstanding_try: (sales.data ?? []).filter((s) => s.currency === "TRY").reduce((sum, s) => sum + Math.max(0, Number(s.total_amount) - (paidBySale.get(s.id) ?? 0)), 0),
    },
  });
});
