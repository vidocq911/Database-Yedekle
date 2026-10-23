-- Atomic one-device activation and administrator-controlled device release.
-- Call only through trusted Edge Functions using the server-side secret key.

create or replace function public.activate_license_atomic(
  p_key_hash text,
  p_device_hash text,
  p_device_label text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_license public.licenses%rowtype;
  v_customer_status text;
  v_device public.license_devices%rowtype;
begin
  select l.* into v_license
  from public.licenses l
  where l.license_key_hash = p_key_hash
  for update;

  if not found then
    return jsonb_build_object('ok', false, 'code', 'invalid_license');
  end if;

  select c.status into v_customer_status
  from public.customers c
  where c.id = v_license.customer_id;

  if v_customer_status is distinct from 'active' then
    return jsonb_build_object('ok', false, 'code', 'customer_inactive');
  end if;

  if v_license.status in ('suspended', 'revoked', 'expired') then
    return jsonb_build_object('ok', false, 'code', v_license.status);
  end if;

  if v_license.expires_at is not null and v_license.expires_at <= now() then
    update public.licenses set status = 'expired' where id = v_license.id;
    insert into public.license_events(customer_id, license_id, event_type, details)
    values (v_license.customer_id, v_license.id, 'license_expired', '{}'::jsonb);
    return jsonb_build_object('ok', false, 'code', 'expired');
  end if;

  select d.* into v_device
  from public.license_devices d
  where d.license_id = v_license.id and d.released_at is null
  limit 1;

  if found and v_device.device_fingerprint_hash <> p_device_hash then
    return jsonb_build_object('ok', false, 'code', 'device_conflict');
  end if;

  if found then
    update public.license_devices
    set device_label = coalesce(nullif(p_device_label, ''), device_label),
        last_verified_at = now()
    where id = v_device.id;

    update public.licenses
    set status = 'active',
        starts_at = coalesce(starts_at, now()),
        last_verified_at = now()
    where id = v_license.id;

    insert into public.license_events(customer_id, license_id, device_id, event_type, details)
    values (v_license.customer_id, v_license.id, v_device.id, 'license_verified', '{"source":"activation"}'::jsonb);

    return jsonb_build_object(
      'ok', true, 'code', 'already_activated',
      'license_id', v_license.id,
      'customer_id', v_license.customer_id,
      'starts_at', coalesce(v_license.starts_at, now()),
      'expires_at', v_license.expires_at,
      'device_id', v_device.id
    );
  end if;

  insert into public.license_devices(license_id, device_fingerprint_hash, device_label, last_verified_at)
  values (v_license.id, p_device_hash, nullif(p_device_label, ''), now())
  returning * into v_device;

  update public.licenses
  set status = 'active',
      starts_at = coalesce(starts_at, now()),
      last_verified_at = now()
  where id = v_license.id;

  insert into public.license_events(customer_id, license_id, device_id, event_type, details)
  values (v_license.customer_id, v_license.id, v_device.id, 'device_activated', '{"device_limit":1}'::jsonb);

  return jsonb_build_object(
    'ok', true, 'code', 'activated',
    'license_id', v_license.id,
    'customer_id', v_license.customer_id,
    'starts_at', coalesce(v_license.starts_at, now()),
    'expires_at', v_license.expires_at,
    'device_id', v_device.id
  );
end;
$$;

create or replace function public.release_license_device_atomic(
  p_device_id uuid,
  p_released_by uuid,
  p_release_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_device public.license_devices%rowtype;
  v_license public.licenses%rowtype;
begin
  select d.* into v_device
  from public.license_devices d
  where d.id = p_device_id
  for update;

  if not found then
    return jsonb_build_object('ok', false, 'code', 'device_not_found');
  end if;

  select l.* into v_license
  from public.licenses l
  where l.id = v_device.license_id
  for update;

  if v_device.released_at is not null then
    return jsonb_build_object('ok', true, 'code', 'already_released', 'device_id', v_device.id);
  end if;

  update public.license_devices
  set released_at = now(),
      released_by = p_released_by::text,
      release_note = nullif(p_release_note, '')
  where id = v_device.id;

  insert into public.license_events(customer_id, license_id, device_id, event_type, details)
  values (
    v_license.customer_id,
    v_license.id,
    v_device.id,
    'device_released',
    jsonb_build_object('released_by', p_released_by, 'note', nullif(p_release_note, ''))
  );

  return jsonb_build_object('ok', true, 'code', 'released', 'device_id', v_device.id, 'license_id', v_license.id);
end;
$$;

revoke all on function public.activate_license_atomic(text, text, text) from public, anon, authenticated;
grant execute on function public.activate_license_atomic(text, text, text) to service_role;
revoke all on function public.release_license_device_atomic(uuid, uuid, text) from public, anon, authenticated;
grant execute on function public.release_license_device_atomic(uuid, uuid, text) to service_role;
