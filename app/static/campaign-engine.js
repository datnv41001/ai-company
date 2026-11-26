/* Workspace data lives in memory; a scope change invalidates every in-flight response. */
function createCampaignEngine(api) {
  const by = id => document.getElementById(id);
  const panel = by('campaign-engine'), selector = by('engine-select'), board = by('engine-dashboard');
  const status = by('engine-status'), caption = by('engine-caption'), number = new Intl.NumberFormat('vi-VN');
  const kinds = {strategy:'Chiến lược',measurement:'Đo lường',landing:'Trang đích',seo:'SEO',social:'Nội dung mạng xã hội',
    ad:'Quảng cáo',creative_brief:'Brief thiết kế',calendar:'Lịch nội dung'};
  const states = {proposed:'Chờ duyệt',approved:'Đã duyệt',superseded:'Đã thay thế',draft:'Nháp',submitted:'Chờ QA',
    queued:'Đã xếp hàng',running:'Đang chạy',awaiting_qa:'Chờ QA',failed:'Thất bại',requested:'Đã giao việc',generated:'Đã tạo',
    scheduled:'Đã lên lịch',authorized:'Được phép chạy',executed:'Đã thực thi mô phỏng',cancelled:'Đã hủy',
    qualified:'Đủ điều kiện',received:'Đã nhận',assigned:'Đã phân công',accepted:'Sales đã nhận',rejected:'Từ chối',
    quoted:'Đã báo giá',ordered:'Đã đặt hàng',confirmed:'Đã xác nhận',refunded:'Đã hoàn tiền',
    shared:'Đã giao khách',qa_passed:'Đã qua QA',business_accepted:'Đã được tiếp nhận',fixture_accepted:'Nghiệm thu mô phỏng',incomplete:'Chưa hoàn tất'};
  const origins = {staff_saved_studio_revision:'Bản đã lưu trong Studio',staff_saved_revision:'Bản do tài khoản biên tập lưu',
    workforce_draft:'Bản nháp từ Workforce','deterministic-composition/1':'Soạn theo quy tắc'};
  const departments = {Strategy:'Chiến lược',Analytics:'Phân tích',Content:'Nội dung',Social:'Mạng xã hội',
    Media:'Quảng cáo',Design:'Thiết kế','Campaign Manager':'Điều phối chiến dịch'};
  const department = role => departments[role] || role;
  const channelName = value => ({web:'Trang web',search:'Tìm kiếm',social:'Mạng xã hội',email:'Email'})[value.toLowerCase()] || value;
  const label = v => states[v] || v || 'Chưa ghi nhận';
  let tenant = '', role = '', actor = '', generation = 0, abort, selected = '', campaigns = [];
  function add(parent, tag, title, cls) {
    const e = document.createElement(tag);
    if (title != null) e.textContent = title;
    if (cls) e.className = cls;
    parent.append(e); return e;
  }
  function reset() {
    generation++; abort?.abort(); abort = null;
    board.replaceChildren(); status.textContent = ''; panel.removeAttribute('aria-busy');
    caption.textContent = 'Chọn chiến dịch để xem mục tiêu, kế hoạch và kết quả sandbox.';
  }
  function scope(nextTenant, nextRole, rows, userId) {
    if (nextTenant !== tenant || role !== nextRole || actor!==userId || !rows.some(c => c.id === selected)) { reset(); selected = ''; }
    tenant = nextTenant; role = nextRole; actor=userId; campaigns = rows;
    panel.hidden = !['owner','admin'].includes(role) || !rows.length;
    selector.replaceChildren(new Option('Chọn chiến dịch',''), ...rows.map(c => new Option(c.name,c.id)));
    selector.value = selected;
  }
  selector.addEventListener('change', () => { selected=selector.value; load(); });
  const route = () => '/api/tenants/' + encodeURIComponent(tenant) + '/campaigns/' + encodeURIComponent(selected);
  const money = value => Number.isFinite(value) ? number.format(value)+' ₫' : 'Chưa đo';
  function card(grid,title) { const section=add(grid,'section',null,'engine-card'); add(section,'h4',title); return section; }
  function details(parent,title) { const box=add(parent,'details'); add(box,'summary',title); return box; }
  function line(parent,title,detail,chip) {
    const row=add(parent,'div',null,'engine-row'), body=add(row,'div');
    add(body,'strong',title); if(detail)add(body,'small',detail); if(chip)add(row,'span',chip,'state-chip');return body;
  }
  function field(form,title,type,defaultValue='',required=true) {
    const node=add(add(form,'label',title),'input');node.type=type;node.value=defaultValue;node.required=required;
    return node;
  }
  function pick(form,title,items) {
    const node=add(add(form,'label',title),'select');items.forEach(([id,name])=>node.add(new Option(name,id)));
    return node;
  }
  // Keep a logical request's id across a lost response. A changed payload is a new intent.
  function command(parent,title,build,{form=false}={}) {
    const source=route(), epoch=generation; let key, signature;
    const button=add(parent,'button',title);button.type=form?'submit':'button';
    const run=async e=>{
      e.preventDefault(); if(epoch!==generation || button.disabled)return;
      try {
        const {path, payload, idField} = build();
        const next=JSON.stringify([path,payload]);if(next!==signature){key=crypto.randomUUID();signature=next;}
        if(idField)payload[idField]=key;
        button.disabled=true; status.textContent='Đang ghi nhận…';
        await api(source+path,'POST',payload);
        if(epoch===generation)await load();
      }catch(err){if(epoch===generation)status.textContent=err.message;}
      finally{button.disabled=false;}
    };
    if(form)parent.addEventListener('submit',run);else button.addEventListener('click',run);
    return button;
  }
  function planEditor(section, planner) {
    if(!planner.choices.length){add(section,'p','Chưa có hồ sơ C3 có hành động người mua để lập kế hoạch.');return;}
    const old=planner.proposed || planner.active, form=add(details(section,old?'Đề xuất phiên bản kế tiếp':'Lập kế hoạch từ hồ sơ đã duyệt'),'form');
    const selections = planner.choices.map(item=>{
      const node=add(form,'label'), check=add(node,'input');check.type='checkbox';check.value=item.id;
      check.checked=Object.values(old?.manifests || {}).some(ref=>ref.id===item.id);
      node.append(document.createTextNode(item.workflow.split('/')[0]+' · '+item.product+' · '+item.audience+' · '+item.digest.slice(0,8)));
      if(item.channel)add(node,'small',channelName(item.channel)+' · '+item.objective+' · '+item.kpi);
      if(item.limits)add(node,'small','Tối đa '+item.limits.max_duration_days+' ngày · '+money(item.limits.max_media_budget_vnd)+' truyền thông');
      return check;
    });
    const target=field(form,'Kết quả mong muốn','text',old?.target_outcome||'',false);
    const outcomes=add(form,'datalist');
    outcomes.id='engine-approved-outcomes';
    target.setAttribute('list',outcomes.id);
    for(const value of new Set(planner.choices.flatMap(c=>[c.objective,c.kpi]).filter(Boolean))){
      add(outcomes,'option').value=value;
    }
    const days=field(form,'Thời hạn (ngày)','number',old?.duration_days||14);days.min=1;days.max=180;
    const budget=field(form,'Trần chi phí mô phỏng (VND)','number',old?.budget_vnd??0);budget.min=0;
    const ai=field(form,'Hạn mức sản xuất AI mỗi lượt (µUSD)','number',old?.ai_budget_microusd_per_run??10000);
    ai.min=0;ai.max=1000000;
    const channels=field(form,'Kênh đề xuất (cách nhau bằng dấu phẩy)','text',(old?.channels||[]).join(', '),false);
    const secondary=pick(form,'Tiếp nhận báo giá trong chiến dịch lịch hẹn',[['no','Chỉ nhận lịch hẹn'],['yes','Nhận thêm yêu cầu báo giá']]);
    secondary.value=old?.secondary_conversions?.includes('rfq')?'yes':'no';
    function syncIntake(){
      const choices=planner.choices.filter((_,i)=>selections[i].checked);
      secondary.disabled=!choices.length || !choices.every(c=>c.buyer_action==='appointment');
      secondary.closest('label').hidden=secondary.disabled;
    }
    for(const check of selections)check.addEventListener('change',syncIntake);
    syncIntake();
    command(form,'Lưu đề xuất',()=>{
      const ids=selections.filter(input=>input.checked).map(input=>input.value);
      if(!ids.length || ids.length>2)throw Error('Chọn một hoặc hai hồ sơ, mỗi workflow một hồ sơ.');
      return {path:'/engine/plans',idField:'key',payload:{manifest_ids:ids,expected_revision:planner.revisions[0]?.revision||0,
        duration_days:days.valueAsNumber,ai_budget_microusd_per_run:ai.valueAsNumber,budget_vnd:budget.valueAsNumber,...(target.value?{target_outcome:target.value}:{}),
        ...(!secondary.disabled && secondary.value==='yes'?{secondary_rfq:true}:{}),
        ...(channels.value?{channels:channels.value.split(',').map(x=>x.trim()).filter(Boolean)}:{})}};
    },{form:true});
  }
  function draw(planner, production, ops) {
    const active=planner.active, proposal=planner.proposed, plan=active||proposal;
    const title=campaigns.find(item=>item.id===selected)?.name;
    caption.textContent=title+(plan?' · '+plan.product+' · '+plan.audience:'');
    const nav=add(board,'nav',null,'engine-nav');
    nav.setAttribute('aria-label','Các phần của chiến dịch');
    const kpis=add(board,'div',null,'engine-kpis');
    const report=ops.report;
    const isService = plan?.buyer_action === 'appointment';
    const intakeMetric=isService?['Yêu cầu đặt lịch của kế hoạch',ops.appointments.filter(a=>a.plan_id===plan.id).length]:
      ['Yêu cầu báo giá sandbox',report.rfqs];
    for(const [caption,value] of [['Kế hoạch được duyệt',active?'v'+active.revision:'Chưa có'],
      ['Lượt Workforce',production.runs.length], intakeMetric,
      ['Chi phí mô phỏng',money(report.simulated_spend_vnd)]]) {
      const metric=add(kpis,'div',null,'metric');add(metric,'span',caption);add(metric,'strong',value);
    }
    const grid=add(board,'div',null,'engine-grid'), goals=card(grid,'Mục tiêu và phiên bản');
    if(plan){line(goals,plan.objective,plan.target_outcome!==plan.objective?plan.target_outcome:'',label(plan.status));
      add(goals,'p',plan.measurement_plan.kpi);
      const facts=add(goals,'dl',null,'engine-facts');
      for(const [term,value] of [['Kênh sản xuất',plan.channels.map(channelName).join(', ')],['Thời hạn',plan.duration_days+' ngày'],
        ['Ngân sách truyền thông mô phỏng',money(plan.budget_vnd)],['Hạn mức AI mỗi lượt',number.format(plan.ai_budget_microusd_per_run??10000)+' µUSD']]){
        add(facts,'dt',term);add(facts,'dd',value);
      }
      if(plan.research_gaps?.length)add(goals,'p','Cần làm rõ: '+plan.research_gaps.join(' · '));}
    if(planner.revisions.length>1){
      const versions=details(goals,'Lịch sử kế hoạch');
      for(const v of planner.revisions)line(versions,'v'+v.revision+' · '+v.target_outcome,v.digest.slice(0,12),label(v.status));
    }
    if(proposal) {
      const proposed=details(goals,'Xem bản chờ duyệt v'+proposal.revision);
      line(proposed,proposal.product,proposal.audience,label(proposal.status));
      add(proposed,'p',proposal.objective);
      if(proposal.target_outcome!==proposal.objective)add(proposed,'p',proposal.target_outcome);
      add(proposed,'p',proposal.measurement_plan.kpi);
      add(proposed,'p',proposal.duration_days+' ngày · '+money(proposal.budget_vnd)+' · '+proposal.channels.join(', '));
      if(proposal.buyer_action==='appointment')add(proposed,'p',proposal.secondary_conversions?.includes('rfq')?
        'Tiếp nhận lịch hẹn và yêu cầu báo giá riêng biệt.':'Chỉ tiếp nhận lịch hẹn.');
      for(const [kind,ref] of Object.entries(proposal.manifests))
        line(proposed,kinds[kind],ref.workflow+' · Brief '+ref.brief_id+' · Manifest '+ref.id+' · SHA-256 '+ref.digest);
      for(const item of proposal.work_packages)
        line(proposed,kinds[item.kind]||item.kind,department(item.role)+' · '+item.criteria,'Ngày '+item.due_day);
      add(proposed,'small','SHA-256 kế hoạch · '+proposal.digest);
      command(proposed,'Duyệt phiên bản '+proposal.revision,()=>({path:'/engine/plans/'+proposal.id+'/approve',
        idField:'key',payload:{expected_digest:proposal.digest}}));
    }
    if(active)productionPack(goals,active);
    planEditor(goals,planner);
    const timeline=card(grid,'Lịch làm việc và phân công');
    if(plan)for(const item of plan.work_packages)line(timeline,kinds[item.kind]||item.kind,department(item.role)+' · '+item.criteria,'Ngày '+item.due_day);
    else add(timeline,'p','Lịch và vai trò phụ trách xuất hiện sau khi lập kế hoạch.');
    const assets=card(grid,'Sản xuất và hàng chờ QA');
    for(const [kind] of Object.entries(active?.manifests||{})) {
      const run=production.runs.find(r=>r.kind===kind);
      if(run)line(assets,kinds[kind],run.checkpoint_count+' checkpoint · '+run.id.slice(0,8),label(run.state));
      else command(assets,'Xếp việc '+(kinds[kind]||kind),()=>({path:'/engine/plans/'+active.id+'/runs/'+kind,payload:null}));
    }
    for(const item of production.assets) {
      const b=details(assets,item.title+' · '+label(item.status));add(b,'p',item.body);
      add(b,'small',(origins[item.provenance] || item.provenance)+' · v'+item.revision+' · '+item.digest.slice(0,12));
      if(item.deliverable_id){const a=add(b,'a','Mở hàng chờ duyệt');a.href='#/reviews';}
    }
    if(!production.assets.length)add(assets,'p','Chưa có tài sản được tạo cho kế hoạch đã duyệt.');
    const ledger=card(grid,'Đơn vị công việc');
    for(const u of ops.work_units){
      const unit=details(ledger,(kinds[u.category]||u.expected_output)+' · '+label(u.status));
      add(unit,'p',u.assigned_role+' · '+u.criteria);
      if(u.artifact_digest)add(unit,'small','SHA-256 · '+u.artifact_digest);
      if(u.acceptance)add(unit,'p','Biên nhận '+u.acceptance.share_receipt+' · '+label(u.acceptance.status));
      if(u.cost_coverage){
        const c=u.cost_coverage;
        add(unit,'p','Token đã ghi nhận (vào/ra): '+(c.observed_input_tokens??'chưa đo')+' / '+(c.observed_output_tokens??'chưa đo')+
          ' · Lượt đủ số đo: '+c.fully_metered_attempts+'/'+c.attempts.length);
        const missing={model:'phí model',compute:'tài nguyên máy',tools:'công cụ',human:'nhân công',unfinished_work:'công việc đang mở',
          attempt_inventory:'nhật ký lượt chạy',unmeasured_attempts:'số liệu của lượt chạy'};
        add(unit,'small',u.cost_coverage.missing.length?'Cần đối soát: '+u.cost_coverage.missing.map(k=>missing[k]||k).join(', '):
          'Chi phí có chứng từ: '+money(u.cost_coverage.verified_vnd));
      }
      for(const entry of u.labor)add(unit,'p',entry.observation+' · '+entry.seconds+' giây · '+money(entry.allocated_cost_vnd));
      const form=add(details(unit,'Ghi nhận thời gian thực hiện'),'form');
      const phase=pick(form,'Loại công việc',[['clarification','Làm rõ brief'],['editing','Biên tập'],['qa','Kiểm tra QA'],['production','Sản xuất']]);
      const seconds=field(form,'Thời gian đã đo (giây)','number');seconds.min=0;
      const fee=field(form,'Chi phí phân bổ (VND, nếu đã đo)','number','',false);fee.min=0;
      const note=field(form,'Căn cứ ghi nhận','text');
      command(form,'Ghi công thực hiện',()=>sandbox({id:u.plan_id},{kind:'labor',package_id:u.id,phase:phase.value,
        seconds:seconds.valueAsNumber,allocated_cost_vnd:fee.value===''?null:fee.valueAsNumber,observation:note.value}),{form:true});
    }
    if(!ops.work_units.length)add(ledger,'p','Đơn vị công việc được ghi trước lúc thực hiện.');
    else{
      line(ledger,'Công việc được doanh nghiệp tiếp nhận','',String(ops.business_accepted_units));
      line(ledger,'Chi phí trên bản được tiếp nhận','Gồm chi phí sản xuất của các lần thử',money(ops.cost_per_business_accepted_vnd));
    }
    const destinations=active?controls(grid,active,production,ops):{};
    const progress=details(assets,'Tiến độ theo bộ phận');
    for(const u of ops.work_units.filter(u=>u.plan_id===active?.id)){
      line(progress,department(u.assigned_role),kinds[u.category]||u.category,label(u.status));
    }
    if(!active)add(progress,'p','Duyệt kế hoạch để giao việc cho từng bộ phận.');
    const funnel=card(grid,isService ? 'Lịch hẹn dịch vụ trong sandbox' : 'Từ RFQ đến doanh thu sandbox');
    if (report.primary_measurement) {
      const metric = report.primary_measurement;
      const primary = add(funnel, 'section');
      primary.setAttribute('data-primary-kpi', String(metric.contract.revision));
      add(primary, 'h4', 'KPI chính của kế hoạch');
      add(primary, 'p', metric.definition);
      const value = metric.ratio === null ? 'Chưa có mẫu số' : new Intl.NumberFormat('vi-VN', {
        style: 'percent', maximumFractionDigits: 1
      }).format(metric.ratio);
      line(primary, 'Tỷ lệ trong kỳ', metric.numerator + ' / ' + metric.denominator, value);
      if(metric.attribution){
        line(primary, 'Có nguồn trang đích', 'Cùng bản trang đã duyệt trên lượt vào và biểu mẫu', String(metric.attribution.landing_asset));
        line(primary, 'Có nguồn media', 'Lượt vào gắn với tác vụ media đã thực thi', String(metric.attribution.media_action));
        line(primary, 'Chưa rõ nguồn media', 'Trong mẫu số của KPI', String(metric.attribution.unknown_media_action));
        line(primary, 'Thiếu nguồn', 'Chưa đối chiếu được trang đích hoặc tác vụ media', String(metric.unattributed));
      }else{
        line(primary, 'Chưa rõ nguồn media', 'Báo cáo trước khi có đối chiếu phiên bản trang đích', String(metric.unattributed));
      }
      line(primary, 'Phiên web', 'Chỉ số phụ trong cùng kỳ', String(metric.secondary_metrics[0].value));
    }
    const quoteReport=isService?report.secondary_rfq_funnel:report;
    if (quoteReport) {
      const parent=isService?add(funnel,'section'):funnel;
      if(isService){
        parent.dataset.secondaryRfq=quoteReport.plan_id;
        add(parent,'h4','Báo giá phụ của kế hoạch');
        add(parent,'p','Số liệu sandbox từ khi duyệt phiên bản này. Mỗi yêu cầu báo giá được tính một lần.');
      } else line(parent,'Phiên','',String(quoteReport.sessions));
      for(const [key,text] of [['rfqs','Yêu cầu báo giá'],['qualified_leads','Đủ điều kiện'],['sales_accepted','Sales tiếp nhận'],
        ['quotations','Báo giá'],['confirmed_orders','Đơn xác nhận'],['cancelled_orders','Đơn hủy']])line(parent,text,'',String(quoteReport[key]));
      line(parent,'Doanh thu sau điều chỉnh','Số liệu sandbox',money(quoteReport.confirmed_revenue_vnd));
      line(parent,'Có nguồn chiến dịch','',money(quoteReport.attributed_revenue_vnd));
      line(parent,'Thiếu nguồn','',money(quoteReport.unattributed_revenue_vnd));
      line(parent,'Hoàn tiền','',money(quoteReport.refunds_vnd));
    }
    if(ops.appointment_summary.requests || plan?.buyer_action==='appointment'){
      const a=ops.appointment_summary;
      add(funnel,'h4','Lịch dịch vụ toàn chiến dịch');
      for (const [key, label] of [['requests','Yêu cầu đặt lịch'],['confirmed','Lịch từng được xác nhận'],
        ['completed','Buổi đã hoàn tất'],['cancelled','Đã hủy'],['no_show','Vắng mặt']]) {
        line(funnel, label, 'Toàn chiến dịch', String(a[key]));
      }
    }
    const opt=card(grid,'Đề xuất tối ưu');drawOptimization(opt,active,ops);
    for(const [key,name,section] of [['overview','Tổng quan',kpis],['plan','Kế hoạch',goals],
      ['production','Sản xuất',assets],['execution','Thực thi',destinations.actions],
      ['sales','Lead và Sales',destinations.sales],['analytics','Phân tích',funnel]]) {
      const jump=add(nav,'button',name,'secondary');
      jump.type='button';
      if(!section){jump.disabled=true;continue;}
      section.id='engine-area-'+key;
      section.tabIndex=-1;
      section.setAttribute('aria-label',name);
      jump.setAttribute('aria-controls',section.id);
      jump.onclick=()=>section.focus();
    }
    const reload=add(board,'button','Tải lại trạng thái','secondary');reload.type='button';reload.onclick=load;
  }
  function productionPack(parent,plan){
    const panel=details(parent,'Bộ nội dung và kế hoạch quảng cáo');
    const epoch=generation, target=route()+'/engine/plans/'+encodeURIComponent(plan.id)+'/content-pack';
    let loading=false, rendered=false;
    panel.ontoggle=async()=>{
      if(!panel.open || loading || rendered)return;
      loading=true;
      let child=panel.querySelector('section');
      if(!child)child=add(panel,'section');
      child.setAttribute('aria-busy','true');child.textContent='Đang lấy bản theo kế hoạch đã duyệt…';
      try{
        const pack=await api(target);
        if(epoch!==generation || !panel.isConnected)return;
        child.replaceChildren();rendered=true;
        add(child,'p','Bản nháp nội bộ · Kế hoạch v'+pack.plan_revision+' · '+pack.plan_digest.slice(0,12));
        for(const post of pack.social){
          const item=details(child,post.platform+' · '+post.pillar);
          add(item,'p',post.copy).style.whiteSpace='pre-line';
        }
        const page=details(child,'Trang web và tìm kiếm');
        for(const value of [pack.website.headline,pack.website.body,pack.website.commercial_terms,
          pack.website.cta,pack.organic_search.question,pack.organic_search.answer])add(page,'p',value).style.whiteSpace='pre-line';
        const ad=details(child,'Advertising Studio · Mẫu quảng cáo tìm kiếm');
        add(ad,'p',pack.objective);add(ad,'small','Nhóm người mua: '+pack.audience);
        const format=add(ad,'section',null,'engine-card');
        add(format,'strong',pack.advertising.headlines.join(' · '));
        for(const description of pack.advertising.descriptions)add(format,'p',description);
        for(const item of pack.advertising.ad_groups)line(ad,item.hypothesis,'Ngân sách đề xuất',money(item.budget_vnd));
        add(ad,'p',pack.advertising.experiment);
        const measure=pack.advertising.measurement;
        if(measure.status==='requires_measurement_contract'){
          add(ad,'p','Cần ghim định nghĩa KPI trước khi dùng kế hoạch đo: '+measure.approved_label);
        }else{
          const eventLabel={requested:'yêu cầu đặt lịch đủ điều kiện',confirmed:'lịch được nhân sự xác nhận',completed:'buổi được người phụ trách xác nhận hoàn tất'};
          add(ad,'strong',plan.measurement_plan.kpi+' · KPI v'+measure.revision);
          line(ad,'Tử số',eventLabel[measure.numerator.event]||measure.numerator.event);
          line(ad,'Mẫu số',eventLabel[measure.denominator.event]||measure.denominator.event);
          line(ad,'Kỳ đối soát',measure.window_days+' ngày · UTC');
        }
        for(const issue of pack.advertising.format_issues)add(ad,'p','Cần biên tập '+issue.field+' '+(issue.variant||'')+(issue.limit?' · '+issue.length+'/'+issue.limit+' ký tự':' · kiểm số biến thể'));
        const destination=pack.advertising.destination;
        if(destination.status==='approved'){
          line(ad,'Trang đích sandbox đã duyệt','Bản Studio '+destination.studio_revision+' · '+destination.file_digest.slice(0,12));
          const preview=add(ad,'button','Xem trang đích đã duyệt');preview.type='button';
          preview.onclick=async()=>{
            preview.disabled=true;
            try{
              const live=(await api(target)).advertising.destination;
              if(live.status!=='approved'||live.package_digest!==destination.package_digest)throw new Error('Trang đích đã đổi. Mở lại kế hoạch để đối chiếu.');
              const artifact=await api(live.download_url);
              if(artifact.sha256!==live.file_digest)throw new Error('Dấu vân tay của tệp đã đổi.');
              const bytes=Uint8Array.from(atob(artifact.base64),c=>c.charCodeAt(0));
              const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
              if(digest!==live.file_digest)throw new Error('Nội dung tải về không khớp biên nhận.');
              if(epoch!==generation||!panel.isConnected)return;
              const frame=add(ad,'iframe');
              frame.title='Bản xem trang đích sandbox';frame.setAttribute('sandbox','');frame.referrerPolicy='no-referrer';
              frame.style.cssText='display:block;width:100%;height:26rem;border:0';
              frame.srcdoc=new TextDecoder().decode(bytes);
              preview.remove();
            }catch(error){if(epoch===generation)status.textContent=error.message;preview.disabled=false;}
          };
        }else add(ad,'p','Đích đến cần chọn trong Landing Studio.');
        add(ad,'small','Số tiền bản nháp đã chi '+money(pack.advertising.external_spend_vnd));
        const cal=details(child,'Lịch biên tập · '+pack.calendar_timezone);
        for(const item of pack.calendar)line(cal,item.date+' · '+department(item.owner),item.acceptance,kinds[item.kind]||item.kind);
        add(child,'small','Giả thuyết thị trường cần đối chiếu với bằng chứng theo phạm vi chiến dịch.');
      }catch(error){if(epoch===generation)child.textContent=error.message;}
      finally{loading=false;child.setAttribute('aria-busy','false');}
    };
  }
  function sandbox(plan,payload) {
    return {path:'/sandbox/commands',idField:'request_id',payload:{...payload,plan_id:plan.id}};
  }
  function controls(grid,plan,production,ops) {
    const actions=card(grid,'Thực thi trong sandbox');
    for(const action of ops.actions){
      const row=line(actions,action.id,money(action.cost_vnd)+' · '+(action.due_at || ''),label(action.state));
      if(action.target)add(row,'small',action.target.channel+' · '+action.target.group+' · '+action.target.destination+' · '+(action.execution_mode==='scheduled'?'Bộ điều phối CLI cục bộ':'Thực thi nhóm bằng tay'));
      else add(row,'small','Tài liệu đã qua QA · thao tác sandbox thủ công');
      if(action.sandbox_output)add(row,'small','Biên nhận '+action.execution_receipt+' · '+action.sandbox_output.content_sha256.slice(0,12));
      const next=({scheduled:[['authorize','Cho phép chạy'],['cancel','Hủy lịch']],authorized:[['execute','Chạy mô phỏng'],['cancel','Hủy']],
        failed:[['execute','Thử lại'],['cancel','Hủy']]})[action.state]||[];
      for(const [kind,name] of next){
        if(action.plan_id!==plan.id && kind!=='cancel')continue;
        if(kind==='execute' && action.execution_mode==='scheduled')continue;
        if(kind==='authorize' && action.scheduled_by===actor)continue;
        command(row,name,()=>sandbox({id:action.plan_id},{kind,action_id:action.id}));
      }
    }
    if(!ops.actions.length)add(actions,'p','Chưa có lịch thực thi.');
    // Schedule the complete signed customer document once even when it projects several asset groups.
    const ready=Array.from(new Map(production.assets.filter(x=>x.deliverable_id && ['approved','shared'].includes(x.status))
      .map(x=>[x.deliverable_id,x])).values());
    if(ready.length){
      const form=add(details(actions,'Lên lịch từ tài sản đã qua QA'),'form');
      const doc=pick(form,'Bản đã duyệt',ready.map(a=>[a.deliverable_id,a.title+' · v'+a.revision]));
      const id=field(form,'Mã lịch','text'), due=field(form,'Thời điểm chạy (giờ địa phương)','datetime-local');
      const cost=field(form,'Chi phí mô phỏng (VND)','number','0');cost.min=0;
      command(form,'Lưu lịch chờ duyệt',()=>{const a=ready.find(x=>x.deliverable_id===doc.value);
        return sandbox(plan,{kind:'schedule',action_id:id.value,deliverable_id:a.deliverable_id,
          expected_revision:a.revision,expected_digest:a.document_digest,due_at:new Date(due.value).toISOString(),cost_vnd:cost.valueAsNumber});
      },{form:true});
    }
    const sales=card(grid,'Tiếp nhận và bàn giao Sales');
    campaignOperationForms({plan,production,ops,actions,sales,add,details,field,pick,command,sandbox,actor});
    const visit=add(details(sales,'Ghi nhận phiên truy cập sandbox'),'form');
    const visitId=field(visit,'Mã phiên','text'), visitor=field(visit,'Mã khách tổng hợp','text');
    const origin=pick(visit,'Nguồn tác vụ',[['','Chưa rõ nguồn'],...ops.actions.filter(a=>a.plan_id===plan.id && a.state==='executed').map(a=>[a.id,a.id])]);
    let visited;
    command(visit,'Lưu phiên',()=>sandbox(plan,{kind:'session',session_id:visitId.value,actor_key:visitor.value,
      action_id:origin.value||null,occurred_at:visited??=new Date().toISOString()}),{form:true});
    if(plan.selling_unit && (plan.buyer_action==='rfq' || plan.secondary_conversions?.includes('rfq'))) {
      const form=add(details(sales,'Ghi nhận yêu cầu báo giá'),'form');
      const id=field(form,'Mã yêu cầu','text'),qty=field(form,'Số lượng ('+plan.selling_unit+')','number','',false);
      qty.min='0.001';qty.step='any';
      const loc=field(form,'Địa bàn giao','text','',false),day=field(form,'Ngày cần hàng','date','',false);
      const purpose=pick(form,'Mục đích liên hệ do khách chọn',[['none','Chưa được phép phản hồi'],['quote_request','Phản hồi yêu cầu báo giá']]);
      const extras=commercialDetails(form,plan.selling_unit);
      const session=pick(form,'Nguồn phiên truy cập',[['','Chưa rõ nguồn'],...ops.sessions.filter(s=>s.plan_id===plan.id).map(s=>[s.id,s.id])]);
      let observed;
      command(form,'Ghi nhận RFQ sandbox',()=>sandbox(plan,{kind:'rfq',rfq_id:id.value,occurred_at:observed??=new Date().toISOString(),
        product_id:plan.product_id,unit:plan.selling_unit,quantity:qty.value||null,location:loc.value||null,required_date:day.value||null,
        contact_purpose:purpose.value,session_id:session.value||null,details:extras()}),{form:true});
    }
    for(const lead of ops.leads) {
      const summary=details(sales,lead.id+' · '+label(lead.state));
      add(summary,'p',[lead.quantity,lead.unit,lead.location,lead.required_date].filter(Boolean).join(' · '));
      if(lead.details)add(summary,'p',Object.entries(lead.details).filter(([k,v])=>k!=='schema_id' && v).map(([,v])=>v).join(' · '));
      for(const item of lead.feedback || [])add(summary,'p',item.text);
      const originatingPlan={id:lead.plan_id};
      if(lead.state==='received') {
        const form=add(details(summary,'Bổ sung thông tin theo yêu cầu của khách'),'form');
        const qty=field(form,'Số lượng ('+lead.unit+')','number',lead.quantity||'');qty.step='any';qty.min='0.001';
        const place=field(form,'Địa bàn giao','text',lead.location||''),when=field(form,'Ngày cần hàng','date',lead.required_date||'');
        const consent=field(form,'Khách yêu cầu phản hồi báo giá','checkbox');
        command(form,'Lưu thông tin bổ sung',()=>sandbox(originatingPlan,{kind:'complete_rfq',rfq_id:lead.id,expected_revision:lead.revision,
          quantity:qty.value,location:place.value,required_date:when.value,contact_purpose:consent.checked?'quote_request':'none'}),{form:true});
      }
      const steps=({received:['reject'],qualified:['assign','reject'],assigned:['accept','reject','cancel'],accepted:['quote','reject','cancel'],
        quoted:['order','reject','cancel'],ordered:['confirm','cancel'],confirmed:['refund','correct','cancel']})[lead.state]||[];
      if(!steps.length)continue;
      const names={assign:'Nhận phụ trách',accept:'Sales tiếp nhận',reject:'Từ chối',quote:'Ghi nhận báo giá',order:'Ghi nhận đơn',
        confirm:'Xác nhận doanh thu',refund:'Ghi hoàn tiền',correct:'Đính chính số tiền',cancel:'Ghi nhận hủy'};
      const form=add(summary,'form'),step=pick(form,'Bước Sales',steps.map(s=>[s,names[s]]));
      const note=field(form,'Phản hồi của Sales','text','',false),amount=field(form,'Số tiền khi xác nhận hoặc điều chỉnh (VND)','number','',false);
      amount.min=1;let observed;
      command(form,'Lưu quyết định Sales',()=>sandbox(originatingPlan,{kind:'sales',rfq_id:lead.id,expected_revision:lead.revision,
        occurred_at:observed??=new Date().toISOString(),step:step.value,...(note.value?{reason:note.value}:{}),
        ...(step.value==='assign'?{assignee_id:actor}:{}),...(['confirm','correct','refund'].includes(step.value)?{amount_vnd:amount.valueAsNumber}:{})}),{form:true});
    }
    return {actions,sales};
  }
  function commercialDetails(form,unit) {
    const config = [
      [['piece','box','m²','tonne','kg'],'materials_v1','application','Ứng dụng vật liệu'],
      [['machine','visit','service'],'service_v1','service_scope','Phạm vi dịch vụ'],
      [['participant','subscription_month','subscription_year'],'seats_v1','program','Chương trình đăng ký']
    ].find(([units])=>units.includes(unit));
    if(!config)return ()=>null;
    const [,schema,key,title]=config, value=field(form,title+' (nếu có)','text','',false);
    const mode=schema==='seats_v1'?pick(form,'Hình thức',[['onsite','Trực tiếp'],['online','Trực tuyến'],['hybrid','Kết hợp']]):null;
    return ()=>value.value.trim()?{schema_id:schema,[key]:value.value.trim(),...(mode?{delivery_mode:mode.value}:{})}:null;
  }
  function drawOptimization(parent,active,ops){
    parent.dataset.optimization='true';
    const utc=new Intl.DateTimeFormat('vi-VN',{dateStyle:'short',timeStyle:'medium',timeZone:'UTC'});
    const proposal=ops.optimization;
    if(proposal?.recommendation)add(parent,'p',proposal.recommendation);
    else add(parent,'p','Đối soát kết quả Sales và nguồn doanh thu trước khi giao việc tối ưu.');
    function showEvidence(target,evidence){
      if(!evidence)return;
      const metric=evidence.primary_measurement;
      const cutoff=utc.format(new Date(evidence.as_of_inclusive))+' UTC';
      const period=metric ? 'Sau '+utc.format(new Date(metric.window_start_exclusive))+' UTC đến '+cutoff
        : 'Trọn vòng đời kế hoạch, chốt lúc '+cutoff;
      const source={sandbox_appointment_receipts:'Biên nhận lịch dịch vụ',sandbox_rfq_receipts:'Biên nhận RFQ'}[evidence.source]||'Chưa có nguồn đo';
      line(target,source+' · '+period,'KPI: '+evidence.kpi);
      if(metric)line(target,metric.definition,'Số đạt / số đủ điều kiện: '+metric.numerator+' / '+metric.denominator);
      add(target,'small','Kế hoạch '+evidence.plan_id);
    }
    showEvidence(parent,proposal?.evidence);
    if(!active)return;
    const proposalId=crypto.randomUUID();
    command(parent,'Tạo đề xuất từ báo cáo',()=>sandbox(active,{kind:'propose_optimization',proposal_id:proposalId}));
    for(const item of ops.proposals||[]) {
      const row=line(parent,item.recommendation||item.id,item.work_package?.criteria,label(item.status));
      if(item.evidence?.version==='plan-optimization/2'){
        showEvidence(row,item.evidence);
        if(item.plan_id===active.id && item.status==='proposed' && item.author!==actor)command(row,'Duyệt gói việc tối ưu',()=>sandbox(active,{kind:'approve_optimization',proposal_id:item.id}));
      }else if(item.status==='proposed')add(row,'small','Đề xuất cũ dùng tổng chiến dịch. Tạo đề xuất mới cho kế hoạch đang duyệt.');
    }
  }
  async function load() {
    reset(); if(!selected)return;
    const epoch=generation;abort=new AbortController();const source=route(),signal=abort.signal;
    status.textContent='Đang đọc kế hoạch và biên nhận…';panel.setAttribute('aria-busy','true');
    const get=path=>api(source+path,'GET',null,false,signal);
    try {
      const [planner,ops]=await Promise.all([get('/engine/planner'),get('/sandbox')]);
      const prod=planner.active?await get('/engine/plans/'+planner.active.id+'/production'):{runs:[],assets:[]};
      if(epoch!==generation)return;draw(planner,prod,ops);status.textContent='Đã cập nhật dữ liệu sandbox.';
    }catch(e){if(epoch===generation){board.replaceChildren();status.textContent=e.message;const retry=add(board,'button','Thử tải lại');retry.onclick=load;}}
    finally{if(epoch===generation)panel.removeAttribute('aria-busy');}
  }
  return {scope};
}
