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
      campaign.onchange=fillRecipients;fillRecipients();
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
        const select=field(row,'Chuyên môn bổ sung','select');select.multiple=true;
        ['seo','creative','ads','analytics'].forEach(s=>select.add(new Option(labels[s],s)));
        const budget=field(row,'Ngân sách model (USD, 0 cho local)','input');budget.type='number';budget.step='0.01';budget.min=0;budget.max=1;budget.value=0;
        action(row,'Giao việc cho AI Director',async()=>{await api(base+'/briefs/'+b.id+'/run','POST',{
          extra_skills:Array.from(select.selectedOptions,o=>o.value),budget_microusd:Math.round(Number(budget.value)*1000000)});await reload();});
      }
    }
    if(!external) {
      action(box,'Cập nhật tiến độ',reload);
      for(const r of runs) {
        const row=node(box,'div');node(row,'h4',r.title+' · '+(states[r.state]||r.state));
        node(row,'p',r.done+'/'+r.skills.length+' bước · '+r.skills.map(s=>labels[s]).join(' → '));
        const info=node(row,'div');action(row,'Xem kết quả và chi phí',async()=>{
          const v=await api(base+'/runs/'+r.id);if(ticket!==revision)return;
          info.replaceChildren();node(info,'p',v.journal.length+' lượt xử lý · Chi phí đã tính hoặc giữ chỗ: '+(v.reserved_microusd/1000000).toFixed(6)+' USD');
          if(v.last_error)node(info,'p','Lỗi: '+v.last_error);
          v.checkpoints.forEach(p=>{node(info,'h4',labels[p.skill]);node(info,'p',p.output.text);
            node(info,'p','Nguồn: '+p.output.source_ids.map(k=>v.source_registry?.[k]?.label||k).join(', '));
            if(p.quality?.numbers_for_qa.length)node(info,'p','Số liệu cần QA đối chiếu: '+p.quality.numbers_for_qa.join(', '));});
          if(v.deliverable_id)node(info,'p','Mở mục Bàn giao và duyệt nội dung để kiểm tra bộ tài sản.');
          v.approved_assets.forEach(a=>{const link=node(info,'a','Mở bộ tài sản đã duyệt · v'+a.version);link.href='?workspace='+encodeURIComponent(tenant)+'&review='+encodeURIComponent(a.id);});
        });
      }
    }
  }
  return {reset,show,pause(){ revision++; root.inert=true; }};
}
