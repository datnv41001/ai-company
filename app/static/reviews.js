/* This panel receives an authenticated API function from app.js. Keep bearer tokens in memory. */
function createReviewPanel(root, api, notify) {
  let context = null;
  let generation = 0;
  let reload = null;
  const labels = {
    pending:'Chờ khách duyệt', expired:'Đã hết hạn', approved:'Khách đã duyệt', rejected:'Khách từ chối',
    cancelled:'Đã hủy', superseded:'Đã có bản mới', changes_requested:'Khách yêu cầu sửa', comment:'Bình luận',
    draft:'Bản nháp', submitted:'Chờ QA', shared:'Đã bàn giao'
  };
  function el(tag, value, parent) {
    const n = document.createElement(tag);
    if (value !== null) n.textContent = value;
    if (parent) parent.append(n);
    return n;
  }
  function button(parent, label, action) {
    const b = el('button',label,parent);
    b.type = 'button';
    b.addEventListener('click',async () => {
      b.disabled = true;
      try { await action(); } catch (error) { notify(error.message, true); }
      finally { b.disabled = false; }
    });
    return b;
  }
  function field(parent, label, tag, value='') {
    const control = el(tag,null,el('label',label,parent));
    control.value = value;
    return control;
  }
  const url = (ctx,path) => '/api/tenants/'+encodeURIComponent(ctx.tenant)+'/'+path;
  const write = (ctx,path,method,body) => api(url(ctx,path),method,body);
  function setContext(next) {
    generation++;
    context = next;
    root.replaceChildren();
  }
  async function detail(ctx, id, parent) {
    const current = ++generation;
    parent.replaceChildren();
    let item;
    try { item = await api(url(ctx,'reviews/'+encodeURIComponent(id))); }
    catch (error) {
      if (context !== ctx || generation !== current) return;
      el('p','Không mở được bản bàn giao. Hãy kiểm tra đường dẫn và quyền truy cập.',parent);
      button(parent,'Thử lại',()=>detail(ctx,id,parent));
      return;
    }
    if (context !== ctx || generation !== current) return;
    el('h4',item.title+' · Phiên bản '+item.version,parent);
    el('p',labels[item.status]+' · Hạn '+new Date(item.expires_at).toLocaleString('vi-VN'),parent);
    el('pre',item.preview,parent).className='review-preview';
    const proof = el('details',null,parent);
    el('summary','Dấu xác nhận nội dung SHA-256',proof);
    el('code',item.digest,proof);
    const link = el('a','Liên kết bản này',parent);
    const address = new URL(location.pathname,location.origin);
    address.search = new URLSearchParams({workspace:ctx.tenant,review:item.id});
    link.href=address.href;
    el('h4','Lịch sử phản hồi',parent);
    if (!item.history.length) el('p','Chưa có phản hồi.',parent);
    for (const e of item.history) {
      el('p',new Date(e.at).toLocaleString('vi-VN')+' · '+labels[e.kind]+(e.note?' — '+e.note:''),parent);
    }
    if (item.status !== 'pending' || !(item.can_decide || item.can_comment || item.can_cancel)) return;
    const note=field(parent,'Ý kiến của bạn','textarea');
    if (item.can_decide) el('p','Khi từ chối hoặc yêu cầu sửa, ghi lý do cụ thể (ít nhất 5 ký tự).',parent);
    note.maxLength=2000;
    const actions=el('div',null,parent); actions.className='review-buttons';
    // Retrying an identical form after a lost response reuses the original key.
    const keys=new Map();
    for (const [kind,label,allowed] of [['comment','Gửi bình luận',item.can_comment],['approved','Duyệt phiên bản này',item.can_decide],
      ['changes_requested','Yêu cầu sửa',item.can_decide],['rejected','Từ chối',item.can_decide],['cancelled','Hủy yêu cầu',item.can_cancel]]) {
      if (allowed) button(actions,label,async()=>{
        if (['changes_requested','rejected'].includes(kind) && Array.from(note.value.trim()).length < 5) {
          note.focus();
          throw new Error('Vui lòng ghi lý do cụ thể (ít nhất 5 ký tự).');
        }
        const bodyKey=JSON.stringify([kind,note.value]);
        if (!keys.has(bodyKey)) keys.set(bodyKey,crypto.randomUUID());
        await write(ctx,'reviews/'+item.id+'/events','POST',{kind,note:note.value,digest:item.digest,request_key:keys.get(bodyKey)});
        if (context === ctx) await reload(item.id);
      });
    }
  }
  function staff(ctx,panel,docs,campaigns) {
    const box=el('details',null,panel); el('summary','Soạn và bàn giao cho khách',box);
    const pick=field(box,'Bản làm việc','select');
    pick.add(new Option('Tạo bản mới',''));
    docs.forEach(d=>pick.add(new Option(d.title+' · '+(d.status==='approved'?'QA đã duyệt':labels[d.status]||d.status),d.id)));
    const form=el('div',null,box);
    function draw() {
      form.replaceChildren();
      const doc=docs.find(d=>d.id===pick.value);
      const campaign=field(form,'Chiến dịch','select');
      campaigns.forEach(c=>campaign.add(new Option(c.name,c.id)));
      if(doc){campaign.value=doc.campaign_id;campaign.disabled=true;}
      const title=field(form,'Tiêu đề gửi khách','input',doc?.title||'');
      const preview=field(form,'Nội dung khách sẽ xem','textarea',doc?.content?.client_preview||'');
      const update=async(path,method,body)=>{
        await write(ctx,path,method,body);
        if(context===ctx) await reload();
      };
      if(doc?.status==='shared') el('p','Lưu bản sửa sẽ hủy yêu cầu đang chờ của phiên bản đã chia sẻ.',form);
      button(form,doc?'Lưu bản sửa':'Tạo bản nháp',()=>{
        if(!title.value.trim() || !preview.value.trim() || !campaign.value) throw new Error('Chọn chiến dịch, nhập tiêu đề và nội dung.');
        return doc?update('deliverables/'+doc.id+'/draft','PATCH',{title:title.value,client_preview:preview.value})
          :update('deliverables','POST',{title:title.value,campaign_id:campaign.value,content:{client_preview:preview.value}});
      });
      const claims=doc?.content?.qa_claims;
      if(Array.isArray(claims) && claims.length) el('p','Các câu cần đối chiếu từ bản nháp AI ban đầu',form);
      for(const finding of Array.isArray(claims)?claims:[]) {
        if(typeof finding?.claim!=='string' || !Array.isArray(finding.matching_ids)) continue;
        const source=finding.matching_ids.length?'Trùng câu trong nguồn '+finding.matching_ids.join(', '):'Cần bổ sung bằng chứng';
        el('p',source+' · '+finding.claim,form);
      }
      if(!doc)return;
      const path='deliverables/'+doc.id;
      if(doc.status==='draft') button(form,'Gửi QA',()=>update(path+'/submit','POST'));
      if(!['owner','admin'].includes(ctx.role))return;
      if(doc.status==='submitted'){
        const note=field(form,'Ghi chú QA nội bộ','textarea');
        for(const [kind,label] of [['approved','QA duyệt'],['rejected','Trả lại để sửa']])
          button(form,label,()=>update(path+'/review','POST',{decision:kind,note:note.value}));
      }
      if(doc.status==='approved'){
        const deadline=field(form,'Hạn phản hồi (giờ địa phương)','input'); deadline.type='datetime-local';
        button(form,'Chia sẻ phiên bản đã duyệt',()=>{
          if(!deadline.value) throw new Error('Chọn hạn phản hồi.');
          return update(path+'/share','POST',{expires_at:new Date(deadline.value).toISOString()});
        });
      }
    }
    pick.onchange=draw;draw();
  }
  async function load(ctx,docs,campaigns,selected=null) {
    const ticket=++generation;
    root.replaceChildren();
    const heading=el('h3','Bàn giao và duyệt nội dung',root);
    const content=el('div',null,root);
    let rows;
    try {rows=await api(url(ctx,'reviews'),'GET',null,true);} catch(error) {
      if(context!==ctx || generation!==ticket)return;
      el('p','Không tải được danh sách bản bàn giao.',content);
      button(content,'Thử lại',()=>reload(selected));return;
    }
    if(context!==ctx || generation!==ticket)return;
    heading.tabIndex=-1;
    if(['owner','admin','editor'].includes(ctx.role))staff(ctx,content,docs,campaigns);
    const list=el('div',null,content); list.className='review-buttons';
    const body=el('article',null,content); body.setAttribute('aria-live','polite');
    const addRows = items => {
      for (const row of items) button(list,row.title+' · v'+row.version+' · '+labels[row.status],()=>detail(ctx,row.id,body));
    };
    if (!rows.items.length) el('p','Chưa có phiên bản nào được chia sẻ.',list);
    addRows(rows.items);
    let cursor=rows.next;
    if (cursor) {
      const more=button(content,'Xem thêm bản bàn giao',async()=>{
        const page=await api(url(ctx,'reviews?cursor='+encodeURIComponent(cursor)),'GET',null,true);
        if (context!==ctx || !content.isConnected) return;
        addRows(page.items);
        cursor=page.next;
        if (!cursor) more.remove();
      });
    }
    if(selected)await detail(ctx,selected,body);
  }
  return {setContext, show:async(docs,campaigns,refresh)=>{
    const ctx=context;if(!ctx)return;
    reload=refresh;
    const query=new URLSearchParams(location.search);
    await load(ctx,docs,campaigns,ctx.selected || (query.get('workspace')===ctx.tenant?query.get('review'):null));
    ctx.selected=null;
  }, select(id){if(context)context.selected=id;}};
}
