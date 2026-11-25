/* Attach Marketing readiness to an immutable internal brief. Only explicit clicks enqueue work. */
function mountMarketingBrief(root, api, context) {
  const {tenant, client, brand, brief, role, signal} = context;
  const base = '/api/tenants/' + tenant;
  const path = base + '/clients/' + client + '/brands/' + brand + '/business-workspace/marketing';
  const alive = () => root.isConnected && !signal.aborted;
  const read = url => api(url, 'GET', null, false, signal);
  const send = (url, method, body) => api(url,method,body,false,signal);
  const create = (tag, text) => {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    return node;
  };
  const button = text => {
    const node = create('button', text);
    node.type = 'button';
    return node;
  };
  const details = create('details'), summary = create('summary','Chuẩn bị Marketing từ brief này');
  root.replaceChildren(details);
  details.append(summary);
  let loaded = false;
  details.addEventListener('toggle', async () => {
    if (!details.open || loaded || !alive()) return;
    loaded = true;
    const form = create('form'), status = create('p','Đang tải lựa chọn của thương hiệu…');
    status.setAttribute('role','status');
    details.append(form,status);
    const feedback = msg => { if(alive()) status.textContent = msg; };
    const controls = {}, items = {}, labels = {brief:'Brief chiến dịch đã gửi', market:'Thị trường', kpi:'KPI chiến dịch', claim:'Nhận định được phép dùng'};
    let terms = null, captured = null, ticket = 0, active = false;
    const check = button('Kiểm tra mức sẵn sàng'), activate = button('Bật quy trình cho chiến dịch'), queue = button('Xếp việc cho AI');
    queue.disabled = true;
    activate.hidden = true;
    function field(label, node) {
      const group=create('label',label);
      group.append(node); form.append(group);
      return node;
    }
    function select(name, label) {
      const node=field(label,create('select'));
      node.name=name; node.add(new Option('Chọn…','')); controls[name]=node;
      return node;
    }
    const workflow = select('workflow','Loại công việc');
    workflow.add(new Option('Chiến lược nghiên cứu · WF-03','WF-03/research-strategy-draft@2'));
    workflow.add(new Option('Trang đích và SEO · WF-13','WF-13/landing-seo-draft@5'));
    workflow.selectedIndex=1;
    const picks = create('fieldset');
    async function load(kind, offset=0) {
      const page = await read(path+'/choices?kind='+kind+'&offset='+offset);
      if(!alive()) return;
      items[kind].push(...page.items);
      for(const row of page.items) {
        if(kind==='claim') {
          const label=create('label'), box=create('input');
          box.type='checkbox'; box.name='claim'; box.value=row.id;
          label.append(box,document.createTextNode(' '+[row.label,...row.qualifiers,row.scope.product,row.scope.region,row.scope.channel].filter(Boolean).join(' · ')));
          picks.append(label);
        } else {
          controls[kind].add(new Option(row.label,row.id));
        }
      }
      if(page.next_offset!==null) {
        const next=button('Xem thêm · '+labels[kind]);form.append(next);
        next.onclick=()=>{next.remove();load(kind,page.next_offset).catch(e=>feedback(e.message));};
      }
    }
    for(const kind of ['brief','market','kpi']) { select(kind,labels[kind]); items[kind]=[]; }
    picks.append(create('legend',labels.claim)); form.append(picks); items.claim=[];
    for(const [k,label] of Object.entries({locale:'Ngôn ngữ và thị trường',region:'Khu vực áp dụng',channel:'Kênh',currency:'Tiền tệ (nếu báo giá)',quantity:'Số lượng báo giá'})) {
      controls[k]=field(label,create('input')); controls[k].name=k;
    }
    form.append(check,activate,queue); form.onsubmit=e=>e.preventDefault();
    function choice() {
      const val = k=>controls[k].value.trim();
      const briefTarget=items.brief.find(r=>r.id===val('brief'));
      const claims=[...picks.querySelectorAll('input:checked')].map(el=>el.value);
      if(!briefTarget || !claims.length || ['market','kpi','locale','region','channel'].some(k=>!val(k))) {
        throw Error('Chọn brief chiến dịch, thị trường, KPI, ít nhất một nhận định và phạm vi áp dụng.');
      }
      return {key:crypto.randomUUID(),workspace_brief_id:brief,target:{campaign_id:briefTarget.campaign_id,brief_id:briefTarget.id},
              workflow:val('workflow'), market:val('market'),kpi:val('kpi'),claims, locale:val('locale'),region:val('region'),channel:val('channel'),
              currency:val('currency') || null,quantity:val('quantity') || null};
    }
    form.addEventListener('input', e=>{
      ++ticket; terms=captured=null;queue.disabled=true;activate.hidden=true;
      if(e.target.name==='claim' && e.target.checked) {
        const f=items.claim.find(r=>r.id===e.target.value);
        for(const k of ['locale','region','channel']) if(!controls[k].value) controls[k].value=f.scope[k];
        for(const k of ['currency','quantity']) if(!controls[k].value && f[k]) controls[k].value=f[k];
      }
      feedback('Kiểm tra lại phạm vi của lựa chọn hiện tại.');
    });
    async function assess() {
      const token=++ticket, data=choice();
      const readiness=await send(path+'/readiness','POST',data);
      if(!alive() || token!==ticket) return;
      if(readiness.status!=='ready') return feedback(readiness.guidance.join(' '));
      const entries=await read(base+'/workforce/registry/'+data.target.campaign_id);
      if(!alive() || token!==ticket) return;
      const release=entries.find(r=>r.workflow===data.workflow);
      if(!release)return feedback('Chưa cài phiên bản quy trình này trên PostgreSQL. Liên hệ quản trị workspace.');
      active=release.manifest.required.every(s=>release.grants[s]==='activate');
      terms=data; queue.disabled=!active;
      activate.hidden=active || !['owner','admin'].includes(role);
      feedback(active?'Đã đủ căn cứ để xếp việc. QA sẽ kiểm tra lại trước khi chia sẻ.':'Dữ liệu đã sẵn sàng. Quản trị viên cần bật quy trình cho chiến dịch.');
    }
    check.onclick=()=>assess().catch(e=>feedback(e.message));
    activate.onclick=async()=>{
      const data=terms;
      if(!data)return;
      try {
        const skills=data.workflow.startsWith('WF-03')?['director','research','strategy']:['director','content','seo'];
        await send(base+'/workforce/registry/'+data.target.campaign_id,'PUT',{workflow:data.workflow,action:'activate',skills});
        if(alive() && data===terms)await assess();
      } catch(e){feedback(e.message);}
    };
    queue.onclick=async()=>{
      const data=terms, token=ticket;
      if(!active || !data)return;
      queue.disabled=true;
      try {
        const snap=captured || await send(path+'/manifests','POST',data);
        if(!alive() || token!==ticket)return;
        captured=snap;
        const run=await send(base+'/workforce/briefs/'+data.target.brief_id+'/run','POST',
          {workflow:'dynamic-v1',registry_workflow:data.workflow,budget_microusd:0,knowledge_manifest:{id:snap.id,digest:snap.digest}});
        if(alive() && token===ticket)feedback('Đã xếp việc '+run.id+'. Theo dõi trong mục AI Workforce, sau đó mở bản giao để QA.');
      } catch(e){if(alive() && token===ticket){feedback(e.message);queue.disabled=false;}}
    };
    try {
      await Promise.all(['brief','market','kpi','claim'].map(k=>load(k)));
      feedback(items.brief.length?'Chọn dữ liệu để kiểm tra căn cứ của brief.':'Chưa có brief chiến dịch đã gửi trong thương hiệu này.');
    } catch(e){if(alive()){feedback(e.message);const retry=button('Tải lại lựa chọn');retry.onclick=()=>mountMarketingBrief(root,api,context);details.append(retry);}}
  });
}
