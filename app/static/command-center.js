// The list carries the server's decision and exact assessment binding. Sharing remains a server command.
function deliverableStage(doc) {
  if (doc.status !== 'approved') return ({submitted:'Chờ QA',draft:'Nháp',rejected:'Cần sửa'})[doc.status] || doc.status || 'Chưa xác định';
  const report=doc.qa_evidence;
  const current=Boolean(doc.reviewed_by) && Number.isInteger(doc.qa_revision) && doc.qa_revision>0 && doc.qa_approved_revision===doc.qa_revision &&
    report?.qa_revision===doc.qa_revision && /^[a-f0-9]{64}$/.test(doc.qa_approved_digest || '') &&
    doc.qa_approved_digest===report.content_digest && ['current','source_unavailable'].includes(report.state);
  return current ? 'Đã qua QA' : 'Chờ QA';
}

/* Tenant totals come from the current refresh. Task and department rows belong to one selected campaign. */
function createCommandCenter(api,screens) {
  const by = id => document.getElementById(id);
  const box = by('command-center'), campaignControl = by('command-campaign'), brandControl=by('toolbar-brand');
  const phases = {
    intake:'Tiếp nhận', research:'Nghiên cứu', strategy:'Chiến lược', content:'Nội dung',
    creative:'Sáng tạo', quality:'Kiểm duyệt', reporting:'Đo lường',
  };
  const states = {
    backlog:'Chờ làm', pending:'Chờ làm', queued:'Chờ làm', planned:'Đã lập kế hoạch', draft:'Nháp',
    in_progress:'Đang làm', active:'Đang làm', running:'Đang làm', blocked:'Đang vướng',
    failed:'Thất bại', cancelled:'Đã hủy', completed:'Hoàn tất', done:'Hoàn tất', succeeded:'Hoàn tất',
    submitted:'Chờ QA', approved:'Đã qua QA', rejected:'Cần sửa', changes_requested:'Cần sửa',
  };
  const completed = new Set(['completed','done','succeeded']);
  const text = (tag,value,className) => {
    const part = document.createElement(tag);
    part.textContent = value;
    if (className) part.className = className;
    return part;
  };
  const write = (id,value) => { by(id).textContent = value; };
  const status = value => states[value] || value || 'Chưa xác định';
  const phase = row => phases[row.workflow_key] || row.title || row.workflow_key;
  const row = (name,detail,tag) => {
    const li = document.createElement('li');
    const body = document.createElement('span');
    body.append(text('strong',name),text('small',detail));
    const chip=text('span',tag,'state-chip');
    if(['Chờ QA','Cần sửa','Đang vướng','Đã dừng','Thất bại'].includes(tag)) chip.dataset.tone='attention';
    li.append(body,chip);
    return li;
  };
  const note = (list,message) => list.replaceChildren(text('li',message,'empty'));
  function loadingRows(list,message) {
    note(list,message);
    const placeholders=document.createElement('span');
    placeholders.className='pending-rows';
    placeholders.setAttribute('aria-hidden','true');
    for(let n=0;n<3;n++) placeholders.append(document.createElement('i'));
    list.firstElementChild.append(placeholders);
  }
  let context = null, controller = null, roleAbort = null, roleMap = new Map(), currentTasks = [], generation = 0;
  let selectedCampaign = '', runs = null, activityFailed = false;
  function clear() {
    generation++;
    controller?.abort();
    roleAbort?.abort();
    context = null;
    currentTasks = [];
    selectedCampaign = '';
    roleMap = new Map();
    runs=null; activityFailed=false;
    box.hidden = true;
    box.removeAttribute('aria-busy');
    campaignControl.replaceChildren();
    for (const id of ['command-tasks','command-outcomes','command-departments','command-runs','command-capabilities','command-flow','command-scope','command-objective','command-client-total','campaign-caption','toolbar-brand'])
      by(id).replaceChildren();
    for (const id of ['command-campaign-count','command-deliverable-count','command-review-count','command-approved-count','command-progress-label'])
      write(id,'—');
    by('command-progress').removeAttribute('value');
    write('command-progress-caption','');
    write('command-status','');
  }
  function departments(tasks) {
    const groups = new Map();
    for (const task of tasks) {
      const designation = roleMap.get(task.role_slug);
      const group = designation?.group || 'Chưa xác định bộ phận';
      if (!groups.has(group)) groups.set(group,[]);
      const entry = groups.get(group);
      entry.push({task,role:designation?.display_name || task.role_slug || 'Chưa có vai trò'});
    }
    const list = by('command-departments');
    if (!groups.size) return note(list,'Chưa có nhiệm vụ để phân công bộ phận.');
    list.replaceChildren(...Array.from(groups, ([group,entries]) => {
      const li=document.createElement('li'), details=document.createElement('details'), summary=document.createElement('summary');
      const icon=document.createElementNS('http://www.w3.org/2000/svg','svg');
      const use=document.createElementNS(icon.namespaceURI,'use');
      icon.setAttribute('class','icon');icon.setAttribute('aria-hidden','true');
      const key=entries[0].task.workflow_key;
      const glyph=({intake:'team',research:'book',strategy:'grid',content:'campaign',creative:'campaign',quality:'review',reporting:'finance'})[key] || 'team';
      use.setAttribute('href','/static/interface-icons.svg#'+glyph);icon.append(use);
      summary.append(icon,text('strong',group),text('span',entries.length+' việc','state-chip'),text('small',entries[0].role));
      details.append(summary);
      for(const {task,role} of entries){
        const assignment=text('div','','assignment');
        assignment.append(text('strong',role),text('span',task.title),text('small',status(task.status)+' · Nhiệm vụ kế hoạch'));
        details.append(assignment);
      }
      li.append(details);return li;
    }));
  }
  function drawTasks(tasks) {
    const ordering = Object.keys(phases);
    const rank = r => ordering.includes(r.workflow_key) ? ordering.indexOf(r.workflow_key) : ordering.length;
    currentTasks = [...tasks].sort((a,b) => rank(a)-rank(b));
    const done = tasks.filter(r=>completed.has(r.status)).length;
    write('command-progress-label',tasks.length ? Math.round(done*100/tasks.length)+'%' : '—');
    const meter = by('command-progress');
    if (tasks.length) { meter.max = tasks.length; meter.value = done; } else meter.removeAttribute('value');
    write('command-progress-caption',tasks.length ? done+' / '+tasks.length+' nhiệm vụ hoàn tất' : 'Chưa có nhiệm vụ để tính tiến độ.');
    const flow = by('command-flow');
    flow.replaceChildren(...currentTasks.map((r,i) => {
      const step = document.createElement('li'), trigger=text('button',phase(r),'phase-button');
      trigger.type='button';
      step.dataset.state = completed.has(r.status) ? 'done' : ['running','active','in_progress'].includes(r.status) ? 'active' : 'pending';
      trigger.setAttribute('aria-label',phase(r)+' · '+status(r.status)+'. Xem nhiệm vụ');
      trigger.title = status(r.status);
      trigger.prepend(text('span',String(i+1).padStart(2,'0'),'step-number'));
      trigger.addEventListener('click',()=>{
        const detail=by('command-tasks').children[i]?.querySelector('details');
        if(!detail) return;
        detail.open=true;
        detail.querySelector('summary').focus();
      });
      step.append(trigger);
      return step;
    }));
    const list = by('command-tasks');
    if (tasks.length) list.replaceChildren(...currentTasks.map(r=>{
      const li=document.createElement('li'), details=document.createElement('details'), summary=text('summary',phase(r)+' · '+status(r.status));
      details.append(summary,text('p',r.title || 'Chưa có mô tả.'));
      if(r.expected_output) details.append(text('small','Đầu ra dự kiến · '+r.expected_output));
      li.append(details);
      return li;
    }));
    else note(list,'Bảng nhiệm vụ sẽ xuất hiện sau khi lập kế hoạch cho chiến dịch.');
    departments(currentTasks);
  }
  function drawOutcomes(id) {
    const items = context.deliverables.filter(d => d.campaign_id === id);
    const list = by('command-outcomes');
    if (items.length) list.replaceChildren(...items.map(d=>{
      const stage=deliverableStage(d), evidence=d.qa_evidence?.qa_revision===d.qa_revision ? d.qa_evidence : null;
      const source=evidence?.state==='current' ? 'Đã liên kết nguồn' : evidence?.state==='source_unavailable' ? 'Chưa có nguồn để đối chiếu' : 'Chưa có đánh giá nguồn hiện hành';
      const access=stage==='Đã qua QA' ? (['owner','admin'].includes(context.role) ? 'Có thể yêu cầu chia sẻ trong Phê duyệt' : 'Cần quản trị viên để chia sẻ') :
        d.status==='shared' ? 'Đã tạo phiên bản bàn giao' : 'Bản nội bộ';
      return row(d.title||'Bản giao',source+' · '+access,stage);
    }));
    else note(list,'Chiến dịch chưa có bản giao.');
  }
  function drawRuns() {
    const list=by('command-runs');
    if (!selectedCampaign) return note(list,'Chọn chiến dịch để xem hoạt động của đội ngũ AI.');
    if (!runs) return note(list,activityFailed ? 'Chưa tải được dữ liệu Workforce.' : 'Đang tải hoạt động Workforce.');
    const chosen=runs.filter(run=>run.campaign===selectedCampaign);
    if (!chosen.length) return note(list,'Chưa thấy lượt xử lý trong 100 lượt gần nhất của workspace.');
    const labels={queued:'Đang chờ worker',running:'Đang xử lý',awaiting_qa:'Đã chuyển QA',failed:'Đã dừng'};
    list.replaceChildren(...chosen.map(run=>row(run.title,run.done+' / '+run.steps+' checkpoint · '+run.workflow, labels[run.state] || status(run.state))));
  }
  function activity(tenant, briefs, reports) {
    if (!context || context.tenant!==tenant) return;
    activityFailed=!Array.isArray(briefs) || !Array.isArray(reports);
    if (activityFailed) runs=null;
    else {
      const scope=new Map(briefs.map(brief=>[brief.id,brief.campaign_id]));
      runs=reports.filter(run=>scope.has(run.brief_id)).map(run=>({
        campaign:scope.get(run.brief_id),title:run.title,state:run.state,done:run.done,steps:run.skills.length,workflow:run.workflow,
      }));
    }
    drawRuns();
  }
  async function capabilities(local,campaign,epoch,signal) {
    const list=by('command-capabilities');
    note(list,'Đang đọc quyền workflow…');
    try {
      const rows=await api('/api/tenants/'+encodeURIComponent(local.tenant)+'/workforce/registry/'+encodeURIComponent(campaign.id),'GET',null,false,signal);
      if(epoch!==generation || context!==local) return;
      if(!rows.length) return note(list,'Chưa có workflow được đăng ký cho môi trường này.');
      list.replaceChildren(...rows.map(entry=>{
        const required=entry.manifest.required || [], granted=required.filter(skill=>entry.grants[skill]==='activate');
        return row(entry.workflow,required.join(' · '),granted.length===required.length && required.length ? 'Đã cấp quyền' : 'Chưa đủ quyền');
      }));
    } catch(error) {
      if(epoch===generation && context===local && error.name!=='AbortError') note(list,'Chưa đọc được năng lực đã đăng ký.');
    }
  }
  async function choose() {
    const local = context;
    if (!local) return;
    const epoch = ++generation;
    controller?.abort();
    controller = new AbortController();
    const campaign = local.campaigns.find(c=>c.id===campaignControl.value);
    selectedCampaign = campaign?.id || '';
    write('campaign-caption',campaign?.name || 'Chưa chọn chiến dịch');
    currentTasks = [];
    by('command-flow').replaceChildren();
    by('command-progress').removeAttribute('value');
    write('command-progress-label','—');
    write('command-objective',campaign?.objective || (campaign?'Chưa ghi mục tiêu.':'Chọn chiến dịch sau khi tạo hồ sơ đầu tiên.'));
    by('command-plan-link').hidden = !campaign || local.role === 'viewer';
    const firstAction=by('command-new-link');
    firstAction.hidden = Boolean(campaign) || local.role === 'viewer';
    const next=!local.clients.length ? ['client-form','Thêm doanh nghiệp'] : !local.brands.length ?
      ['brand-form','Thiết lập thương hiệu'] : ['campaign-form','Tạo chiến dịch'];
    firstAction.href='#'+next[0]; firstAction.textContent=next[1];
    const brand = local.brands.find(b=>b.id===campaign?.brand_id);
    const client = local.clients.find(c=>c.id===brand?.client_id);
    write('command-scope',campaign ? [client?.name,brand?.name].filter(Boolean).join(' / ') : '');
    drawOutcomes(selectedCampaign);
    drawRuns();
    if (!campaign) {
      note(by('command-capabilities'),'Chọn chiến dịch để xem workflow.');
      drawTasks([]);
      box.removeAttribute('aria-busy');
      write('command-status','');
      return;
    }
    box.setAttribute('aria-busy','true');
    write('command-status','Đang tải nhiệm vụ…');
    write('command-progress-caption','Đang tải tiến độ.');
    loadingRows(by('command-tasks'),'Đang tải nhiệm vụ.');
    loadingRows(by('command-departments'),'Đang tải phân công.');
    void capabilities(local,campaign,epoch,controller.signal);
    try {
      const result = await api('/api/tenants/'+encodeURIComponent(local.tenant)+'/campaigns/'+encodeURIComponent(campaign.id)+'/tasks','GET',null,false,controller.signal);
      if (epoch !== generation || local !== context) return;
      drawTasks(result);
      write('command-status','');
    } catch (error) {
      if (epoch !== generation || local !== context || error.name==='AbortError') return;
      if ([401,403,404].includes(error.status)) {
        clear();
        local.onRestricted?.(error.status);
        return;
      }
      write('command-status','Chưa tải được nhiệm vụ. Bấm Cập nhật để thử lại.');
      write('command-progress-caption','Chưa nhận được dữ liệu tiến độ.');
      note(by('command-tasks'),'Chưa nhận được danh sách nhiệm vụ.');
      note(by('command-departments'),'Chưa nhận được dữ liệu phân công.');
    } finally {
      if (epoch === generation) box.removeAttribute('aria-busy');
    }
  }
  async function show(data) {
    const previous = context?.tenant===data.tenant ? selectedCampaign : '';
    clear();
    if (!['owner','admin','editor','viewer'].includes(data.role)) return;
    context = data;
    box.hidden = false;
    by('command-refresh').disabled=false;
    write('command-client-total',(data.mode==='agency' ? 'Agency · '+data.clients.length+' khách hàng' : 'Marketing nội bộ')+' · '+data.brands.length+' thương hiệu');
    write('command-campaign-count',data.campaigns.length);
    write('command-deliverable-count',data.deliverables.length);
    write('command-review-count',data.deliverables.filter(d=>deliverableStage(d)==='Chờ QA').length);
    write('command-approved-count',data.deliverables.filter(d=>deliverableStage(d)==='Đã qua QA').length);
    brandControl.replaceChildren(new Option('Tất cả thương hiệu',''),...data.brands.map(b=>new Option(b.name,b.id)));
    const params=screens.params();
    brandControl.value=data.brands.some(b=>b.id===params.get('brand')) ? params.get('brand') : '';
    const work = filterCampaigns(params.get('campaign') || previous);
    screens.bindContext(params=>{
      if(context!==data) return;
      const brand=data.brands.some(b=>b.id===params.get('brand')) ? params.get('brand') : '';
      if(brandControl.value===brand && campaignControl.value===params.get('campaign')) return;
      brandControl.value=brand;
      filterCampaigns(params.get('campaign'));
    });
    if (data.campaigns.length) {
      roleAbort=new AbortController();
      void api('/api/catalog/roles','GET',null,false,roleAbort.signal).then(rows => {
        if (context !== data) return;
        roleMap = new Map(rows.map(r=>[r.id,r]));
        if(currentTasks.length) departments(currentTasks);
      }).catch(()=>{}); // The registered role slug remains visible when directory labels are unavailable.
    }
    await work;
  }
  function filterCampaigns(wanted, replace=true) {
    if(!context) return;
    const rows=context.campaigns.filter(c=>!brandControl.value || c.brand_id===brandControl.value);
    campaignControl.replaceChildren(...(rows.length ? rows.map(c=>new Option(c.name,c.id)) : [new Option('Chưa có chiến dịch','')]));
    campaignControl.disabled=!rows.length;
    if(rows.some(c=>c.id===wanted)) campaignControl.value=wanted;
    screens.context(brandControl.value,campaignControl.value,replace);
    return choose();
  }
  brandControl.addEventListener('change',()=>filterCampaigns(campaignControl.value,false));
  campaignControl.addEventListener('change',()=>{
    screens.context(brandControl.value,campaignControl.value,false);choose();
  });
  return {show,clear,activity};
}
