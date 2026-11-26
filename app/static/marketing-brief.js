/* Fetch the private locator only after an authorized reviewer opens it. */
function attachMarketingProvenance(parent, path, read, active) {
  const details=document.createElement('details'), label=document.createElement('summary'), rows=document.createElement('ul');
  label.textContent='Đối chiếu mã nguồn với tài liệu gốc';
  details.append(label,rows); parent.append(details);
  let generation=0, openListener;
  details.ontoggle=async()=>{
    const token=++generation;
    openListener?.abort();
    rows.replaceChildren();
    if(!details.open || !active())return;
    openListener=new AbortController();
    document.addEventListener('visibilitychange',()=>{
      if(document.hidden){++generation;rows.replaceChildren();details.open=false;openListener.abort();}
    },{signal:openListener.signal});
    try{
      const data=await read(path);
      if(token!==generation || !details.open || !active() || !details.isConnected)return;
      for(const entry of data.entries){
        const item=document.createElement('li');
        item.textContent=entry.handle+' · '+entry.document+' · '+entry.locator+' · SHA-256 '+entry.source_digest;
        rows.append(item);
      }
    }catch{if(token===generation && active())rows.textContent='Không thể đọc nguồn trong phạm vi quyền hiện tại.';}
  };
}

/* A client or staff author explicitly approves this bounded summary for the Marketing team. */
function taskIntentForm(parent, seed, onSubmit, options={}) {
  const box=document.createElement('details'), heading=document.createElement('summary'), fields=document.createElement('div');
  heading.textContent=options.title || 'Giao nhiệm vụ cho AI Director'; box.dataset.taskEntry='';
  const tip=document.createElement('p');tip.textContent='Chỉ nhập nội dung được phép gửi cho đội Marketing. Ghi rõ đầu ra và cách biết công việc đã đạt.';
  box.append(heading,tip,fields);parent.append(box);
  const controls={};
  function field(key,label,tag='input') {
    const wrap=document.createElement('label'), input=document.createElement(tag);
    wrap.textContent=label;input.name=key;wrap.append(input);fields.append(wrap);controls[key]=input;
    if(tag!=='select'){input.maxLength=tag==='textarea'?1450:240;input.value=seed[key]||'';}
    return input;
  }
  if(options.campaigns) {
    const campaign=field('campaign','Chiến dịch của nhiệm vụ','select');
    campaign.add(new Option('Chọn chiến dịch…',''));
    for(const row of options.campaigns)campaign.add(new Option(row.name,row.id));
    if(options.campaigns.length===1)campaign.selectedIndex=1;
  }
  const type=field('deliverable_type','Đầu ra cần nhận','select');
  type.add(new Option('Trang đích và metadata SEO','landing_page'));type.add(new Option('Nghiên cứu và chiến lược','marketing_strategy'));
  const action=field('buyer_action','Hành động người mua cần thực hiện','select');
  action.add(new Option('Chọn hành động…',''));
  for(const [code,label] of Object.entries({rfq:'Yêu cầu báo giá',appointment:'Gửi đề nghị hẹn',sample_request:'Yêu cầu mẫu thử',
    colour_card_request:'Yêu cầu bảng màu',catalogue_download:'Tải danh mục',registration:'Đăng ký',purchase:'Mua hàng',
    request_assessment:'Yêu cầu khảo sát',submit_reference:'Gửi mẫu tham chiếu',select_sample:'Gửi lựa chọn mẫu',choose_session:'Chọn buổi'})){
    action.add(new Option(label,code));
  }
  const material=field('buyer_input','Người mua cần gửi gì (nếu có)?','select');
  material.add(new Option('Không yêu cầu',''));
  for(const [code,label] of Object.entries({photo:'Ảnh',sample:'Mẫu tham chiếu',sample_choice:'Lựa chọn mẫu',session_choice:'Lựa chọn buổi'})){
    material.add(new Option(label,code));
  }
  const style=field('editorial_style','Cách diễn đạt','select');
  for(const [code,label] of Object.entries({plain:'Dễ hiểu',concise:'Ngắn gọn',formal:'Trang trọng',friendly:'Thân thiện'})){
    style.add(new Option(label,code));
  }
  field('purpose','Mục đích của công việc lần này');
  field('product','Sản phẩm của nhiệm vụ');field('audience','Nhóm khách hàng của nhiệm vụ');
  field('channel','Kênh của nhiệm vụ');field('region','Địa bàn của nhiệm vụ');field('locale','Ngôn ngữ của nhiệm vụ');
  field('requirements','Yêu cầu thực hiện, mỗi dòng một ý','textarea');
  field('exclusions','Cụm từ cấm xuất hiện, mỗi dòng một cụm (tuỳ chọn)','textarea');
  field('acceptance_criteria','Tiêu chí chấp nhận, mỗi dòng một ý','textarea');
  const save=document.createElement('button'), note=document.createElement('p');
  save.type='button';save.textContent=options.button || 'Xác nhận yêu cầu công việc';note.setAttribute('role','status');
  box.append(save,note);
  let key=crypto.randomUUID();
  fields.addEventListener('input',()=>{key=crypto.randomUUID();save.disabled=false;});
  save.onclick=async()=>{
    const intent={};
    for(const [k,control] of Object.entries(controls)){
      const v=control.value.trim();
      if(k==='buyer_input' && !v)continue;
      if(!v && k!=='exclusions'){note.textContent='Bổ sung trường '+control.parentElement.firstChild.textContent+'.';control.focus();return;}
      if(k==='campaign')continue;
      if(['requirements','exclusions','acceptance_criteria'].includes(k)){
        const lines=v.split('\n').map(s=>s.trim()).filter(Boolean);
        if(lines.length>6 || lines.some(s=>s.length>240)){
          note.textContent='Mỗi mục có tối đa sáu dòng, mỗi dòng tối đa 240 ký tự.';control.focus();return;
        }
        intent[k]=lines;
      }else intent[k]=v;
    }
    save.disabled=true;
    try{await onSubmit(intent,controls.campaign?.value,key);note.textContent='Đã ghi nhận yêu cầu. Hãy kiểm tra mức sẵn sàng trước khi giao việc.';}
    catch(e){note.textContent=e.message;save.disabled=false;}
  };
  return box;
}

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
    const guidance = reason => ({
      'Update company and brand profiles, then save a new internal brief against both current revisions':'Lưu hồ sơ chung và bản thương hiệu hiện tại, sau đó tạo brief nháp mới.',
      'Complete name, offer, audience and goal in the company or brand profile, then save the brief':'Bổ sung tên doanh nghiệp, sản phẩm, khách hàng và mục tiêu rồi lưu brief.',
      'Select a product or variant, audience and campaign objective in the internal brief':'Ghim sản phẩm hoặc biến thể, hồ sơ khách hàng và mục tiêu của đúng chiến dịch vào brief mới.',
      'Select an approved objective and KPI for this exact campaign':'Chọn KPI đã duyệt gắn với đúng mục tiêu của chiến dịch.',
      'Attach the brand objective to a current shared company objective':'Nối mục tiêu thương hiệu với mục tiêu công ty đang được duyệt.',
      'Revision lacks current approved authority':'Đối chiếu lại trạng thái duyệt, hiệu lực và nguồn đã ghim trong danh mục.',
      'Claim differs from the exact product, variant, market, locale, region or channel':'Kiểm tra lại sản phẩm, SKU, thị trường, ngôn ngữ, khu vực và kênh của từng nhận định.',
      'Select the exact approved currency and quote quantity':'Nhập tiền tệ và số lượng khớp với điều kiện báo giá đã duyệt.',
      'Select fewer approved claims so every qualifier fits in one deliverable':'Giảm số nhận định để bản giao chứa đủ mọi điều kiện đã duyệt.',
      'Locale and audience must match the selected market':'Kiểm tra thị trường của hồ sơ khách hàng và ngôn ngữ áp dụng.',
      'Brief recipient no longer has this scope':'Kiểm tra lại quyền của người nhận brief chiến dịch.'
    })[reason] || reason;
    const controls = {}, items = {}, labels = {brief:'Brief chiến dịch đã gửi', market:'Thị trường', kpi:'KPI chiến dịch', claim:'Nhận định được phép dùng',
      guidelines:'Hướng dẫn thương hiệu đã duyệt'};
    let terms = null, captured = null, ticket = 0, active = false;
    const check = button('Kiểm tra mức sẵn sàng'), activate = button('Bật quy trình cho chiến dịch'), queue = button('Xếp việc cho AI');
    const corrections=create('section');corrections.setAttribute('aria-label','Làm rõ dữ liệu thương mại');
    details.append(corrections);
    check.disabled = true;
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
    const currentResearch='WF-03/research-strategy-draft@3',currentLanding='WF-13/landing-seo-draft@6';
    workflow.add(new Option('Chiến lược theo yêu cầu · WF-03 v3',currentResearch));
    workflow.add(new Option('Trang đích theo yêu cầu · WF-13 v6',currentLanding));
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
    for(const kind of ['brief','guidelines','market','kpi']) { select(kind,labels[kind]); items[kind]=[]; }
    function recommend(row){
      if(row?.deliverable_type)workflow.value=row.deliverable_type==='landing_page'?currentLanding:currentResearch;
    }
    controls.brief.addEventListener('change',()=>recommend(items.brief.find(row=>row.id===controls.brief.value)));
    if(context.mode==='inhouse'){
      const entry=taskIntentForm(details,{product:context.selections.product?.label,audience:context.selections.audience?.label},
        async(intent,campaign,key)=>{
          const row=await send(base+'/workforce/internal-tasks','POST',{key,campaign_id:campaign,intent});
          if(!alive())return;
          if(!items.brief.some(r=>r.id===row.id)){items.brief.push({...row,label:row.title,deliverable_type:intent.deliverable_type});
            controls.brief.add(new Option(row.title,row.id));}
          controls.brief.value=row.id;recommend({deliverable_type:intent.deliverable_type});
          form.dispatchEvent(new Event('input'));feedback('Đã chọn nhiệm vụ nội bộ. Ghim hướng dẫn thương hiệu và căn cứ để kiểm tra.');
        },{campaigns:context.campaigns});
      details.insertBefore(entry,form);
    }
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
      const current=[currentLanding,currentResearch].includes(val('workflow'));
      return {key:crypto.randomUUID(),workspace_brief_id:brief,target:{campaign_id:briefTarget.campaign_id,brief_id:briefTarget.id},
              workflow:val('workflow'), market:val('market'),kpi:val('kpi'),claims, locale:val('locale'),region:val('region'),channel:val('channel'),
              ...(current && val('guidelines') ? {guidelines:val('guidelines')} : {}),
              currency:val('currency') || null,quantity:val('quantity') || null};
    }
    form.addEventListener('input', e=>{
      corrections.replaceChildren();
      ++ticket; terms=captured=null;queue.disabled=true;activate.hidden=true;
      if(e.target.name==='claim' && e.target.checked) {
        const f=items.claim.find(r=>r.id===e.target.value);
        for(const k of ['locale','region','channel']) if(!controls[k].value) controls[k].value=f.scope[k];
        for(const k of ['currency','quantity']) if(!controls[k].value && f[k]) controls[k].value=f[k];
      }
      feedback('Kiểm tra lại phạm vi của lựa chọn hiện tại.');
    });
    async function assess() {
      corrections.replaceChildren();
      terms=captured=null; active=false; queue.disabled=true; activate.hidden=true;
      const token=++ticket, data=choice();
      const readiness=await send(path+'/readiness','POST',data);
      if(!alive() || token!==ticket) return;
      if(readiness.status!=='ready'){
        if(readiness.clarifications?.length){
          feedback('Cần xác nhận đơn vị tính tiền trước khi giao việc.');
          for(const issue of readiness.clarifications)showCorrection(issue,data,token);
        }else feedback(readiness.guidance.map(guidance).join(' '));
        return;
      }
      const entries=await read(base+'/workforce/registry/'+data.target.campaign_id);
      if(!alive() || token!==ticket) return;
      const release=entries.find(r=>r.workflow===data.workflow);
      if(!release)return feedback('Chưa cài phiên bản quy trình này trên PostgreSQL. Liên hệ quản trị workspace.');
      active=release.manifest.required.every(s=>release.grants[s]==='activate');
      terms=data; queue.disabled=!active;
      activate.hidden=active || !['owner','admin'].includes(role);
      const internal=items.brief.find(row=>row.id===data.target.brief_id)?.origin==='internal';
      const ready=internal?'Đã đủ căn cứ để tạo bản nháp nội bộ.':'Đã đủ căn cứ để xếp việc. QA sẽ kiểm tra lại trước khi chia sẻ.';
      feedback(active?ready:'Dữ liệu đã sẵn sàng. Quản trị viên cần bật quy trình cho chiến dịch.');
    }
    check.onclick=()=>assess().catch(e=>feedback(e.message));
    if(['owner','admin'].includes(role)){
      const saved=create('div');
      const resume=button('Tiếp tục sau khi sửa đơn vị bán');
      form.append(resume,saved);
      resume.onclick=()=>loadSaved(0).catch(e=>feedback(e.message));
      async function loadSaved(offset){
        const page=await read(path+'/clarifications?workspace_brief_id='+encodeURIComponent(brief)+'&offset='+offset);
        if(!alive())return;
        if(!offset)saved.replaceChildren();
        for(const row of page.items){
          const s=row.selection,target=s.target;
          const label=items.brief.find(i=>i.id===target.brief_id)?.label || 'Nhiệm vụ đã lưu';
          const use=button(label+(row.status==='approved'?' · dùng giá đã duyệt':' · xem đề xuất'));
          use.onclick=async()=>{
            for(const k of ['brief','workflow','market','kpi','guidelines','locale','region','channel','currency','quantity']){
              const v=k==='brief'?target.brief_id:s[k];
              if(v && controls[k].tagName==='SELECT' && !Array.from(controls[k].options).some(o=>o.value===v)){
                controls[k].add(new Option('Lựa chọn đã ghim trong brief',v));
              }
              controls[k].value=v??'';
            }
            if(!items.brief.some(b=>b.id===target.brief_id))items.brief.push({id:target.brief_id,label,campaign_id:target.campaign_id});
            const ids=s.claims.map(id=>id===row.original_claim && row.status==='approved'?row.claim:id);
            for(const box of picks.querySelectorAll('input'))box.checked=ids.includes(box.value);
            for(const id of ids){
              if(Array.from(picks.querySelectorAll('input')).some(box=>box.value===id))continue;
              const el=create('input'),wrap=create('label');
              el.type='checkbox';el.name='claim';el.checked=true;el.value=id;
              wrap.append(el,document.createTextNode(' Nhận định đã ghim khi làm rõ'));picks.append(wrap);
              items.claim.push({id,scope:{},label:'Nhận định đã ghim khi làm rõ'});
            }
            await assess().catch(e=>feedback(e.message));
          };
          saved.append(use);
        }
        if(page.next_offset!==null){
          const next=button('Xem thêm lựa chọn đã lưu');saved.append(next);
          next.onclick=()=>{next.remove();loadSaved(page.next_offset).catch(e=>feedback(e.message));};
        }else if(!saved.childElementCount)saved.append(create('p','Brief này chưa có đề xuất đơn vị đã lưu.'));
      }
    }
    function showCorrection(issue,selection,token){
      const panel=create('fieldset'), terms=issue.terms;
      panel.append(create('legend','Đơn vị bán · bản chào giá '+issue.offer_revision));
      const scale=['VND','JPY'].includes(terms.currency)?1:100;
      const money=new Intl.NumberFormat(selection.locale, {style:'currency',currency:terms.currency}).format(terms.amount_minor/scale);
      panel.append(create('p',money+' cho '+terms.basis_quantity+' đơn vị “dịch vụ”. Tối thiểu '+terms.moq+
        ', bậc giá từ '+terms.tier_min+(terms.tier_max?' đến '+terms.tier_max:'')+'. Số lượng đang báo '+issue.quantity+'.'),
        create('p',({included:'Đã gồm thuế',excluded:'Chưa gồm thuế',unknown:'Chưa rõ thuế'}[terms.tax])+
          '. '+[...new Set([...terms.conditions,...issue.qualifiers])].join(' ')));
      corrections.append(panel);
      if(!issue.can_amend){panel.append(create('p','Chuyển thẻ giá cho người quản trị có quyền cập nhật dữ liệu.'));return;}
      const input=(caption,tag='input')=>{
        const label=create('label',caption), el=create(tag);label.append(el);panel.append(label);return el;
      };
      const proposal=issue.proposal;
      const submit=(caption,handler)=>{
        const btn=button(caption);panel.append(btn);
        btn.onclick=async()=>{btn.disabled=true;try{await handler();}catch(e){feedback(e.message);}finally{btn.disabled=false;}};
      };
      async function reuse(id){
        if(!alive() || token!==ticket)return;
        const row=items.claim.find(c=>c.id===issue.claim);
        const old=Array.from(picks.querySelectorAll('input')).find(el=>el.value===issue.claim);
        if(!row||!old)throw Error('Chọn lại nhận định đã sửa.');
        const choice={...row,id,label:'Giá đã xác nhận theo '+issue.choices[proposal.unit]};
        items.claim.push(choice);
        const label=create('label'), el=create('input');
        el.type='checkbox';el.name='claim';el.value=id;el.checked=true;old.checked=false;
        label.append(el,document.createTextNode(' '+choice.label));picks.append(label);
        await assess();
      }
      if(proposal){
        panel.append(create('p','Đơn vị đề xuất: '+issue.choices[proposal.unit]+'.'));
        if(proposal.state==='approved'){submit('Dùng bản đã duyệt cho nhiệm vụ này',()=>reuse(proposal.claim));return;}
        if(proposal.state!=='draft'){panel.append(create('p','Xem lịch sử duyệt tại hồ sơ thương mại.'));return;}
        const evidence=button('Xem nguồn xác nhận');panel.append(evidence);
        evidence.onclick=async()=>{try{
          const url=base+'/clients/'+client+'/brands/'+brand+'/knowledge/revisions/'+proposal.evidence;
          const row=await read(url);
          if(!alive()||token!==ticket)return;
          const data=row.data;panel.append(create('p',data.document+' · '+data.entries[0].locator+' · '+data.entries[0].excerpt));
          evidence.disabled=true;
        }catch(e){feedback(e.message);}};
        if(proposal.required_qualification && (proposal.own || !proposal.qualifications.length)){
          panel.append(create('p','Người duyệt độc lập mở bàn nhận định của thương hiệu, chọn Duyệt đơn vị bán để đối chiếu.'));return;
        }
        const reason=input('Lý do duyệt bản chào giá và nguồn xác nhận');
        const auth=proposal.required_qualification?input('Ủy quyền nghiệp vụ','select'):null;
        if(auth)for(const id of proposal.qualifications)auth.add(new Option(id.slice(0,8),id));
        const key=crypto.randomUUID();
        submit('Duyệt dữ liệu và tiếp tục brief',async()=>{
          if(!reason.value.trim())throw Error('Ghi lý do sau khi đối chiếu nguồn.');
          const result=await send(path+'/clarifications/approve','POST',{key,proposal:proposal.id,
            reason:reason.value.trim(),qualification_revision:auth?.value || null});
          await reuse(result.claim);
        });
      }else{
        const unit=input('Đơn vị ghi trong chứng từ','select');unit.add(new Option('Chọn…',''));
        for(const [value,label] of Object.entries(issue.choices))unit.add(new Option(label,value));
        const doc=input('Tên chứng từ xác nhận'),locator=input('Vị trí trong chứng từ'),excerpt=input('Trích đoạn xác nhận đơn vị','textarea');
        const confirm=input('Tôi đã kiểm tra giá, lượng, bậc và điều kiện hiển thị đều áp dụng nguyên vẹn theo đơn vị này');confirm.type='checkbox';
        let key=crypto.randomUUID();panel.addEventListener('input',()=>{key=crypto.randomUUID();});
        submit('Lưu đề xuất điều chỉnh',async()=>{
          if(!unit.value||!doc.value.trim()||!locator.value.trim()||!excerpt.value.trim()||!confirm.checked)
            throw Error('Chọn đơn vị, cung cấp căn cứ và xác nhận giá. Nếu giá cần quy đổi, cập nhật báo giá riêng.');
          await send(path+'/clarifications/propose','POST',{selection,correction:{key,claim:issue.claim,claim_digest:issue.claim_digest,
            offer_digest:issue.offer_digest,unit:unit.value,document:doc.value.trim(),locator:locator.value.trim(),excerpt:excerpt.value.trim(),
            confirm_same_terms:true}});
          if(alive()&&token===ticket)await assess();
        });
      }
    }
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
        if(alive() && token===ticket){
          const internal=items.brief.find(row=>row.id===data.target.brief_id)?.origin==='internal';
          feedback('Đã xếp việc '+run.id+(internal?'. Theo dõi ở Đội ngũ AI, sau đó mở bản nháp nội bộ để đọc và biên tập.':'. Theo dõi ở Đội ngũ AI, sau đó mở bản giao để QA.'));
          if(['owner','admin'].includes(role))attachMarketingProvenance(details,path+'/manifests/'+snap.id+'/provenance',read,alive);
          // The worker panel may have loaded before the new run existed.
          try { await context.refreshWorkforce?.(tenant); }
          catch { if(alive() && token===ticket)feedback('Đã xếp việc '+run.id+'. Mở Đội ngũ AI và chọn Cập nhật tiến độ để tải lại.'); }
        }
      } catch(e){if(alive() && token===ticket){feedback(e.message);queue.disabled=false;}}
    };
    try {
      await Promise.all(['brief','guidelines','market','kpi','claim'].map(k=>load(k)));
      if(!alive())return;
      check.disabled = false;
      feedback(items.brief.length?'Chọn dữ liệu để kiểm tra căn cứ của brief.':
        context.mode==='inhouse'?'Tạo nhiệm vụ nội bộ cho chiến dịch của thương hiệu này.':'Chưa có brief chiến dịch đã gửi trong thương hiệu này.');
    } catch(e){if(alive()){feedback(e.message);const retry=button('Tải lại lựa chọn');retry.onclick=()=>mountMarketingBrief(root,api,context);details.append(retry);}}
  });
}
