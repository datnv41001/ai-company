/* Keep the intake form separate from agency-only checkpoints and QA. */
function createWorkforce(root, api, notify) {
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
  const labels={director:'Director',research:'Research',strategy:'Strategy',content:'Content',seo:'SEO',creative:'Creative',ads:'Ads',analytics:'Analytics'};
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
      const contract=graph.registry?.nodes.find(c=>c.node_id===n.node_id);
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
  const states={queued:'Đang chờ worker',running:'Đang xử lý',failed:'Đã dừng',awaiting_qa:'Đã chuyển sang QA'};
  async function show(tenant,role,campaigns,expanded) {
    const ticket=++revision; root.inert=true;
    const base='/api/tenants/'+encodeURIComponent(tenant)+'/workforce';
    const admin=['owner','admin'].includes(role), external=role==='client_viewer';
    const reload=()=>ticket===revision && show(tenant,role,campaigns,true);
    let briefs,runs,recipients;
    try {
      [briefs,runs,recipients]=await Promise.all([api(base+'/briefs'),external?[]:api(base+'/runs'),
        admin?api('/api/tenants/'+encodeURIComponent(tenant)+'/recipients'):[]]);
    } catch(e) {
      if(ticket!==revision)return;
      root.inert=false;root.replaceChildren();action(root,'Tải lại brief và tiến độ',reload);return;
    }
    if(ticket!==revision)return;
    root.inert=false;
    const keepOpen=expanded ?? root.querySelector("details")?.open;
    root.replaceChildren();
    if(external&&!briefs.length)return;
    const box=node(root,'details');box.className='panel';box.open=Boolean(keepOpen);
    node(box,'summary',external?'Brief Marketing của bạn':'Điều phối Marketing AI');
    if(admin) {
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
        const goal=field(row,'Mục tiêu','textarea'), audience=field(row,'Khách hàng mục tiêu','textarea');
        const offer=field(row,'Sản phẩm và đề nghị','textarea'), label=field(row,'Tên nguồn','input'), excerpt=field(row,'Trích dẫn từ nguồn','textarea');
        action(row,'Gửi brief',async()=>{
          await api(base+'/briefs/'+b.id+'/submission','PUT',{objective:goal.value,audience:audience.value,offer:offer.value,sources:[{label:label.value,excerpt:excerpt.value}]});await reload();
        });
      } else if (!external && role!=='viewer' && b.submitted && !runs.some(r=>r.brief_id===b.id)) {
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
          if(v.last_error)node(info,'p',v.last_error==='recipient_revoked'?'Đã hủy do thu hồi quyền của người giao brief.':'Lỗi: '+v.last_error);
          v.checkpoints.forEach(p=>{node(info,'h4',labels[p.skill]);node(info,'p',p.output.text);
            node(info,'p','Nguồn: '+p.output.source_ids.map(k=>v.source_registry?.[k]?.label||k).join(', '));
            for(const f of p.quality?.role_qa?.findings||[])node(info,'p',f.field+' · '+f.rule+' · '+f.claim);
            for(const f of p.quality?.claims||[]) {
              node(info,'p',(f.status==='needs_evidence'?'Cần bằng chứng':'Có câu trùng nguồn '+f.matching_ids.join(', '))+' · '+f.claim);
            }
            if(p.quality?.numbers_for_qa.length)node(info,'p','Số liệu cần QA đối chiếu: '+p.quality.numbers_for_qa.join(', '));});
          if(v.deliverable_id)node(info,'p','Mở mục Bàn giao và duyệt nội dung để kiểm tra bộ tài sản.');
          v.approved_assets.forEach(a=>{const link=node(info,'a','Mở bộ tài sản đã duyệt · v'+a.version);link.href='?workspace='+encodeURIComponent(tenant)+'&review='+encodeURIComponent(a.id);});
        });
      }
    }
  }
  return {reset,show,pause(){ revision++; root.inert=true; }};
}
