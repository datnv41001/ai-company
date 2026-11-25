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
  let workspaceGeneration = 0;
  let overviewRequest = 0;
  let refreshSequence = 0;
  let profileRemoved = false;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const msg = (text, error=false) => { $('notice').textContent = text; $('notice').className = error ? 'error' : 'ok'; };
  function validationMessage(detail) {
    const fallback = 'Dữ liệu chưa hợp lệ. Kiểm tra các trường bắt buộc và định dạng đã nhập.';
    if (typeof detail === 'string') {
      if (detail.includes("Check the objective's parent and campaign scope") || detail.includes('Objective hierarchy or parent identity differs')) {
        return 'Kiểm tra mục tiêu cha và chiến dịch. Mục tiêu thương hiệu cần mục tiêu doanh nghiệp làm cha. Mục tiêu chiến dịch cần mục tiêu thương hiệu và chiến dịch tương ứng.';
      }
      // Some older commands serialize Pydantic errors as text. They can include raw inputs.
      const trimmed = detail.trimStart();
      return trimmed.startsWith('[') || trimmed.startsWith('{') ? fallback : detail || fallback;
    }
    if (!Array.isArray(detail)) return fallback;
    const labels = {name:'Tên', title:'Tên bản nháp', email:'Email', password:'Mật khẩu', amount:'Giá', currency:'Tiền tệ',
      parent:'Mục tiêu cha', campaign_id:'Chiến dịch', owner:'Người phụ trách', valid_from:'Ngày bắt đầu', valid_until:'Ngày kết thúc'};
    const fields = [...new Set(detail.flatMap(issue => (Array.isArray(issue?.loc) ? issue.loc : [])
      .filter(key => Object.hasOwn(labels, key)).map(key => labels[key])))];
    return fields.length ? 'Kiểm tra trường ' + fields.join(', ') + ' rồi thử lại.' : fallback;
  }
  const claims = token => JSON.parse(atob(token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));
  const cookie = name => document.cookie.split('; ').find(v => v.startsWith(name+'='))?.slice(name.length+1);
  let accountGeneration = 0, browserContext = null, switching = false;
  const changed = () => new Error('Phiên hoặc tài khoản đã thay đổi. Vui lòng đăng nhập lại.');
  function checkAccount(generation) {
    if (generation !== accountGeneration || switching || (browserContext && browserContext !== cookie('__Host-amc-context'))) throw changed();
  }
  function familyLock(sid, task) {
    if (!navigator.locks) throw Error('Trình duyệt cần hỗ trợ khóa phiên. Vui lòng đăng nhập lại trên HTTPS.');
    return navigator.locks.request('amc-device-'+sid, task);
  }
  let refreshing = null;
  async function renew(generation) {
    if (refreshing?.generation === generation) return refreshing.promise;
    const sid = claims(state.token).sid;
    const promise = familyLock(sid, async () => {
      checkAccount(generation);
      const csrf = cookie('__Host-amc-csrf-'+sid);
      if (!csrf) throw changed();
      const response = await fetch('/api/auth/refresh', {method:'POST', headers:{'X-AMC-CSRF':csrf,'X-AMC-Session':sid}});
      if (!response.ok) throw Error('Vui lòng đăng nhập lại để tiếp tục.');
      const token = (await response.json()).access_token;
      checkAccount(generation);
      if (claims(token).sid !== sid) throw changed();
      state.token = token;
    }).finally(() => { if (refreshing?.generation === generation) refreshing = null; });
    refreshing = {generation, promise};
    return promise;
  }
  const api = async (path, method='GET', body=null, withCursor=false, signal) => {
    const generation = accountGeneration;
    checkAccount(generation);
    if (state.token && claims(state.token).exp <= Date.now()/1000 + 15) await renew(generation);
    checkAccount(generation);
    const response = await fetch(path, {method, signal, headers: {'Content-Type':'application/json', ...(state.token ? {'Authorization':`Bearer ${state.token}`} : {})}, ...(body ? {body: JSON.stringify(body)} : {})});
    const result = await response.json().catch(() => ({}));
    checkAccount(generation);
    if (response.status === 429) {
      const delay = Number(response.headers.get('Retry-After'));
      throw new Error(Number.isInteger(delay) && delay > 0 ? `Vui lòng thử lại sau ${delay} giây.` : 'Vui lòng thử lại sau.');
    }
    if(!response.ok) throw Object.assign(new Error(response.status === 422 ? validationMessage(result.detail) :
      typeof result.detail === 'string' ? result.detail : `HTTP ${response.status}`),{status:response.status});
    return withCursor ? {items:result, next:response.headers.get("X-Next-Cursor")} : result;
  };
  const knowledge = createKnowledgePanel($('knowledge-panel'), api, refreshWorkforce);
  const campaignLab = createCampaignLab(api);
  const screens = createWorkspaceScreens(id => {
    const membership=state.memberships.find(m=>m.tenant_id===id);
    if(!membership) return false;
    enter(state.token,membership,state.email).catch(e=>msg(e.message,true));
    return true;
  });
  const command = createCommandCenter(api,screens);
  const workforce = createWorkforce($('workforce-panel'),api,msg,(tenant,briefs,runs)=>command.activity(tenant,briefs,runs));
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
    const generation = workspaceGeneration;
    const data = await api(tenantPath('operations'));
    if (workspaceGeneration !== generation || state.tenantId !== tenant || !data.available) return;
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
  const enter = async (token, membership, email='', lostProfile=false) => {
    checkAccount(accountGeneration);
    const tenantId = membership.tenant_id;
    const entry = ++workspaceGeneration;
    profileRemoved = lostProfile;
    overviewRequest++;
    command.clear();
    $('workspace').dataset.loading='true';
    document.body.dataset.access = membership.role === 'client_viewer' ? 'portal' : 'staff';
    document.body.dataset.role = membership.role;
    screens.enter(membership,lostProfile);
    $('workspace-choice').classList.remove('hidden');
    knowledge.reset();
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
    msg('');
    try { await refresh(); }
    finally {
      if (entry===workspaceGeneration) delete $('workspace').dataset.loading;
    }
  };
  const session = async (result, email) => {
    checkAccount(accountGeneration);
    clearWorkspacePresentation();
    document.body.dataset.access = 'account';
    $('workspace-choice').classList.add('hidden');
    state.userId = result.user_id || result.id;
    state.token = result.access_token;
    state.email = email;
    $('verify-form').reset();
    $('verify-form').classList.toggle('hidden', Boolean(result.email_verified));
    $('verify-address').textContent = email;
    $('auth').classList.add('hidden');
    $('switch-account').classList.remove('hidden');
    $('device-panel').classList.remove('hidden');
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
  function leaveTab() {
    ++accountGeneration;
    switching = true;
    workspaceGeneration++;
    overviewRequest++;
    command.clear();
    knowledge.reset();
    if (invitation !== null) history.replaceState(null, '', location.pathname + '#invite=' + encodeURIComponent(invitation));
    location.reload();
  }
  $('leave-tab').onclick = leaveTab;
  $('switch-account').onclick = async () => {
    if (switching) return;
    ++accountGeneration;
    switching = true;
    try {
      if (state.token) {
        const token = state.token, sid = claims(token).sid;
        const logout = async () => {
          let response = await fetch('/api/auth/logout',{method:'POST',headers:{Authorization:'Bearer '+token}});
          const csrf = cookie('__Host-amc-csrf-'+sid);
          if (response.status === 401 && csrf) {
            response = await fetch('/api/auth/logout-cookie',{method:'POST',headers:{'X-AMC-CSRF':csrf,'X-AMC-Session':sid}});
          }
          if (!response.ok) throw Error('Máy chủ chưa xác nhận thu hồi phiên này. Bạn có thể thử lại hoặc về đăng nhập trên tab này.');
        };
        await (navigator.locks ? familyLock(sid, logout) : logout());
      }
      leaveTab();
    } catch(error) { switching = false; $('leave-tab').classList.remove('hidden'); msg(error.message,true); }
  };
  async function deviceList() {
    const list = $('device-list');
    const devices = await api('/api/me/sessions');
    list.replaceChildren();
    for (const device of devices) {
      const row = document.createElement('li');
      row.append(document.createTextNode(device.device+' · '+new Date(device.last_seen*1000).toLocaleString()+(device.current?' · Phiên hiện tại ': ' ')));
      if (!device.current) {
        const button = document.createElement('button');
        button.type = 'button'; button.textContent = 'Thu hồi';
        button.onclick = async () => {
          try { await api('/api/me/sessions/'+device.id,'DELETE'); await deviceList(); }
          catch(error) { msg(error.message,true); }
        };
        row.append(button);
      }
      list.append(row);
    }
  }
  $('device-panel').ontoggle = () => { if ($('device-panel').open) deviceList().catch(error=>msg(error.message,true)); };
  process($('device-reauth'),async data => {
    try { await api('/api/auth/reauthenticate','POST',data); msg('Đã xác thực lại. Bạn có thể thu hồi phiên khác.'); }
    finally { $('device-reauth').reset(); }
  });
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
  process($('login-form'), async data => {
    const generation = ++accountGeneration;
    const login = async () => {
      checkAccount(generation);
      const result = await api('/api/auth/login', 'POST', data);
      if (result.browser_context !== cookie('__Host-amc-context')) throw changed();
      browserContext = result.browser_context;
      return result;
    };
    const result = await (navigator.locks ? navigator.locks.request('amc-account-login',login) : login());
    checkAccount(generation);
    await session(result,data.email);
  });
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
    if (membership) {
      screens.switching(membership.tenant_id);
      enter(state.token, membership, state.email).catch(e => msg(e.message, true));
    }
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
    option(state.clients, 'brand-client', 'Chọn khách hàng'); option(state.brands, 'campaign-brand', 'Chọn thương hiệu');
    campaignLab.scope(state.tenantId, state.readOnly ? [] : state.campaigns);
    $('campaigns-list').innerHTML = state.campaigns.length ? state.campaigns.map(c=>`<div class="item"><div><strong>${esc(c.name)}</strong><small>${esc(c.objective)} · ${esc(c.status)}</small></div><div class="item-actions ${state.readOnly ? 'hidden' : ''}"><button class="small secondary" data-action="plan" data-id="${esc(c.id)}">Phân rã việc</button></div></div>`).join('') : '<div class="empty">Chưa có chiến dịch.</div>';
    $('actions-list').innerHTML = actions.length ? actions.map(a=>`<div class="item"><div><strong>${esc(a.action_kind)}</strong><small>${esc(a.state)} · ${esc(a.id.slice(0,8))}</small></div><span class="tag">${esc(a.state)}</span></div>`).join('') : '<div class="empty">Chưa có yêu cầu hành động.</div>';
    $('deliverables-list').innerHTML = deliverables.length ? deliverables.map(a=>`<div class="item"><div><strong>${esc(a.title)}</strong><small>${esc(a.id.slice(0,8))}</small></div><span class="tag">${esc(deliverableStage(a))}</span></div>`).join('') : '<div class="empty">Chưa có tài liệu.</div>';
  };
  function clearWorkspacePresentation() {
    workspaceGeneration++;
    refreshSequence++;
    overviewRequest++;
    profileRemoved=false;
    screens.reset();
    command.clear(); knowledge.reset(); workforce.reset(); accessPanel.reset(); portal.setContext(null);
    state.clients=[]; state.brands=[]; state.campaigns=[];
    render([],[]);
    $('operations-panel').classList.add('hidden');
    $('operations-values').replaceChildren();
    $('operations-month').textContent='';
    $('workspace').classList.add('hidden');
    delete $('workspace').dataset.loading;
    $('workspace-choice').classList.add('hidden');
  }
  function authLost() {
    clearWorkspacePresentation();
    state.token=null; state.tenantId=null; state.role=null; state.email=null; state.userId=null; state.memberships=[];
    delete document.body.dataset.access; delete document.body.dataset.role;
    $('workspace-select').replaceChildren(); $('who').textContent='Chưa đăng nhập';
    for (const id of ['onboarding','switch-account','verify-form']) $(id).classList.add('hidden');
    $('auth').classList.remove('hidden');
    msg('Phiên hoặc quyền truy cập đã thay đổi. Hãy đăng nhập lại để tiếp tục.',true);
  }
  async function changeMembership(me, membership) {
    if (!membership) {
      await session({...me,access_token:state.token},state.email);
      msg('Quyền truy cập workspace đã thay đổi.',true);
      return;
    }
    const lostProfile=document.body.dataset.access==='staff' && membership.role==='client_viewer';
    state.memberships=me.tenants;
    $('workspace-select').replaceChildren(...me.tenants.map(m=>new Option(m.organization_name,m.tenant_id)));
    $('workspace-choice').classList.toggle('hidden',me.tenants.length<2);
    // Keep the chosen tenant on a role change. A fresh login or explicit workspace switch resets this notice.
    await enter(state.token,membership,state.email,lostProfile);
  }
  const refresh = async (selected=null) => {
    workforce.pause();
    portal.select(selected);
    const tenantId = state.tenantId;
    const generation = workspaceGeneration;
    const sequence = ++refreshSequence;
    const dashboardTicket = ++overviewRequest;
    try {
      const me = await api('/api/me');
      if (generation !== workspaceGeneration || sequence !== refreshSequence) return;
      const membership = me.tenants.find(m=>m.tenant_id===tenantId);
      if (!membership || membership.role!==state.role) {
        await changeMembership(me,membership);
        return;
      }
      const [clients,brands,campaigns,actions,deliverables] = await Promise.all(
        ['clients','brands','campaigns','actions','deliverables'].map(n=>api(tenantPath(n)))
      );
      if (generation !== workspaceGeneration || sequence !== refreshSequence) return;
      state.clients=clients;state.brands=brands;state.campaigns=campaigns;render(actions,deliverables);
      await Promise.all([dashboardTicket===overviewRequest ? showCommand({clients,brands,campaigns,deliverables}) : null, profileRemoved ? knowledge.permissionChanged() : knowledge.show({
        tenant: tenantId, actor: state.userId, role: state.role, mode: state.mode, campaigns,
        requestedBrand: document.body.dataset.screen==='knowledge' ? screens.params().get('brand') : null,
        organization: state.memberships.find(m => m.tenant_id === tenantId)?.organization_name || '',
        clients, brands
      }), operations(), refreshWorkforce(tenantId),portal.show(deliverables,campaigns,refresh),
        accessPanel.show(tenantId, state.role, clients, brands, campaigns)]);
    } catch (error) {
      if (generation !== workspaceGeneration || sequence !== refreshSequence) return;
      if ([401,403].includes(error.status)) { authLost(); return; }
      state.clients = []; state.brands = []; state.campaigns = [];
      render([], []);
      command.clear();
      $('operations-panel').classList.add('hidden'); $('operations-values').replaceChildren();
      knowledge.reset(); accessPanel.reset(); workforce.reset();
      $('review-panel').replaceChildren();
      throw error;
    }
  };
  function refreshWorkforce(tenant) {
    if (tenant !== state.tenantId) return;
    const campaigns=state.campaigns.map(c=>({...c,client_id:state.brands.find(b=>b.id===c.brand_id)?.client_id}));
    return workforce.show(tenant,state.role,campaigns,undefined,state.mode);
  }
  function showCommand(data) {
    if (document.hidden) { command.clear(); return; }
    return command.show({...data,tenant:state.tenantId,role:state.role,mode:state.mode,
      organization:state.memberships.find(m=>m.tenant_id===state.tenantId)?.organization_name,
      onRestricted:code=>[401,403].includes(code) ? authLost() : msg('Chiến dịch không còn hiển thị. Làm mới workspace để cập nhật.',true)});
  }
  async function refreshCommand() {
    const generation = workspaceGeneration, ticket = ++overviewRequest;
    const current = () => generation === workspaceGeneration && ticket === overviewRequest;
    if (document.body.dataset.access !== 'staff') return;
    const button=$('command-refresh');
    button.disabled=true;
    try {
      const me = await api('/api/me');
      if (!current()) return;
      const membership = me.tenants.find(m=>m.tenant_id===state.tenantId);
      if (!membership || membership.role!==state.role) {
        await changeMembership(me,membership);
        return;
      }
      const result = await Promise.all(['clients','brands','campaigns','deliverables'].map(name=>api(tenantPath(name))));
      if (!current()) return;
      const [clients,brands,campaigns,deliverables]=result;
      await showCommand({clients,brands,campaigns,deliverables});
      if (!current() || !campaigns.length) return;
      const base=tenantPath('workforce');
      try {
        const [briefs,runs]=await Promise.all([api(base+'/briefs'),api(base+'/runs')]);
        if (current()) command.activity(state.tenantId,briefs,runs);
      } catch(error) {
        if (!current()) return;
        if ([401,403].includes(error.status)) { authLost(); return; }
        command.activity(state.tenantId,null,null);
      }
    } catch (error) {
      if (!current()) return;
      if ([401,403].includes(error.status)) { authLost(); return; }
      command.clear();
      msg('Chưa tải được dữ liệu điều hành. Hãy làm mới workspace.',true);
    } finally {
      if (current()) button.disabled=false;
    }
  }
  $('command-refresh').addEventListener('click',refreshCommand);
  document.addEventListener('visibilitychange',()=>{
    if (document.hidden && document.body.dataset.access==='staff') {
      overviewRequest++;
      refreshSequence++;
      command.clear();
    } else if (!document.hidden) void refreshCommand();
  });
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
