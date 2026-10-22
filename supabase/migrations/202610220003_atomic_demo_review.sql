-- Atomically review a demo request, update its customer, and append an audit event.
-- The Edge Function must authenticate the caller and check admin_users before invoking this RPC.
create or replace function public.review_demo_request_atomic(
  p_request_id uuid,
  p_decision text,
  p_reviewed_by uuid,
  p_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_demo public.demo_requests%rowtype;
  v_now timestamptz := now();
  v_trial_end timestamptz;
begin
  if p_decision not in ('approve', 'reject') then
    raise exception 'Invalid decision' using errcode = '22023';
  end if;

  select *
    into v_demo
    from public.demo_requests
   where id = p_request_id
   for update;

  if not found then
    raise exception 'Demo request not found' using errcode = 'P0002';
  end if;

  if v_demo.status <> 'pending' then
    raise exception 'Demo request already reviewed' using errcode = '40001';
  end if;

  if p_decision = 'approve' then
    v_trial_end := v_now + interval '7 days';
  else
    v_trial_end := null;
  end if;

  update public.demo_requests
     set status = case when p_decision = 'approve' then 'approved' else 'rejected' end,
         reviewed_at = v_now,
         reviewed_by = p_reviewed_by::text,
         review_note = left(nullif(btrim(p_note), ''), 1000),
         trial_starts_at = case when p_decision = 'approve' then v_now else null end,
         trial_ends_at = v_trial_end
   where id = p_request_id;

  update public.customers
     set status = case when p_decision = 'approve' then 'active' else 'rejected' end,
         updated_at = v_now
   where id = v_demo.customer_id;

  if not found then
    raise exception 'Related customer not found' using errcode = 'P0002';
  end if;

  insert into public.license_events (
    customer_id, event_type, details
  ) values (
    v_demo.customer_id,
    case when p_decision = 'approve' then 'demo_approved' else 'demo_rejected' end,
    jsonb_build_object(
      'request_id', p_request_id,
      'reviewed_by', p_reviewed_by,
      'note', left(nullif(btrim(p_note), ''), 1000)
    )
  );

  return jsonb_build_object(
    'id', p_request_id,
    'status', case when p_decision = 'approve' then 'approved' else 'rejected' end,
    'reviewed_at', v_now,
    'trial_starts_at', case when p_decision = 'approve' then v_now else null end,
    'trial_ends_at', v_trial_end
  );
end;
$$;

revoke all on function public.review_demo_request_atomic(uuid, text, uuid, text) from public;
revoke all on function public.review_demo_request_atomic(uuid, text, uuid, text) from anon, authenticated;
grant execute on function public.review_demo_request_atomic(uuid, text, uuid, text) to service_role;
