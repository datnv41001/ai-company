(() => {
  const state = { memberships: [], readOnly: false, token: null, tenantId: null, mode: null, email: null, clients: [], brands: [], campaigns: [] };
  const $ = id => document.getElementById(id);
  let invitation = new URLSearchParams(location.hash.slice(1)).get('invite');
  if (invitation !== null) {
    document.body.classList.add('invitation-entry');
    history.replaceState(null, '', location.pathname + location.search);
    $('link-hint').classList.remove('hidden');
  }
  let workspaceRequest = null;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const msg = (text, error=false) => { $('notice').textContent = text; $('notice').className = error ? 'error' : 'ok'; };
  const api = async (path, method='GET', body=null, withCursor=false) => {
    const response = await fetch(path, {method, headers: {'Content-Type':'application/json', ...(state.token ? {'Authorization':`Bearer ${state.token}`} : {})}, ...(body ? {body: JSON.stringify(body)} : {})});
    const result = await response.json().catch(() => ({}));
    if (response.status === 429) {
      const delay = Number(response.headers.get('Retry-After'));
      throw new Error(Number.isInteger(delay) && delay > 0 ? `Vui lòng thử lại sau ${delay} giây.` : 'Vui lòng thử lại sau.');
    }
    if(!response.ok) throw Object.assign(new Error(typeof result.detail === 'string' ? result.detail : `HTTP ${response.status}`),{status:response.status});
    return withCursor ? {items:result, next:response.headers.get("X-Next-Cursor")} : result;
  };
  const workforce = createWorkforce($('workforce-panel'),api,msg);
  const portal = createReviewPanel($('review-panel'),api,msg);
  const accessPanel = createRecipientPanel($('recipient-panel'), api, msg, async tenantId => {
    invitation = null;
    document.body.classList.remove('invitation-entry');
    $('leave-invite').classList.add('hidden');
    $('link-hint').classList.add('hidden');
    $('onboarding').classList.remove('hidden');
    $('entry-title').textContent = 'Tài khoản của bạn';
    const me = await api('/api/me');
    state.memberships = me.tenants;
    $('workspace-select').replaceChildren(...me.tenants.map(m => new Option(m.organization_name, m.tenant_id)));
    $('workspace-choice').classList.toggle('hidden', me.tenants.length < 2);
    await enter(state.token, me.tenants.find(m => m.tenant_id === tenantId), me.email);
  });
  const operations = async () => {
    if (!['owner','admin'].includes(state.role)) return;
    const tenant = state.tenantId;
    const data = await api(tenantPath('operations'));
    if (state.tenantId !== tenant || !data.available) return;
    $('operations-month').textContent = 'Kỳ UTC ' + data.month + (data.enabled ? ' · Đang điều phối' : ' · Chưa bật pool');
    const labels = {'Hạn mức (micro-USD)':data.ceiling ?? 'Chưa thiết lập','Đang giữ (micro-USD)':data.held,
      'Đã ghi chi (micro-USD)':data.spent,'Lượt xử lý':data.attempts,'Đang xử lý':data.active};
    if (data.director_first_total) labels['Director đạt lần đầu'] = data.director_first_ok + '/' + data.director_first_total;
    if (data.input_tokens || data.output_tokens) labels['Token đầu vào / đầu ra'] = data.input_tokens + ' / ' + data.output_tokens;
    if (data.ceiling != null && data.held + data.spent >= data.ceiling) labels['Ngân sách'] = 'Đã chạm hạn mức';
    for (const [key,count] of Object.entries(data.outcomes || {})) labels[key] = count;
    $('operations-values').replaceChildren(...Object.entries(labels).flatMap(([label,value]) => {
      const term = document.createElement('dt'), number = document.createElement('dd');
      term.textContent = label; number.textContent = String(value); return [term,number];
    }));
    $('operations-panel').classList.remove('hidden');
  };
  $('operations-refresh').addEventListener('click', () => operations().catch(e => msg(e.message,true)));
  const tenantPath = name => `/api/tenants/${state.tenantId}/${name}`;
  const fromForm = form => Object.fromEntries(new FormData(form).entries());
  const process = (form, handler) => form.addEventListener('submit', async event => { event.preventDefault(); try { await handler(fromForm(form)); } catch (e) { msg(e.message, true); } });
  const enter = async (token, membership, email='') => {
    const tenantId = membership.tenant_id;
    $('review-panel').before($('recipient-panel'));
    state.token = token; state.tenantId = tenantId; state.mode = membership.mode; state.email = email;
    portal.setContext({tenant:tenantId,role:membership.role});
    $('operations-panel').classList.add('hidden'); $('operations-values').replaceChildren();
    accessPanel.reset(); workforce.reset();
    state.role = membership.role;
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
  const session = async (result, email) => {
    state.token = result.access_token;
    state.email = email;
    $('verify-form').reset();
    $('verify-form').classList.toggle('hidden', Boolean(result.email_verified));
    $('verify-address').textContent = email;
    $('auth').classList.add('hidden');
    $('switch-account').classList.remove('hidden');
    $('leave-invite').classList.toggle('hidden', invitation === null);
    $('who').textContent = email;
    $('onboarding').classList.toggle('hidden', !result.email_verified || invitation !== null);
    $('entry-title').textContent = result.tenants.length ? 'Tài khoản của bạn' : 'Bạn chưa tham gia workspace nào';
    if (invitation !== null) {
      $('workspace').classList.add('hidden');
      $('workspace').before($('recipient-panel'));
      if (!result.email_verified) { msg('Hãy xác minh email nhận lời mời.'); return; }
      msg('');
      try {
        await accessPanel.linked(invitation, () => {
          $('link-hint').textContent = 'Lời mời này không còn hiệu lực. Hãy mở lời mời mới nhất của workspace.';
          msg('Quyền truy cập của bạn chưa thay đổi.', true);
        });
        $('link-hint').textContent = 'Kiểm tra phạm vi và quyền trước khi tham gia.';
      } catch (error) {
        $('link-hint').textContent = error.message + ' Bạn có thể đổi tài khoản hoặc yêu cầu gửi lại.';
      }
      return;
    }
    if (!result.tenants.length) {
      $('workspace').classList.add('hidden');
      if (result.email_verified) {
        $('workspace').before($('recipient-panel'));
        await accessPanel.show(null, null, [], [], []);
        msg('Tài khoản chưa thuộc workspace nào. Bạn có thể nhận lời mời tại đây.');
      } else {
        msg('Hãy xác minh địa chỉ email của bạn.');
      }
      return;
    }
    state.memberships = result.tenants;
    $('workspace-select').replaceChildren(...result.tenants.map(m => new Option(m.organization_name, m.tenant_id)));
    $('workspace-choice').classList.toggle('hidden', result.tenants.length < 2);
    const linked=new URLSearchParams(location.search).get('workspace');
    await enter(result.access_token,result.tenants.find(m=>m.tenant_id===linked)||result.tenants[0],email);
    if(linked && !result.tenants.some(m=>m.tenant_id===linked)) msg('Bạn không có quyền mở liên kết của workspace này.',true);
  };
  process($('register-form'), async data => {
    await api('/api/auth/register', 'POST', data);
    $('register-form').reset();
    const login = $('login-form');
    login.elements.email.value = data.email;
    login.elements.password.value = '';
    login.elements.password.focus();
    msg('Đã nhận yêu cầu. Đăng nhập để tiếp tục xác minh hoặc mở tài khoản của bạn.');
  });
  $('leave-invite').onclick = async () => {
    invitation = null;
    document.body.classList.remove('invitation-entry');
    $('link-hint').classList.add('hidden');
    try { await session({...await api('/api/me'), access_token:state.token},state.email); }
    catch (error) { msg(error.message, true); }
  };
  $('switch-account').onclick = () => {
    if (invitation !== null) history.replaceState(null, '', location.pathname + '#invite=' + encodeURIComponent(invitation));
    location.reload();
  };
  $('workspace-form').addEventListener('input', () => { workspaceRequest = null; });
  process($('workspace-form'), async data => {
    workspaceRequest ||= crypto.randomUUID();
    const button = $('workspace-form').querySelector('button');
    button.disabled = true;
    try {
      const result = await api('/api/me/workspaces', 'POST', {...data, request_id:workspaceRequest});
      const me = await api('/api/me');
      await session({...me,access_token:state.token},me.email);
      await enter(state.token,me.tenants.find(m => m.tenant_id === result.tenant_id),me.email);
      $('workspace-form').reset(); $('new-workspace').open = false; workspaceRequest = null;
    } finally { button.disabled = false; }
  });
  process($('login-form'), async data => session(await api('/api/auth/login', 'POST', data), data.email));
  process($('verify-form'), async data => {
    await api('/api/auth/verify-email', 'POST', data);
    await session({...await api('/api/me'), access_token:state.token}, state.email);
  });
  $('resend-proof').onclick = async () => {
    try { await api('/api/auth/request-verification', 'POST'); msg('Đã gửi mã mới vào hộp thư phát triển.'); }
    catch (error) { msg(error.message, true); }
  };
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
    $('campaigns-list').innerHTML = state.campaigns.length ? state.campaigns.map(c=>`<div class="item"><div><strong>${esc(c.name)}</strong><small>${esc(c.objective)} · ${esc(c.status)}</small></div><div class="item-actions ${state.readOnly ? 'hidden' : ''}"><button class="small secondary" data-action="plan" data-id="${esc(c.id)}">Phân rã việc</button></div></div>`).join('') : '<div class="empty">Chưa có chiến dịch.</div>';
    $('actions-list').innerHTML = actions.length ? actions.map(a=>`<div class="item"><div><strong>${esc(a.action_kind)}</strong><small>${esc(a.state)} · ${esc(a.id.slice(0,8))}</small></div><span class="tag">${esc(a.state)}</span></div>`).join('') : '<div class="empty">Chưa có yêu cầu hành động.</div>';
    $('deliverables-list').innerHTML = deliverables.length ? deliverables.map(a=>`<div class="item"><div><strong>${esc(a.title)}</strong><small>${esc(a.status)} · ${esc(a.id.slice(0,8))}</small></div><span class="tag">${esc(a.status)}</span></div>`).join('') : '<div class="empty">Chưa có tài liệu.</div>';
  };
  const refresh = async (selected=null) => {
    workforce.pause();
    portal.select(selected);
    const tenantId = state.tenantId;
    try {
      const [clients,brands,campaigns,actions,deliverables] = await Promise.all(
        ['clients','brands','campaigns','actions','deliverables'].map(n=>api(tenantPath(n)))
      );
      if (tenantId !== state.tenantId) return;
      state.clients=clients;state.brands=brands;state.campaigns=campaigns;render(actions,deliverables);
      await Promise.all([operations(), workforce.show(tenantId,state.role,campaigns.map(c=>({...c,client_id:brands.find(b=>b.id===c.brand_id)?.client_id}))),portal.show(deliverables,campaigns,refresh),
        accessPanel.show(tenantId, state.role, clients, brands, campaigns)]);
    } catch (error) {
      if (tenantId !== state.tenantId) return;
      state.clients = []; state.brands = []; state.campaigns = [];
      render([], []);
      $('operations-panel').classList.add('hidden'); $('operations-values').replaceChildren();
    accessPanel.reset(); workforce.reset();
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

      }
      await refresh();
    } catch(e) { msg(e.message,true); }
    finally {button.disabled=false;}
  });
})();
