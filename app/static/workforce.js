/* Keep the intake form separate from agency-only checkpoints and QA. */
function createWorkforce(root, api, notify, onActivity=()=>{}) {
  let revision = 0;
  function reset() { revision++; root.inert=false; root.replaceChildren(); }
  function node(parent, tag, text) {
    const item=document.createElement(tag);
    if (text) item.textContent=text;
    parent.append(item); return item;
  }
  function field(parent, label, tag) {
    const control=node(node(parent,'label',label),tag);
    control.setAttribute('aria-label',label); return control;
  }
  function action(parent, caption, run) {
    const b=node(parent,'button',caption);
    b.type='button';
    b.onclick=async()=>{ b.disabled=true; try {await run();} catch(e){notify(e.message,true);} finally{b.disabled=false;} };
  }
  const labels={director:'Director',research:'Research',strategy:'Strategy',content:'Content',storyboard:'Storyboard',seo:'SEO',creative:'Creative',ads:'Ads',analytics:'Analytics'};
  function showContentHandoff(host, output) {
    let handoff;
    try {handoff=JSON.parse(output.sections.content_handoff);} catch {return false;}
    if(handoff?.version!=='amc.content-storyboard-handoff/1')return false;
    const panel=node(host,'section');panel.className='content-handoff';panel.setAttribute('aria-label','Bàn giao nội dung cho storyboard');
    node(panel,'h5','Bàn giao nội dung cho storyboard');
    const scope=node(panel,'dl');scope.className='handoff-scope';
    for(const [label,value] of [['Đối tượng',handoff.audience],['Mục đích',handoff.purpose],['Kênh và định dạng',handoff.channel==='vertical-social'?'Mạng xã hội · khung dọc 9:16':handoff.channel]]){
      const group=node(scope,'div');node(group,'dt',label);node(group,'dd',value);
    }
    const script=node(panel,'div');script.className='handoff-script';
    node(script,'h6','Câu mở');node(script,'p',handoff.channel_copy.opening);
    node(script,'h6','Nội dung theo nguồn');
    for(const fact of handoff.channel_copy.declarations){
      const group=node(script,'div');group.className='handoff-declaration';
      node(group,'strong',fact.source_id);
      const lines=node(group,'ul');for(const line of fact.lines)node(lines,'li',line);
    }
    node(script,'h6','Lời mời hành động');node(script,'p',handoff.channel_copy.action);
    const detail=node(panel,'details');node(detail,'summary','Chỉ dẫn dựng và căn cứ');
    node(detail,'p',handoff.production_direction);
    node(detail,'h6','Câu hỏi cần kiểm chứng');node(detail,'p',handoff.question_to_validate);
    if(handoff.audience_hypotheses.length){
      node(detail,'h6','Giả thuyết về người mua');const list=node(detail,'ul');
      for(const item of handoff.audience_hypotheses)node(list,'li',item);
    }
    node(detail,'h6','SHA-256 của bản bàn giao');node(detail,'code',output.handoff_digest);
    return true;
  }
  const qaRules={cta_action:'Kiểm tra lời kêu gọi hành động',brief_alignment:'Đối chiếu mục tiêu brief',
    brand_alignment:'Đối chiếu thông tin sản phẩm trong Brand Kit',audience_alignment:'Đối chiếu đối tượng',
    offer_alignment:'Đối chiếu sản phẩm và đề nghị',brand_instruction:'Đối chiếu từ ngữ Brand Kit yêu cầu tránh',
    page_alignment:'So sánh với nội dung trang',intent_alignment:'Đối chiếu ý định tìm kiếm với trang',
    metadata_length:'Độ dài ngoài khoảng gợi ý',duplicate_metadata:'Meta trùng tiêu đề',
    claim_evidence:'Kiểm tra nguồn của nhận định',quote_context:'Có câu trùng nguồn, cần kiểm tra ngữ cảnh'};
  const graphStates={waiting:'Đang chờ',ready:'Sẵn sàng',running:'Đang xử lý',succeeded:'Hoàn tất',failed:'Thất bại',blocked:'Bị chặn',retry_wait:'Chờ thử lại'};
  function showGraph(info,graph) {
    const view=node(info,'section');view.setAttribute('aria-label','Trạng thái workflow');
    node(view,'h4','Mẫu '+graph.template+' · Phiên bản '+graph.revision);
    if(graph.registry) {
      view.style.overflowWrap='anywhere';
      node(view,'p',graph.registry.workflow+' · Manifest '+graph.registry.manifest_digest);
    }
    const skills=Object.fromEntries((graph.contract?.nodes||[]).map(n=>[n.node_id,n.skill_type]));
    const caption=id=>skills[id]?labels[skills[id]]+' ('+id+')':(labels[id]||id);
    if(graph.phase)node(view,'p',({planning:'Đang lập kế hoạch',validating:'Đang kiểm tra kế hoạch',frozen:'Đã chốt kế hoạch',executing:'Đang thực thi'})[graph.phase]);
    if(graph.max_parallel_nodes===2)node(view,'p','Tối đa 2 node đồng thời');
    if(graph.digest)node(view,'p','SHA-256: '+graph.digest);
    const list=node(view,'ul');
    for(const n of graph.nodes) {
      const item=node(list,'li');item.dataset.node=n.node_id;
      node(item,'strong',(n.node_id==='join'?'Join':caption(n.node_id))+' · '+graphStates[n.status]);
      const contract=graph.registry?.nodes?.find(c=>c.node_id===n.node_id);
      if(contract) {
        node(item,'p',contract.role_id+'@'+contract.contract_version+' · '+contract.skill_id+'@'+contract.skill_version);
        node(item,'p','Ngân sách node: '+contract.exposure+' / '+contract.node_cap+' micro-USD');
        if(contract.overage)node(item,'p','Cần đối soát: vượt '+contract.overage+' micro-USD');
      }
      if(n.missing.length)node(item,'p','Chờ đầu ra: '+n.missing.map(caption).join(', '));
      if(n.status==='retry_wait' && n.ready_at)node(item,'p','Thử lại từ '+new Date(n.ready_at).toLocaleTimeString());
      if(n.error && n.error!=='ok')node(item,'p','Lỗi gần nhất: '+n.error);
      if(n.node_id!=='join')node(item,'p',n.attempts+' lượt · giữ '+n.held+' · đã chi '+n.spent+' micro-USD');
    }
  }
  const waitLabels={dependency_pending:'Chờ checkpoint tiền nhiệm',retry_backoff:'Đang chờ tới lượt thử lại',
    adapter_unavailable:'Thiếu dispatcher tương thích',report_waiting_adapter:'Report chờ dispatcher tương thích',
    telemetry_unknown:'Chưa đủ dữ liệu từ các replica',worker_unavailable:'Chưa có worker sẵn sàng',
    worker_busy:'Worker phù hợp đang bận',capacity_full:'Agency đã dùng hết slot',budget_insufficient:'Ngân sách còn lại chưa đủ',
    agency_disabled:'Pool của agency đang dừng',run_slot_busy:'Run còn lease giữ slot',
    attempt_limit:'Đã hết lượt thử',prompt_version:'Cần kiểm tra phiên bản prompt'};
  function showWaits(parent,data){
    parent.replaceChildren();
    node(parent,'p','Thời điểm quan sát '+new Date(data.observed_at).toLocaleString());
    for(const item of data.nodes){
      if(!item.wait_reasons.length && !['lease_active','awaiting_reconciliation','report'].includes(item.phase))continue;
      const row=node(parent,'div');
      node(row,'strong',item.node_id);
      for(const reason of item.wait_reasons)node(row,'p',waitLabels[reason]||reason);
      if(item.phase==='lease_active')node(row,'p','Lease đang hoạt động');
      if(item.phase==='awaiting_reconciliation')node(row,'p','Chờ đối soát lease');
      if(item.phase==='report' && !item.wait_reasons.length)node(row,'p','Report đang chờ xử lý');
      if(item.retry_at)node(row,'p','Có thể thử lại từ '+new Date(item.retry_at).toLocaleString());
    }
  }
  const states={queued:'Đang chờ worker',running:'Đang xử lý',failed:'Đã dừng',awaiting_qa:'Đã chuyển sang QA'};
  const assetNames={research_notes:'Ghi chú nghiên cứu',strategy_decisions:'Quyết định chiến lược',buyer_copy:'Nội dung trang dành cho người mua',
    seo_fields:'Nội dung SEO',evidence_report:'Nguồn cho từng dữ kiện',measurement_plan:'Kế hoạch đo lường',customer_preview:'Bản xem trước cho khách'};
  const fieldNames={research_question:'Câu hỏi nghiên cứu',evidence_needed:'Bằng chứng cần bổ sung',segment:'Phân khúc',buyer_problem:'Vấn đề của người mua',
    positioning:'Định vị',rationale:'Lý do lựa chọn',channel_choice:'Lựa chọn kênh',test_hypothesis:'Giả thuyết thử nghiệm',
    headline:'Tiêu đề',value_proposition:'Giá trị đề xuất',benefit:'Lợi ích',call_to_action:'Lời mời hành động',
    page_title:'Tiêu đề SEO',meta_description:'Mô tả',search_intent:'Ý định tìm kiếm',selected_kpi:'KPI được chọn trong brief',
    measurable_action:'Sự kiện cần đo',measurement_method:'Cách đo',hypotheses:'Giả thuyết từ brief',gaps:'Thông tin còn thiếu',
    title:'Tiêu đề',body:'Nội dung'};
  function showMarketingAssets(info,report) {
    const section=node(info,'section');
    section.setAttribute('aria-label','Tài liệu Marketing của lần chạy');
    node(section,'h4','Tài liệu Marketing của lần chạy');
    node(section,'p','Chiến lược, giả thuyết, nội dung và SEO là đề xuất để biên tập. QA từng nhận định chỉ áp dụng cho tiêu đề và nội dung bản xem trước của khách.');
    const values=(parent,fields)=>{
      const list=node(parent,'dl');list.className='knowledge-summary';
      for(const [key,value] of Object.entries(fields)){
        if(!value?.length)continue;
        const row=node(list,'div');node(row,'dt',fieldNames[key]||key);
        node(row,'dd',Array.isArray(value)?value.join('\n'):value).style.whiteSpace='pre-wrap';
      }
    };
    const roleFor={strategy_decisions:'strategy',buyer_copy:'content',seo_fields:'seo',measurement_plan:'strategy'};
    const outputs=report.sections;
    for(const [key,caption] of Object.entries(assetNames)){
      const details=node(section,'details');details.dataset.marketingAsset=key;
      node(details,'summary',caption);
      const data=outputs[key];
      if(key==='customer_preview'){
        if(!data.current){node(details,'p','Chưa có tài liệu để xem trước.');continue;}
        node(details,'h5','Bản làm việc hiện tại · lần lưu '+data.current.revision);
        values(details,{title:data.current.title,body:data.current.body});
        node(details,'p',report.evidence_coverage.current_assessment?'Đã có kết quả đối chiếu nhận định cho lần lưu này.':'Chưa có kết quả đối chiếu khớp lần lưu hiện tại.');
        const original=node(details,'details');node(original,'summary','Xem bản khi AI tạo');
        values(original,data.generated);
      }else if(key==='evidence_report'){
        node(details,'p','Các mã do role viện dẫn giúp tra cứu. Kết quả xác minh từng câu nằm ở màn hình phê duyệt của bản xem trước.');
        for(const fact of data.facts)node(details,'p',fact.handle+' · '+fact.text);
        for(const [role,handles] of Object.entries(data.suggested_handles))if(handles.length)node(details,'p',(labels[role]||role)+' · '+handles.join(', '));
      }else if(key==='research_notes'){
        values(details,{...data.fields,hypotheses:data.hypotheses,gaps:data.gaps});
      }else{
        const role=roleFor[key];
        if(!Object.keys(data).length){
          const applies=role in outputs.evidence_report.suggested_handles;
          node(details,'p',!applies?'Quy trình này không tạo phần này.':report.completed_roles.includes(role)?'Chưa có trường nội dung dùng được.':'Chờ đầu ra của '+labels[role]+'.');
        }else values(details,data);
      }
    }
    if(report.field_issues.length){
      const notes=node(section,'details');node(notes,'summary','Các trường cần biên tập ('+report.field_issues.length+')');
      for(const issue of report.field_issues){
        const reason=issue.reason==='same_text'?'trùng nội dung với '+(fieldNames[issue.other_field]||issue.other_field):
          issue.reason==='withheld'?'đã được giữ lại khỏi bản nội dung hướng tới khách':'thiếu nội dung';
        node(notes,'p',labels[issue.role]+' · '+(fieldNames[issue.field]||issue.field)+' · '+reason);
      }
    }
  }
  async function show(tenant,role,campaigns,expanded,mode) {
    const ticket=++revision; root.inert=true;
    const base='/api/tenants/'+encodeURIComponent(tenant)+'/workforce';
    const admin=['owner','admin'].includes(role), external=role==='client_viewer';
    const reload=()=>ticket===revision && show(tenant,role,campaigns,true,mode);
    let briefs,runs,recipients;
    try {
      [briefs,runs,recipients]=await Promise.all([api(base+'/briefs'),external?[]:api(base+'/runs'),
        admin && mode!=='inhouse'?api('/api/tenants/'+encodeURIComponent(tenant)+'/recipients'):[]]);
    } catch(e) {
      if(ticket!==revision)return;
      if(!external) onActivity(tenant,null,null);
      root.inert=false;root.replaceChildren();action(root,'Tải lại brief và tiến độ',reload);return;
    }
    if(ticket!==revision)return;
    if(!external) onActivity(tenant,briefs,runs);
    root.inert=false;
    const keepOpen=expanded ?? root.querySelector("details")?.open;
    root.replaceChildren();
    if(external&&!briefs.length)return;
    const box=node(root,'details');box.className='panel';box.open=Boolean(keepOpen);
    node(box,'summary',external?'Brief Marketing của bạn':'Điều phối Marketing AI');
    if(mode==='inhouse' && ['owner','admin','editor'].includes(role)){
      taskIntentForm(box,{},async(intent,campaign,key)=>{
        await api(base+'/internal-tasks','POST',{key,campaign_id:campaign,intent});
        if(ticket===revision)await reload();
      },{campaigns});
      const guide=node(box,'p','Sau khi ghi nhận mục đích, mở brief đã ghim sản phẩm trong Hồ sơ doanh nghiệp để kiểm tra căn cứ và giao việc.');
      const link=node(guide,'a','Mở hồ sơ doanh nghiệp');link.href='#/knowledge';
    }
    if(admin && mode!=='inhouse') {
      const title=field(box,'Tên bộ tài sản','input');
      const campaign=field(box,'Chiến dịch nhận brief','select');
      campaigns.forEach(c=>campaign.add(new Option(c.name,c.id)));
      const recipient=field(box,'Người giao brief','select');
      const fillRecipients=()=>{
        const selected=campaigns.find(c=>c.id===campaign.value);
        recipient.replaceChildren();
        recipients.filter(g=>selected && (!g.campaign_id||g.campaign_id===selected.id)
          &&(!g.brand_id||g.brand_id===selected.brand_id) && g.client_id===selected.client_id)
          .forEach(g=>recipient.add(new Option(g.email||g.user_id,g.user_id)));
      };
      const registryInfo=node(box,'div');
      campaign.onchange=()=>{fillRecipients();registryInfo.replaceChildren();};
      fillRecipients();
      action(box,'Quyền workflow của chiến dịch',async()=>{
        const id=campaign.value;
        if(!id)return;
        const entries=await api(base+'/registry/'+encodeURIComponent(id));
        if(ticket!==revision||campaign.value!==id)return;
        registryInfo.replaceChildren();
        if(!entries.length)node(registryInfo,'p','Chiến dịch chưa có registry PostgreSQL.');
        for(const entry of entries) {
          node(registryInfo,'h4',entry.workflow);
          for(const skill of Object.keys(entry.manifest.contracts))
            node(registryInfo,'p',(labels[skill]||skill)+' · '+({activate:'Đã cấp',disable:'Ngừng cấp mới',revoke:'Đã thu hồi'}[entry.grants[skill]]||'Chưa cấp'));
          for(const [mode,caption] of [['activate','Cấp quyền cho workflow'],['disable','Ngừng cấp cho run mới'],['revoke','Thu hồi và dừng run đang chạy']])
            action(registryInfo,caption,async()=>{
              if(mode==='revoke'&&!window.confirm('Dừng các run đang dùng workflow này trong chiến dịch?'))return;
              await api(base+'/registry/'+encodeURIComponent(id),'PUT',{workflow:entry.workflow,action:mode,skills:entry.manifest.required});
              await reload();
            });
        }
      });
      action(box,'Yêu cầu khách gửi brief',async()=>{
        if(!recipient.value||!title.value.trim())throw new Error('Chọn chiến dịch, người nhận và nhập tên bộ tài sản.');
        await api(base+'/briefs','POST',{campaign_id:campaign.value,recipient_id:recipient.value,title:title.value});await reload();
      });
    }
    for(const b of briefs) {
      const row=node(box,'details');node(row,'summary',b.title+(b.submitted?' · Đã nhận brief':' · Chờ brief'));
      if(external&&!b.submitted) {
        taskIntentForm(row,{},async intent=>{await api(base+'/briefs/'+b.id+'/task-submission','PUT',intent);await reload();},
          {title:'Yêu cầu cho AI Director',button:'Gửi yêu cầu cho đội Marketing'});
        const goal=field(row,'Mục tiêu','textarea'), audience=field(row,'Khách hàng mục tiêu','textarea');
        const offer=field(row,'Sản phẩm và đề nghị','textarea'), label=field(row,'Tên nguồn','input'), excerpt=field(row,'Trích dẫn từ nguồn','textarea');
        action(row,'Gửi brief',async()=>{
          await api(base+'/briefs/'+b.id+'/submission','PUT',{objective:goal.value,audience:audience.value,offer:offer.value,sources:[{label:label.value,excerpt:excerpt.value}]});await reload();
        });
      } else if (!external && role!=='viewer' && b.submitted && b.origin!=='internal' && !runs.some(r=>r.brief_id===b.id)) {
        const workflow=field(row,'Mẫu workflow','select');
        workflow.add(new Option('Tuyến tính','linear'));workflow.add(new Option('Content và SEO sau Strategy (diamond-v1)','diamond-v1'));
        const versions=await api(base+'/registry/'+encodeURIComponent(b.campaign_id));
        if(ticket!==revision)return;
        for(const version of versions) {
          if(version.manifest.required.every(skill=>version.grants[skill]==='activate'))
            workflow.add(new Option(version.workflow,version.workflow));
        }
        workflow.add(new Option('Director lập kế hoạch (dynamic-v1)','dynamic-v1'));
        const select=field(row,'Chuyên môn bổ sung','select');select.multiple=true;
        ['seo','creative','ads','analytics'].forEach(s=>select.add(new Option(labels[s],s)));
        const parallel=field(row,'Số node tối đa cùng chạy','select');
        parallel.add(new Option('1','1'));parallel.add(new Option('2','2'));parallel.disabled=true;
        workflow.onchange=()=>{parallel.disabled=workflow.value!=='dynamic-v1'&&!workflow.value.includes('@');select.disabled=workflow.value==='diamond-v1'||workflow.value.includes('@');
          for(const option of select.options){option.disabled=workflow.value==='dynamic-v1' && option.value!=='seo';if(option.disabled)option.selected=false;}
        };
        const budget=field(row,'Ngân sách model (USD, 0 cho local)','input');budget.type='number';budget.step='0.01';budget.min=0;budget.max=1;budget.value=0;
        action(row,'Giao việc cho AI Director',async()=>{await api(base+'/briefs/'+b.id+'/run','POST',{
          workflow:workflow.value.includes('@')?'dynamic-v1':workflow.value,...(workflow.value.includes('@')?{registry_workflow:workflow.value}:{}),max_parallel_nodes:parallel.disabled?1:Number(parallel.value),extra_skills:select.disabled?[]:Array.from(select.selectedOptions,o=>o.value),budget_microusd:Math.round(Number(budget.value)*1000000)});await reload();});
      }
    }
    if(!external) {
      action(box,'Cập nhật tiến độ',reload);
      for(const r of runs) {
        const row=node(box,'div');node(row,'h4',r.title+' · '+(states[r.state]||r.state));
        node(row,'p',r.done+'/'+r.skills.length+' bước · '+(r.workflow==='diamond-v1'?'Director → Research → Strategy → (Content + SEO) → Join':r.skills.map(s=>labels[s]).join(' → ')));
        const info=node(row,'div');action(row,'Xem kết quả và chi phí',async()=>{
          const v=await api(base+'/runs/'+r.id);if(ticket!==revision)return;
          info.replaceChildren();node(info,'p',v.journal.length+' lượt xử lý · Chi phí đã tính hoặc giữ chỗ: '+(v.reserved_microusd/1000000).toFixed(6)+' USD');
          if(v.registry?.status==='legacy_v13')node(info,'p','Lịch sử thực thi · legacy_v13');
          if(v.graph)showGraph(info,v.graph);
          if(v.graph && ['owner','admin'].includes(role)){
            const panel=node(info,'section');
            action(info,'Xem lý do node chờ',async()=>{
              const data=await api(base+'/runs/'+r.id+'/wait-diagnostics');
              if(ticket===revision)showWaits(panel,data);
            });
          }
          if(v.last_error)node(info,'p',v.last_error==='recipient_revoked'?'Đã hủy do thu hồi quyền của người giao brief.':'Lỗi: '+v.last_error);
            if(v.marketing_provenance)attachMarketingProvenance(info,v.marketing_provenance,api,()=>ticket===revision);
            let checkpointHost=info;
            if(v.marketing_artifacts){
              if(v.deliverable_id && ['owner','admin','editor'].includes(role))
                mountMarketingStudio(info,api,'/api/tenants/'+encodeURIComponent(tenant)+'/deliverables/'+encodeURIComponent(v.deliverable_id)+'/studio',role);
              showMarketingAssets(info,v.marketing_artifacts);
              checkpointHost=node(info,'details');node(checkpointHost,'summary','Nhật ký đầu ra từng vai trò');
            }
            const wf=v.graph?.registry?.workflow;
            if(['WF-08/video-storyboard@1','WF-08/video-storyboard@2'].includes(wf) && v.deliverable_id && ['owner','admin','editor'].includes(role))
              window.storyboardEditor?.mount(info,{run:v,tenantId:tenant,api,onSaved:reload});
            v.checkpoints.forEach(p=>{const info=checkpointHost;node(info,'h4',labels[p.skill]||p.skill);
            if(p.skill==='storyboard'){
              const raw=node(info,'details');node(raw,'summary','Dữ liệu storyboard gốc');node(raw,'pre',p.output.text).className='storyboard-raw';
            }else if(!(p.skill==='content' && showContentHandoff(info,p.output)))node(info,'p',p.output.text);
            node(info,'p','Nguồn: '+p.output.source_ids.map(k=>v.source_registry?.[k]?.label||k).join(', '));
            const qa=p.quality?.role_qa;
            if(qa?.scope==='node_checkpoint'){
              node(info,'h5','QA đầu ra AI · '+qa.node_id+' · '+qa.policy);
              node(info,'p','SHA-256 đầu ra '+qa.output_digest.slice(0,12));
              for(const [parent,digest] of Object.entries(qa.research_parents||{}))
                node(info,'p','Checkpoint Research '+parent+' · '+digest.slice(0,12));
              for(const f of qa.findings){
                const finding=node(info,'details');
                node(finding,'summary',f.field+' · '+(qaRules[f.rule_id]||f.rule_id));
                const ev=f.evidence;
                node(finding,'p',(f.severity==='info'?'Gợi ý đối chiếu':'Cần kiểm tra')+' · '+f.rule_id+'@'+f.rule_version);
                if(ev.text||ev.claim)node(finding,'p',ev.text||ev.claim);
                if(ev.range)node(finding,'p',ev.length+' ký tự · ngưỡng gợi ý '+ev.range.join('–'));
                if(ev.reference)node(finding,'p','Đối chiếu: '+[ev.reference].flat().join(' · '));
                if(ev.avoid)node(finding,'p','Từ ngữ cần tránh: '+ev.avoid);
                if(ev.content_parents)node(finding,'p','Node Content tiền nhiệm: '+ev.content_parents.join(', '));
                if(ev.matching_ids?.length)node(finding,'p','Nguồn có câu trùng: '+ev.matching_ids.join(', '));
                node(finding,'p','Nguồn đã dẫn: '+f.source_ids.join(', '));
              }
            }else{
              for(const f of qa?.findings||[])node(info,'p',f.field+' · '+f.rule+' · '+f.claim);
            }
            for(const f of p.quality?.claims||[]) {
              node(info,'p',(f.status==='needs_evidence'?'Cần bằng chứng':'Có câu trùng nguồn '+f.matching_ids.join(', '))+' · '+f.claim);
            }
            if(p.quality?.numbers_for_qa?.length)node(info,'p','Số liệu cần QA đối chiếu: '+p.quality.numbers_for_qa.join(', '));});
          if(v.deliverable_id)node(info,'p','Mở mục Bàn giao và duyệt nội dung để kiểm tra bộ tài sản.');
          v.approved_assets.forEach(a=>{const link=node(info,'a','Mở bộ tài sản đã duyệt · v'+a.version);link.href='?workspace='+encodeURIComponent(tenant)+'&review='+encodeURIComponent(a.id);});
        });
      }
    }
  }
  return {reset,show,pause(){ revision++; root.inert=true; }};
}
