function createKnowledgePanel(root, api) {
  const byId = id => document.getElementById(id);
  const context = byId('knowledge-context');
  const content = byId('knowledge-content');
  const status = byId('knowledge-status');
  const progress = byId('knowledge-progress');
  const catalogDrawer = byId('catalog-drawer');
  const catalog = createCatalogPane(byId('catalog-pane'),api);
  let catalogContext = null;
  function openCatalog() {
    if (!data || !brand || !catalogDrawer.open) return;
    const role = data.can_edit ? scope.role : 'viewer';
    const key = [generation,scope.actor,scope.tenant,client,brand,role].join('/');
    if (catalogContext === key) return;
    catalogContext = key;
    catalog.show({...scope,client,brand,role}).catch(() => {
      if (catalogContext === key) {catalogContext=null;byId('catalog-pane').textContent='Chưa tải được danh mục. Đóng và mở lại để thử.';}
    });
  }
  catalogDrawer.addEventListener('toggle',()=>{if(catalogDrawer.open)openCatalog();else{catalog.reset();catalogContext=null;}});
  const names = {name:'Tên doanh nghiệp', sells:'Sản phẩm hoặc dịch vụ', audience:'Khách hàng mục tiêu', goal:'Mục tiêu'};
  const hints = {name:'Tên dùng khi giới thiệu doanh nghiệp', sells:'Bạn cung cấp sản phẩm hoặc dịch vụ nào?', audience:'Ai thường mua hoặc sử dụng?', goal:'Bạn muốn Marketing giúp đạt điều gì?'};
  const modes = {inherit:'Từ hồ sơ doanh nghiệp', override:'Điều chỉnh cho thương hiệu', empty:'Chủ động để trống'};
  const html = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fields = Object.keys(names);
  const briefSlots = {product:'Sản phẩm hoặc dịch vụ', audience:'Hồ sơ khách hàng', objective:'Mục tiêu đã khai báo'};
  const statusNames = {draft:'Bản nháp', approved:'Đã duyệt', superseded:'Đã thay thế', withdrawn:'Đã thu hồi', disputed:'Tranh chấp', expired:'Hết hạn', pending_effective:'Chưa có hiệu lực'};
  let scope, client, brand, view, data, edit, command, brief, conflict, reentry;
  let generation = 0;
  let reading;
  let claimDesk;
  const contextKey = () => `amc.knowledge.${scope.actor}.${scope.tenant}`;
  const scopeKey = () => `${contextKey()}.${client}.${brand}`;
  const profilePath = () => `/api/tenants/${scope.tenant}/clients/${client}/business-profile`;
  const brandPath = () => `/api/tenants/${scope.tenant}/clients/${client}/brands/${brand}/business-workspace`;
  const commandPath = kind => kind === 'company' ? profilePath() : brandPath();
  const objectName = (rows,id) => rows.find(row=>row.id===id)?.name || '';
  const read = path => api(path,'GET',null,false,reading.signal);
  const current = token => token === generation;
  const hasChanges = () => edit && (view === 'briefs'
    ? Object.keys(edit.picks || {}).length > 0 || (edit.title !== undefined && edit.title !== 'Brief nghiên cứu · '+objectName(scope.brands,brand))
    : Object.keys(changes()).length > 0);
  const mayLeave = () => !hasChanges() || Boolean(command) || window.confirm('Bạn có thay đổi chưa lưu. Bỏ những thay đổi này để chuyển mục?');
  const valueText = value => value || 'Chưa có thông tin';
  function remembered(key) {
    try { return JSON.parse(sessionStorage.getItem(key)); } catch { return null; }
  }
  function remember(key,value) {
    try {
      if (value === null) sessionStorage.removeItem(key);
      else sessionStorage.setItem(key,JSON.stringify(value));
    } catch { /* Same-page editing still works when browser storage is unavailable. */ }
  }
  function tell(message, error=false) {
    status.textContent = message;
    status.classList.toggle('knowledge-error',error);
    if (error) { status.tabIndex = -1; status.focus(); }
  }
  function clearView() {
    claimDesk?.reset();
    claimDesk=null;
    catalog.reset();
    catalogContext=null;
    catalogDrawer.hidden=true;
    generation++;
    reading?.abort();
    reading = new AbortController();
    data = edit = command = brief = conflict = reentry = null;
    view = 'company';
    content.replaceChildren();
    progress.textContent = '';
    tell('');
  }
  function reset() {
    clearView();
    scope = client = brand = null;
    root.classList.add('hidden');
    byId('knowledge-nav').classList.add('hidden');
    byId('knowledge-org').textContent = '';
    context.replaceChildren();
  }
  function options(rows, selected, placeholder) {
    return `<option value="">${placeholder}</option>`+rows.map(row=>`<option value="${html(row.id)}"${row.id===selected?' selected':''}>${html(row.name)}</option>`).join('');
  }
  function scopedBrands() { return scope.brands.filter(row=>row.client_id===client); }
  function selectors() {
    const brands = scopedBrands();
    context.innerHTML = `<label>Khách hàng<select id="knowledge-client">${options(scope.clients,client,'Chọn khách hàng')}</select></label>
      <label>Thương hiệu<select id="knowledge-brand" ${client?'':'disabled'}>${options(brands,brand,'Chọn thương hiệu')}</select></label>`;
  }
  function emptyContext() {
    const target = !scope.clients.length ? 'client' : client && !scopedBrands().length ? 'brand' : null;
    if (target && ['owner','admin','editor'].includes(scope.role)) {
      const label = target==='client' ? 'khách hàng' : 'thương hiệu';
      content.innerHTML = `<p>Thêm ${label} để bắt đầu hồ sơ.</p><button type="button" data-create="${target}">Thêm ${label}</button>`;
    } else {
      tell(scope.clients.length ? 'Chọn khách hàng và thương hiệu để mở hồ sơ.' : 'Chưa có hồ sơ trong phạm vi của bạn.');
    }
  }
  const revokedMessage = 'Quyền xem hồ sơ đã thay đổi. Hãy liên hệ quản trị viên hoặc làm mới workspace.';
  function lockout() {
    clearView();
    context.replaceChildren();
    tell(revokedMessage,true);
  }
  function permissionChanged() {
    reset();
    root.classList.remove('hidden');
    tell(revokedMessage,true);
  }
  function failed(error, token, retry='load') {
    if (!current(token)) return;
    if ([401,403,404].includes(error.status)) return lockout();
    tell('Chưa tải được dữ liệu. Vui lòng kiểm tra kết nối rồi thử lại.',true);
    content.innerHTML = `<button type="button" data-action="${retry}">Thử lại</button>`;
  }
  async function revalidate() {
    if(claimDesk)await claimDesk.revalidate();
    if(!scope || !brand || !data)return;
    const token=generation, previous=data;
    try {
      const latest=await read(brandPath());
      if(!current(token) || data!==previous)return;
      if(previous.can_edit && !latest.can_edit){
        clearView();data=latest;render();tell('Quyền của bạn đã chuyển sang chỉ xem.',true);
      } else if(!hasChanges() && !command && !conflict && !reentry &&
        (latest.company_revision!==previous.company_revision || latest.brand_revision!==previous.brand_revision ||
          latest.briefs.map(b=>b.id).join()!==previous.briefs.map(b=>b.id).join())){
        data=latest;render();
      }
    } catch(error){
      if(!current(token))return;
      if([401,403,404].includes(error.status))return lockout();
      tell('Chưa kiểm tra được bản mới. Hãy kiểm tra kết nối rồi làm mới hồ sơ.');
    }
  }
  async function selectScope(nextClient, nextBrand) {
    clearView();
    client = nextClient;
    const rows = scopedBrands();
    brand = rows.some(b=>b.id===nextBrand) ? nextBrand : rows.length===1 ? rows[0].id : '';
    remember(contextKey(),{client,brand});
    selectors();
    if (!client || !brand) return emptyContext();
    await loadWorkspace();
  }
  async function show(next) {
    if (!next.actor || !['owner','admin','editor','viewer'].includes(next.role)) return reset();
    const same = next.actor === scope?.actor && next.tenant === scope?.tenant && next.role === scope?.role;
    scope = next;
    root.classList.remove('hidden');
    byId('knowledge-nav').classList.remove('hidden');
    byId('knowledge-org').textContent = next.organization;
    if(same && client && brand && (!next.clients.some(row=>row.id===client) || !scopedBrands().some(row=>row.id===brand))){
      // A narrower directory can be the first response after a grant changes.
      // Purge old content and explain why it disappeared even without a detail GET.
      remember(contextKey(),null);
      client=brand=null;
      return lockout();
    }
    if (same && client && next.clients.some(row=>row.id===client) && scopedBrands().some(row=>row.id===brand)) {
      // A whole-workspace refresh revalidates access without erasing an in-progress edit.
      selectors();
      await revalidate();
      return;
    }
    const direct = next.brands.find(b=>b.id===next.requestedBrand && next.clients.some(c=>c.id===b.client_id));
    const last = direct ? {client:direct.client_id,brand:direct.id} : remembered(contextKey());
    const clientId = next.clients.some(row=>row.id===last?.client) ? last.client : next.clients.length===1 ? next.clients[0].id : '';
    await selectScope(clientId,last?.brand);
  }
  async function loadWorkspace() {
    const token = generation;
    tell('Đang tải hồ sơ…');
    try {
      const latest = await read(brandPath());
      if (!current(token)) return;
      data = latest;
      const pending = remembered(scopeKey()+'.command');
      if (pending) {
        command ||= pending;
        return await recover(token);
      }
      const open = remembered(scopeKey()+'.brief');
      if (open && latest.briefs.some(b=>b.id===open)) return await openBrief(open);
      tell('');
      render();
    } catch(error){failed(error,token);}
  }
  function baseValues(kind) {
    if(kind==='company') return Object.fromEntries(fields.map(k=>[k,data.company[k] || '']));
    return Object.fromEntries(fields.map(k=>[k,{mode:data.fields[k].mode,value:data.fields[k].mode==='override'?data.fields[k].value || '':''}]));
  }
  function fieldBlock(k) {
    const field = data.fields[k];
    if (view==='company') return `<label for="knowledge-${k}">${names[k]}</label><input id="knowledge-${k}" name="${k}" maxlength="1800" value="${html(edit[k])}" placeholder="${html(hints[k])}" ${data.can_edit?'':'readonly'}>`;
    return `<label for="knowledge-${k}-mode">${names[k]}</label>
      <select id="knowledge-${k}-mode" name="${k}-mode" ${data.can_edit?'':'disabled'}>${Object.entries(modes).map(([mode,label])=>`<option value="${mode}" ${edit[k].mode===mode?'selected':''}>${label}</option>`).join('')}</select>
      <input aria-label="Giá trị riêng · ${names[k]}" name="${k}" id="knowledge-${k}" maxlength="1800" value="${html(edit[k].value)}" ${edit[k].mode==='override'?'':'hidden'} ${data.can_edit?'':'readonly'}>
      <small class="knowledge-source">${html(valueText(field.value))} · ${field.source==='company'?'Doanh nghiệp':'Thương hiệu'}, bản ${Number(field.source_revision)}${field.override_revision ? ' · Lần điều chỉnh '+Number(field.override_revision):''}</small>`;
  }
  function changes() {
    if (view==='briefs' || !data || !edit) return {};
    const base = baseValues(view);
    return Object.fromEntries(fields.filter(k=>JSON.stringify(base[k])!==JSON.stringify(edit[k])).map(k=>[k,edit[k]]));
  }
  function summary() {
    return `<dl class="knowledge-summary">${fields.map(k=>`<div><dt>${names[k]}</dt><dd>${html(valueText(brief.fields[k]?.value ?? (typeof brief.fields[k]==='string'?brief.fields[k]:'')))}</dd></div>`).join('')}</dl>`;
  }
  async function chooseBriefData() {
    const host = byId('brief-options');
    if (!host) return;
    const token = generation;
    const serial = String(Number(host.dataset.request || 0) + 1);
    host.dataset.request = serial;
    const query = byId('brief-search')?.value || '';
    try {
      const slots = Object.keys(briefSlots);
      const lists = await Promise.all(slots.map(slot => read(brandPath()+'/brief-options?slot='+slot+'&q='+encodeURIComponent(query))));
      if (!current(token) || !host.isConnected || host.dataset.request !== serial) return;
      if (!byId('brief-search')) {
        host.innerHTML = '<label>Tìm trong danh mục<input id="brief-search" maxlength="100"></label><button class="secondary" type="button" data-action="brief-options">Tìm dữ liệu</button><div id="brief-selectors" class="knowledge-grid"></div>';
      }
      byId('brief-selectors').innerHTML = slots.map((slot, index) => {
        const list = lists[index];
        const chosen = edit.picks?.[slot];
        const rows = list.items.filter(r => r.state === 'draft' || r.state === 'approved');
        let choices = rows.map(r=>`<option value="${html(r.id)}" ${r.id===chosen?'selected':''}>${html(r.name)}</option>`).join('');
        if (chosen && !rows.some(r=>r.id===chosen)) {
          choices += `<option selected value="${html(chosen)}">${html(edit.pickNames[slot])}</option>`;
        }
        return `<label>${briefSlots[slot]}<select id="brief-${slot}" data-brief-slot="${slot}"><option value="">Chưa chọn</option>${choices}</select></label>${list.more?'<small>Nhập tên để thu hẹp kết quả.</small>':''}`;
      }).join('');
      tell('Đã tải danh mục của thương hiệu.');
    } catch(error) {
      if (current(token) && host.isConnected) failed(error,token);
    }
  }
  function attachedRecords() {
    const selections = Object.entries(brief.selections || {});
    if (!selections.length) return '';
    return '<h5>Dữ liệu danh mục đã ghim</h5><dl class="knowledge-summary">'+selections.map(([slot,r])=>{
      const basis = r.basis==='hypothesis' ? ' · Giả thuyết' : r.basis==='fact' ? ' · Dữ kiện do doanh nghiệp khai báo' : '';
      const state = r.current_state!==r.saved_state ? ' · Hiện tại: '+(statusNames[r.current_state] || r.current_state) : '';
      const value = r.available ? r.label+' · Bản '+r.revision+' · '+(statusNames[r.saved_state] || r.saved_state)+basis+state : 'Không còn quyền xem';
      return `<div><dt>${html(briefSlots[slot])}</dt><dd>${html(value)}</dd></div>`;
    }).join('')+'</dl>';
  }
  function briefScreen() {
    const checks={source_validation:'Chưa đối chiếu giá, điều kiện bán và nguồn xác nhận.',kpi_baseline:'KPI ban đầu · Chưa có số liệu.',kpi_target:'KPI mục tiêu · Chưa có chỉ tiêu đã xác nhận.',kpi_actual:'KPI thực tế · Chưa có số liệu.'};
    const list = data.briefs.map(b=>`<li><button type="button" class="knowledge-link" data-brief="${html(b.id)}">${html(b.title)}</button></li>`).join('');
    return `${brief?`<article class="knowledge-brief"><h4 tabindex="-1" id="knowledge-open-title">${html(brief.title)}</h4><p>Nháp nội bộ · Từ bản doanh nghiệp ${Number(brief.company_revision)} và bản thương hiệu ${Number(brief.brand_revision)}.</p>
      ${summary()}${attachedRecords()}<h5>Cần làm rõ trước khi sử dụng</h5><ul>${brief.missing.map(k=>`<li>${html(hints[k])}</li>`).join('')}${brief.pending_checks.map(k=>`<li>${html(checks[k] || 'Cần xác nhận bổ sung.')}</li>`).join('')}</ul></article>`:''}
      ${data.can_edit?`<form id="knowledge-new-brief"><h4>Chuẩn bị brief</h4><p>Ghim thông tin đã lưu cho ${html(objectName(scope.brands,brand))}. Bạn có thể tạo nháp khi hồ sơ còn thiếu.</p><label>Tên brief<input name="title" required maxlength="160" value="${html(edit?.title??'Brief nghiên cứu · '+objectName(scope.brands,brand))}"></label><button class="secondary" type="button" data-action="brief-options">Chọn dữ liệu từ danh mục</button><div id="brief-options"></div><button type="submit">Tạo brief nháp</button></form>`:''}
      <h4>Brief đã lưu của bạn</h4>${list?`<ul class="knowledge-list">${list}</ul>`:'<p>Bạn chưa có brief nào ở thương hiệu này.</p>'}`;
  }
  function render() {
    if (!data) return;
    claimDesk?.reset();
    claimDesk=null;
    catalogDrawer.hidden=false;
    openCatalog();
    progress.textContent = `${data.completion.filled}/${data.completion.total} trường đã lưu cho thương hiệu`;
    const tabs = {company:'Hồ sơ chung',brand:'Theo thương hiệu',briefs:'Brief nháp',claims:'Nguồn và nhận định'};
    if(view==='claims'){
      edit=null;
      content.innerHTML=`<div class="knowledge-tabs" role="group" aria-label="Nội dung hồ sơ">${Object.entries(tabs).map(([id,label])=>`<button type="button" data-view="${id}" aria-pressed="${view===id}">${label}</button>`).join('')}</div><div id="knowledge-claim-desk"></div>`;
      claimDesk=createClaimDesk(byId('knowledge-claim-desk'),api,tell);
      void claimDesk.show({actor:scope.actor,tenant:scope.tenant,client,brand,role:scope.role});
      return;
    }
    edit = view==='briefs' ? (edit || {}) : baseValues(view);
    content.innerHTML = `<div class="knowledge-tabs" role="group" aria-label="Nội dung hồ sơ">${Object.entries(tabs).map(([id,label])=>`<button type="button" data-view="${id}" aria-pressed="${view===id}">${label}</button>`).join('')}</div>
      <div class="knowledge-body">${view==='briefs'?briefScreen():`<form id="knowledge-edit"><h3>${view==='company'?'Thiết lập nhanh':'Thông tin theo thương hiệu'}</h3>
        <p>${view==='company'?`Các thương hiệu của ${html(objectName(scope.clients,client))} có thể dùng chung bốn trường này. Bạn có thể lưu từng phần.`:`Chọn dữ liệu riêng cho ${html(objectName(scope.brands,brand))} hoặc dùng giá trị hiện tại của doanh nghiệp.`}</p>
        <div class="knowledge-grid">${fields.map(k=>`<div>${fieldBlock(k)}</div>`).join('')}</div>
        ${data.can_edit?'<button type="submit" disabled>Lưu thay đổi</button>':'<p>Bạn có quyền xem hồ sơ này.</p>'}
        <span id="knowledge-dirty" role="status"></span></form>`}</div>`;
    if (view==='briefs' && Object.keys(edit?.picks || {}).length) chooseBriefData();
  }
  function edited() {
    if(view==='claims')return;
    if (!edit || !data || conflict || command) return;
    if(view==='briefs') {edit.title=content.querySelector('[name=title]')?.value;return;}
    fields.forEach(k=>{
      const input=byId('knowledge-'+k);
      if(view==='company') edit[k]=input.value;
      else {
        const mode=byId('knowledge-'+k+'-mode').value;
        input.hidden=mode!=='override';
        edit[k]={mode,value:mode==='override'?input.value:''};
      }
    });
    const changed=hasChanges();
    const submit=content.querySelector('[type=submit]');
    if(submit)submit.disabled=!changed;
    byId('knowledge-dirty').textContent=changed?'Có thay đổi chưa lưu':'';
  }
  function serverEquivalent(kind,k,value,after) {
    if(kind==='company') return value || 'Chưa có thông tin';
    if(kind==='briefs') return valueText(value?.value);
    const selected=value.mode;
    const val=selected==='override' ? value.value : selected==='inherit' ? after.company[k] : null;
    return `${modes[selected]} · ${valueText(val)}`;
  }
  function compare(local, before, after) {
    const kind=local.kind;
    const patch=local.body?.fields || {};
    const keys=kind==='briefs' ? fields.filter(k=>before.fields[k].value!==after.fields[k].value || before.fields[k].mode!==after.fields[k].mode) : Object.keys(patch);
    const rows=keys.map(k=>{
      const oldValue=kind==='company'?before.company[k]:before.fields[k];
      const newValue=kind==='company'?after.company[k]:after.fields[k];
      const mine=kind==='briefs'?oldValue:patch[k];
      return `<div class="knowledge-diff"><h5>${names[k]}</h5><p>Máy chủ · ${html(serverEquivalent(kind,k,newValue,after))}</p>
        <p>${kind==='briefs'?'Bản trước khi tạo':'Bản bạn đang sửa'} · ${html(serverEquivalent(kind,k,mine,before))}</p>
        ${kind==='briefs'?'':`<label><input type="checkbox" value="${k}">Áp dụng lại ${names[k].toLowerCase()}</label>`}</div>`;
    }).join('');
    conflict={kind,patch,title:local.body?.title,picks:local.body?.selections};
    command=null;
    data=after;
    content.innerHTML=`<section class="knowledge-body"><h3>Đối chiếu thay đổi</h3><p>Một bản mới đã được lưu trước thao tác của bạn.</p>${rows}
      <div class="knowledge-actions"><button type="button" data-action="keep">Dùng bản máy chủ</button><button type="button" class="secondary" data-action="apply">${kind==='briefs'?'Tạo nháp theo bản mới':'Áp dụng các trường đã chọn'}</button></div></section>`;
    tell('Hồ sơ đã thay đổi. Kiểm tra các giá trị trước khi tiếp tục.',true);
  }
  function begin(kind,patch,title,picks) {
    const key=reentry?.key || crypto.randomUUID();
    const body={key,expected_revision:reentry?.expected_revision ?? (kind==='company'?data.company_revision:data.brand_revision)};
    if(kind!=='company')body.expected_company_revision=reentry?.expected_company_revision ?? data.company_revision;
    if(kind==='briefs'){
      body.title=title;
      if (picks && Object.keys(picks).length) body.selections={...picks};
    }
    else body.fields=patch;
    const pointer={kind,key,expected_revision:body.expected_revision,expected_company_revision:body.expected_company_revision};
    reentry=null;
    command={...pointer,body};
    remember(scopeKey()+'.command',pointer);
    return send(command);
  }
  function pendingUI() {
    edit=null;
    content.innerHTML=`<div class="knowledge-body"><h3>Đang xác nhận lần lưu trước</h3><p>Hệ thống sẽ kiểm tra kết quả trên máy chủ trước khi tiếp tục.</p>
      <button type="button" data-action="recover">Kiểm tra kết quả</button></div>`;
    tell('Chưa nhận được xác nhận. Bạn có thể kiểm tra lại.',true);
  }
  async function saved(local,result,token) {
    // Keep the pointer until readback also succeeds, including after a reload.
    try {
      const latest=await read(brandPath());
      if(!current(token))return;
      if(local.kind==='briefs') { view='briefs'; brief=result;remember(scopeKey()+'.brief',result.id); }
      data=latest;
      remember(scopeKey()+'.command',null);
      command=edit=conflict=null;
      render();
      tell(local.kind==='briefs'?'Đã lưu brief nháp nội bộ.':'Đã lưu thay đổi.');
      (byId('knowledge-open-title') || content.querySelector(`[data-view="${view}"]`))?.focus();
    } catch(error){
      if(!current(token))return;
      if([401,403,404].includes(error.status))return lockout();
      pendingUI();
    }
  }
  async function send(local) {
    const token=generation;
    const before=data;
    command=local;
    content.querySelectorAll('button,input,select').forEach(el=>el.disabled=true);
    tell('Đang lưu…');
    try {
      const path=local.kind==='company'?profilePath():brandPath()+(local.kind==='briefs'?'/briefs':'/overrides');
      const result=await api(path,'POST',local.body);
      if(current(token)) await saved(local,result,token);
    } catch(error){
      if(!current(token))return;
      if([401,403,404].includes(error.status))return lockout();
      if(error.status===409){
        try {
          // The user can re-enter an uncertain command after re-login. If the original
          // already won, recover its receipt instead of creating a second intention.
          try {
            const result=await read(commandPath(local.kind)+'/commands/'+local.key);
            if(current(token))return saved(local,result,token);
            return;
          } catch(probe){if(probe.status!==404)throw probe;}
          const after=await read(brandPath());
          if(!current(token))return;
          remember(scopeKey()+'.command',null);
          return compare(local,before,after);
        } catch(fetchError){return failed(fetchError,token);}
      }
      if(error.status===422){
        remember(scopeKey()+'.command',null);
        command=null; render();
        if (local.kind==='briefs') content.querySelector('[name=title]').value=local.body.title;
        else {
          Object.entries(local.body.fields).forEach(([k,v])=>{
            if(local.kind==='brand')byId('knowledge-'+k+'-mode').value=v.mode;
            byId('knowledge-'+k).value=local.kind==='company'?v??'':v.value??'';
          });
          edited();
        }
        return tell('Có trường chưa hợp lệ. Kiểm tra nội dung rồi lưu lại.',true);
      }
      pendingUI();
    }
  }
  async function recover(token) {
    const local=command;
    if(!local)return;
    content.querySelectorAll('button').forEach(b=>b.disabled=true);
    try {
      const result=await read(commandPath(local.kind)+'/commands/'+encodeURIComponent(local.key));
      if(current(token))await saved(local,result,token);
    } catch(error){
      if(!current(token))return;
      if(error.status===404){
        if(local.body)return send(local);
        // Only identifiers survive reload. Re-entering the original intent reuses its
        // key and revisions so a late first commit cannot duplicate a brief.
        pendingUI();
        content.querySelector('button').insertAdjacentHTML('afterend',' <button class="secondary" type="button" data-action="reenter">Nhập lại thao tác</button>');
        tell('Máy chủ chưa xác nhận. Bạn có thể kiểm tra lại hoặc nhập lại thao tác với cùng mã lưu.');
      } else if([401,403].includes(error.status))lockout();
      else pendingUI();
    }
  }
  async function openBrief(id) {
    const token=++generation;
    tell('Đang mở brief…');
    try {
      const result=await read(brandPath()+'/briefs/'+encodeURIComponent(id));
      if(!current(token))return;
      remember(scopeKey()+'.brief',id);
      brief=result;view='briefs';edit=null;render();tell('');
      byId('knowledge-open-title')?.focus();
    } catch(error){failed(error,token);}
  }
  context.addEventListener('change',e=>{
    if(!mayLeave()){selectors();return;}
    const viaClient=e.target.id==='knowledge-client';
    const id=e.target.id;
    const loading=selectScope(viaClient?e.target.value:client,viaClient?'':e.target.value);
    document.dispatchEvent(new CustomEvent('amc-brand-selection',{detail:{tenant:scope.tenant,brand}}));
    byId(id)?.focus();
    void loading;
  });
  content.addEventListener('input',edited);
  content.addEventListener('change',e=>{
    const slot=e.target.dataset.briefSlot;
    if(view==='briefs' && edit && slot in briefSlots){
      edit.picks ||= {}; edit.pickNames ||= {};
      if(e.target.value){
        edit.picks[slot]=e.target.value;
        edit.pickNames[slot]=e.target.selectedOptions[0].textContent;
      } else {
        delete edit.picks[slot]; delete edit.pickNames[slot];
      }
    }
    edited();
  });
  content.addEventListener('submit',e=>{
    e.preventDefault();
    if(command || conflict || !data?.can_edit)return;
    if(view==='briefs'){
      const title=e.target.elements.title.value.trim();
      if(!title){tell('Hãy nhập tên brief.',true);e.target.elements.title.focus();return;}
      begin('briefs',null,title,edit?.picks);
    } else {
      const patch=changes();
      if(!Object.keys(patch).length)return;
      for(const [k,val] of Object.entries(patch)){
        if(view==='company')patch[k]=val.trim()||null;
        else if(val.mode==='override'){
          if(!val.value.trim()){tell('Hãy nhập giá trị riêng hoặc chọn chủ động để trống.',true);byId('knowledge-'+k).focus();return;}
          patch[k]={mode:val.mode,value:val.value.trim()};
        }else patch[k]={mode:val.mode};
      }
      begin(view,patch);
    }
  });
  content.addEventListener('click',e=>{
    const button=e.target.closest('button');
    if(!button)return;
    const {view:next,brief:id,action,create}=button.dataset;
    if(create){
      const f=byId(create+'-form');
      document.querySelector('[data-route="settings"]').click();
      if(create==='brand')f.elements.client_id.value=client;
      f.elements.name.focus();return;
    }
    if(next){
      if(reentry && next!==view)return tell('Hãy hoàn tất thao tác đang khôi phục trước khi chuyển mục.',true);
      if(!mayLeave())return;
      generation++;
      view=next;edit=null;
      if(next!=='briefs'){brief=null;remember(scopeKey()+'.brief',null);}
      render();tell('');content.querySelector(`[data-view="${view}"]`).focus();
    } else if(id)openBrief(id);
    else if(action==='brief-options')chooseBriefData();
    else if(action==='load')loadWorkspace();
    else if(action==='recover')recover(generation);
    else if(action==='reenter'){
      reentry=command;command=null;view=reentry.kind;edit=null;render();tell('Nhập lại nội dung của lần lưu trước.');
    }
    else if(action==='keep'){conflict=edit=null;render();tell('Đã mở bản mới trên máy chủ.');content.querySelector(`[data-view="${view}"]`)?.focus();}
    else if(action==='apply' && conflict){
      const {kind,patch,title,picks}=conflict;
      if(kind==='briefs'){conflict=null;begin(kind,null,title,picks);return;}
      const selected=Array.from(content.querySelectorAll('input:checked'),el=>el.value);
      if(!selected.length)return tell('Chọn ít nhất một trường để áp dụng lại.',true);
      conflict=null;begin(kind,Object.fromEntries(selected.map(k=>[k,patch[k]])));
    }
  });
  window.addEventListener('focus',revalidate);
  document.addEventListener('amc-open-brand',event=>{
    const next=scope?.brands.find(b=>b.id===event.detail && scope.clients.some(c=>c.id===b.client_id));
    if(next && next.id!==brand && mayLeave()) void selectScope(next.client_id,next.id);
  });
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)revalidate();});
  return {show,reset,permissionChanged};
}
