(() => {
  const state = { memberships: [], readOnly: false, token: null, tenantId: null, mode: null, email: null, clients: [], brands: [], campaigns: [] };
  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const msg = (text, error=false) => { $('notice').textContent = text; $('notice').className = error ? 'error' : 'ok'; };
  const api = async (path, method='GET', body=null) => {
    const response = await fetch(path, {method, headers: {'Content-Type':'application/json', ...(state.token ? {'Authorization':`Bearer ${state.token}`} : {})}, ...(body ? {body: JSON.stringify(body)} : {})});
    const result = await response.json().catch(() => ({}));
    if(!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : `HTTP ${response.status}`);
    return result;
  };
  const portal = createReviewPanel($('review-panel'),api,msg);
  const tenantPath = name => `/api/tenants/${state.tenantId}/${name}`;
  const fromForm = form => Object.fromEntries(new FormData(form).entries());
  const process = (form, handler) => form.addEventListener('submit', async event => { event.preventDefault(); try { await handler(fromForm(form)); } catch (e) { msg(e.message, true); } });
  const enter = async (token, membership, email='') => {
    const tenantId = membership.tenant_id;
    state.token = token; state.tenantId = tenantId; state.mode = membership.mode; state.email = email;
    portal.setContext({tenant:tenantId,role:membership.role});
    state.readOnly = ['viewer', 'client_viewer'].includes(membership.role);
    $('workspace-select').value = tenantId;
    $('workspace-forms').classList.toggle('hidden', state.readOnly);
    $('client-scope').classList.toggle('hidden', !state.readOnly);
    state.clients = []; state.brands = []; state.campaigns = [];
    render([], []);
    $('who').textContent = email || `Tenant ${tenantId.slice(0,8)}`;
    $('auth').classList.add('hidden'); $('workspace').classList.remove('hidden');
    msg('Đăng nhập thành công. Đây là môi trường phát triển, chưa dành cho khách hàng thật.');
    await refresh();
  };
  process($('register-form'), async data => {
    const result = await api('/api/auth/register', 'POST', data);
    await enter(result.access_token, {...result, role:'owner'}, data.email);
  });
  process($('login-form'), async data => {
    const result = await api('/api/auth/login', 'POST', data);
    if(!result.tenants.length) throw new Error('Tài khoản không có workspace');
    state.memberships = result.tenants;
    $('workspace-select').replaceChildren(...result.tenants.map(m => new Option(m.organization_name, m.tenant_id)));
    $('workspace-choice').classList.toggle('hidden', result.tenants.length < 2);
    const linked=new URLSearchParams(location.search).get('workspace');
    await enter(result.access_token,result.tenants.find(m=>m.tenant_id===linked)||result.tenants[0],data.email);
    if(linked && !result.tenants.some(m=>m.tenant_id===linked)) msg('Bạn không có quyền mở liên kết của workspace này.',true);
  });
  $('workspace-select').addEventListener('change', event => {
    const membership = state.memberships.find(m => m.tenant_id === event.target.value);
    if (membership) enter(state.token, membership, state.email).catch(e => msg(e.message, true));
  });
  process($('client-form'), async data => {
    await api(tenantPath('clients'), 'POST', data);
    $('client-form').reset(); msg('Đã tạo khách hàng.'); await refresh();
  });
  process($('brand-form'), async data => {
    await api(tenantPath('brands'), 'POST', data);
    $('brand-form').reset(); msg('Đã tạo thương hiệu và ghi nhận Brand Kit.'); await refresh();
  });
  process($('campaign-form'), async data => {
    await api(tenantPath('campaigns'), 'POST', data);
    $('campaign-form').reset(); msg('Đã tạo chiến dịch.'); await refresh();
  });
  const option = (items, id, empty) => {
    $(id).innerHTML = `<option value="">${esc(empty)}</option>` + items.map(i=>`<option value="${esc(i.id)}">${esc(i.name)}</option>`).join('');
  };
  const render = (actions, deliverables) => {
    $('client-scope').textContent = state.readOnly
      ? [...state.clients.map(c => c.name), ...state.brands.map(b => b.name)].join(' · ')
      : '';
    $('client-count').textContent = state.clients.length; $('brand-count').textContent = state.brands.length; $('campaign-count').textContent = state.campaigns.length;
    option(state.clients, 'brand-client', 'Chọn khách hàng'); option(state.brands, 'campaign-brand', 'Chọn thương hiệu');
    $('campaigns-list').innerHTML = state.campaigns.length ? state.campaigns.map(c=>`<div class="item"><div><strong>${esc(c.name)}</strong><small>${esc(c.objective)} · ${esc(c.status)}</small></div><div class="item-actions ${state.readOnly ? 'hidden' : ''}"><button class="small secondary" data-action="plan" data-id="${esc(c.id)}">Phân rã việc</button><button class="small" data-action="strategy" data-id="${esc(c.id)}">AI chiến lược</button></div></div>`).join('') : '<div class="empty">Chưa có chiến dịch.</div>';
    $('actions-list').innerHTML = actions.length ? actions.map(a=>`<div class="item"><div><strong>${esc(a.action_kind)}</strong><small>${esc(a.state)} · ${esc(a.id.slice(0,8))}</small></div><span class="tag">${esc(a.state)}</span></div>`).join('') : '<div class="empty">Chưa có yêu cầu hành động.</div>';
    $('deliverables-list').innerHTML = deliverables.length ? deliverables.map(a=>`<div class="item"><div><strong>${esc(a.title)}</strong><small>${esc(a.status)} · ${esc(a.id.slice(0,8))}</small></div><span class="tag">${esc(a.status)}</span></div>`).join('') : '<div class="empty">Chưa có tài liệu.</div>';
  };
  const refresh = async (selected=null) => {
    portal.select(selected);
    const tenantId = state.tenantId;
    try {
      const [clients,brands,campaigns,actions,deliverables] = await Promise.all(
        ['clients','brands','campaigns','actions','deliverables'].map(n=>api(tenantPath(n)))
      );
      if (tenantId !== state.tenantId) return;
      state.clients=clients;state.brands=brands;state.campaigns=campaigns;render(actions,deliverables);
      await portal.show(deliverables,campaigns,refresh);
    } catch (error) {
      if (tenantId !== state.tenantId) return;
      state.clients = []; state.brands = []; state.campaigns = [];
      render([], []);
      $('review-panel').replaceChildren();
      throw error;
    }
  };
  $('refresh').addEventListener('click', () => refresh().catch(e=>msg(e.message, true)));
  $('campaigns-list').addEventListener('click', async event => {
    const button=event.target.closest('button[data-action]');if(!button)return;
    const id=button.dataset.id;
    button.disabled=true;
    try {
      if(button.dataset.action==='plan') {
        const result = await api(tenantPath(`campaigns/${id}/plan`),'POST');
        msg(`Tạo ${result.created_count} nhiệm vụ thuộc workflow. Đây là phân rã theo quy tắc, không phải kết quả AI.`);
      } else {
        await api(tenantPath(`campaigns/${id}/strategy`),'POST');
        msg('Đã tạo bản nháp chiến lược bằng model có cấu hình. Chưa được phê duyệt.');
      }
      await refresh();
    } catch(e) { msg(e.message,true); }
    finally {button.disabled=false;}
  });
})();
