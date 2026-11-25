function createClaimDesk(root, api, notify) {
  const states = {draft:'Nháp', approved:'Đã duyệt', disputed:'Có tranh chấp', withdrawn:'Đã thu hồi', superseded:'Đã thay thế', expired:'Hết hạn', pending_effective:'Chưa có hiệu lực'};
  const kinds = {description:'Mô tả', price:'Giá', availability:'Tình trạng hàng', payment:'Thanh toán', warranty:'Bảo hành', performance:'Hiệu năng', regulated:'Nội dung có quy định chuyên ngành', comparison:'So sánh', unclassified:'Nội dung cần chuyên môn'};
  const options = {retail:'Bán lẻ', wholesale:'Bán sỉ', prepaid:'Trả trước', credit:'Trả sau', standard:'Tiêu chuẩn', extended:'Mở rộng'};
  const units = {piece:'Cái',box:'Hộp','m²':'m²',tonne:'Tấn',kg:'kg',service:'Dịch vụ',visit:'Lượt',machine:'Máy',participant:'Người',subscription_month:'Tháng',subscription_year:'Năm'};
  const axes={buyer:['Nhóm người mua',['retail','wholesale']],payment_type:['Cách thanh toán',['prepaid','credit']],service_level:['Mức dịch vụ',['standard','extended']]};
  let generation = 0, requestNo = 0, scope, ctl, board, data, src, entry, mandates, selectedMandate, pending, busy;
  let claimOffset = 0, sourceOffset = 0, captureChoices, qualificationOffset=0;
  const path = () => `/api/tenants/${scope.tenant}/clients/${scope.client}/brands/${scope.brand}/knowledge`;
  const pointerKey = () => `amc.claim-desk.${scope.actor}.${scope.tenant}.${scope.client}.${scope.brand}`;
  async function fingerprint(value) {
    const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value)));
    return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
  }
  function remember(value) {
    pending=value;
    try {if(value)sessionStorage.setItem(pointerKey(),JSON.stringify(value));else sessionStorage.removeItem(pointerKey());}catch{}
  }
  const field = (tag, label) => { const n=document.createElement(tag); if(label!=null)n.textContent=label; return n; };
  function button(label, callback) {
    const n=field('button',label); n.type='button'; n.onclick=()=>action(callback); return n;
  }
  function box(title) {const node=field('section');node.className='knowledge-body'; node.append(field('h4',title));return node;}
  function input(parent,name,value='', type='text') {
    const l=field('label',name), elem=field(type==='textarea'?'textarea':'input');
    if(type!=='textarea') elem.type=type; elem.value=value ?? ''; l.append(elem);parent.append(l);return elem;
  }
  function select(parent, title, choices, current='') {
    const label=field('label',title),node=field('select'); node.setAttribute('aria-label',title); label.append(node); parent.append(label);
    node.add(new Option('Chọn…','')); choices.forEach(c=>node.add(new Option(c.label,c.id)));
    node.value=current||''; return node;
  }
  function orderFields(parent, original) {
    const base=original||{}, inputs={};
    for(const [key,[title,choices]] of Object.entries(axes)){
      const selected=base[key] || (choices.includes(base.option)?base.option:'');
      inputs[key]=select(parent,title,choices.map(id=>({id,label:options[id]})),selected);
    }
    inputs.unit=select(parent,'Đơn vị áp dụng',Object.entries(units).map(([id,label])=>({id,label})),base.unit);
    inputs.minimum=input(parent,'Số lượng tối thiểu',base.minimum);inputs.maximum=input(parent,'Số lượng tối đa',base.maximum);
    const values=()=>Object.fromEntries(Object.entries(inputs).filter(([,n])=>n.value).map(([k,n])=>[k,n.value]));
    const initial=JSON.stringify(values());
    // Existing v22 source entries may pin the legacy option field. Preserve
    // exact evidence bytes until the user actually changes an order dimension.
    return ()=>JSON.stringify(values())===initial?original:values();
  }
  function applyOrder(assertion,read) {
    if(!read)return;
    const values=read();
    if(values && Object.keys(values).length)assertion.applicability=values;else delete assertion.applicability;
  }
  const decode = err => ({401:'Phiên đăng nhập đã hết hạn.',403:'Bạn chưa có quyền thao tác.',404:'Thông tin này không còn khả dụng.',409:'Bản ghi hoặc điều kiện phê duyệt đã thay đổi. Đối chiếu lại bản mới nhất.',422:'Kiểm tra dữ liệu nhập và phạm vi đã chọn.'}[err.status] || err.message);
  async function action(fn) {const g=generation;try {await fn();}catch(e){if(g===generation && e.name!=='AbortError')notify(decode(e),true);}}
  function reset() {
    ++generation;++requestNo;ctl?.abort();ctl=null;scope=board=data=src=entry=mandates=selectedMandate=pending=null;busy=false;
    claimOffset=sourceOffset=qualificationOffset=0;captureChoices=null;root.replaceChildren();
  }
  async function get(suffix) {
    const g=generation;const result=await api(path()+'/claim-desk'+suffix,'GET',null,false,ctl.signal);
    if(g!==generation) throw new DOMException('Scope changed','AbortError');
    return result;
  }
  async function loadBoard() {
    const seq=++requestNo;
    const result=await get(`?claim_offset=${claimOffset}&source_offset=${sourceOffset}`);
    if(seq!==requestNo)return;
    board=result;
    if(board.can_approve) {const list=await get('/qualifications?offset='+qualificationOffset);if(seq!==requestNo)return;mandates=list;}
    render();
  }
  async function show(context) {
    reset();scope={...context};ctl=new AbortController();
    try {pending=JSON.parse(sessionStorage.getItem(pointerKey()));}catch{}
    const g=generation;
    await action(async()=>{await loadBoard();if(g===generation && pending)await recover();});
  }
  async function recover() {
    try {
      const receipt=await get('/commands/'+encodeURIComponent(pending.key));
      remember(null);
      if(receipt.kind==='claim')await open(receipt.id);
      else if(receipt.kind==='source')await chooseSource(receipt.id);
      notify('Đã tìm thấy kết quả lưu trước đó.');
      return true;
    } catch(error){if(error.status!==404)throw error;return false;}
  }
  async function open(id) {
    const seq=++requestNo;const found=await get('/'+encodeURIComponent(id));if(seq!==requestNo)return;
    data=found;src=entry=selectedMandate=null;
    if(found.evidence) {
      const from=await get('/sources/'+found.evidence.source.id);
      if(seq!==requestNo)return;src=from;entry=src.entries.find(e=>e.locator===found.evidence.locator);
    }
    render();
  }
  async function chooseSource(id) {
    const seq=++requestNo;const from=id?await get('/sources/'+id):null;if(seq!==requestNo)return;
    src=from;entry=null;render();
  }
  async function send(url, body, done) {
    if(busy)return;
    const g=generation;
    busy=true;
    try {
      const signature=await fingerprint([url,body]);
      if(g!==generation)return;
      if(pending && pending.signature!==signature){
        if(await recover())return;
        if(!window.confirm('Yêu cầu trước chưa có kết quả. Tiếp tục với nội dung mới?'))return;
      }
      if(!pending || pending.signature!==signature)remember({signature,key:crypto.randomUUID()});
      const result=await api(path()+url,'POST',{...body,key:pending.key},false,ctl.signal);
      if(g!==generation)return;
      remember(null);await done(result);
    } catch(err) {
      if(g!==generation)return;
      if(err.status && err.status<500)remember(null);
      throw err;
    } finally {if(g===generation)busy=false;}
  }
  function describe(statement, names) {
    const place=statement.placement,a=statement.applicability,price=statement.price;
    const scopeNames=names || place;
    const pieces=[scopeNames.product,scopeNames.variant,scopeNames.market,place.region,place.locale,place.channel].filter(Boolean);
    if(a)pieces.push([...new Set([a.option,a.buyer,a.payment_type,a.service_level].filter(Boolean).map(id=>options[id]||id)),
      a.minimum&&'từ '+a.minimum,a.maximum&&'đến '+a.maximum,units[a.unit] || a.unit].filter(Boolean).join(' · '));
    if(price) {
      const major=price.amount_minor/(['JPY','VND'].includes(price.currency)?1:100);
      const display=new Intl.NumberFormat('vi-VN',{style:'currency',currency:price.currency}).format(major);
      const tax={included:'đã gồm thuế',excluded:'chưa gồm thuế',unknown:'chưa rõ thuế'};
      pieces.push(`${display} / ${price.basis_quantity} ${units[price.unit] || price.unit}, ${tax[price.tax]}, số lượng ${statement.quantity}, tối thiểu ${price.moq}, bậc từ ${price.tier_min}${price.tier_max?' đến '+price.tier_max:''}. ${price.conditions.join(', ')}`);
    }
    return pieces.join(' · ');
  }
  function pager(target, kind) {
    const offset=kind==='claim'?claimOffset:sourceOffset, more=kind==='claim'?board.more_claims:board.more_sources;
    const change=delta=>{if(kind==='claim')claimOffset+=delta;else sourceOffset+=delta;return loadBoard();};
    if(offset)target.append(button('Trang trước',()=>change(-20))); if(more)target.append(button('Trang sau',()=>change(20)));
  }
  function transitions(target, row, isClaim) {
    if(!board.can_approve)return;
    const choices={draft:['approved','disputed','withdrawn'],approved:['disputed','withdrawn'],disputed:['withdrawn'],superseded:['withdrawn']}[row.state] || [];
    if(!choices.length)return;
    const sel=select(target,'Quyết định',choices.map(id=>({id,label:states[id]})));
    let mandate;
    if(isClaim && data.required_qualification) {
      const category=data.required_qualification;
      target.append(field('p','Cần một người duyệt độc lập có ủy quyền về '+kinds[category]+'.'));
      mandate=select(target,'Ủy quyền của tôi',(mandates?.items||[]).filter(m=>m.mine&&m.category===category&&m.state==='approved'));
    }
    const note=input(target,'Lý do quyết định','','textarea');
    target.append(button('Ghi quyết định',()=>{
      if(!sel.value || !note.value.trim())throw Error('Hãy chọn quyết định và nhập lý do.');
      const body={expected_digest:row.digest,expected_sequence:row.sequence,state:sel.value,reason:note.value.trim()};
      if(sel.value==='approved' && mandate){if(!mandate.value)throw Error('Cần chọn ủy quyền còn hiệu lực.');body.qualification_revision=mandate.value;}
      return send('/revisions/'+row.id+'/events',body,async()=>{await loadBoard();if(data)await open(data.claim.id);else if(src)await chooseSource(src.id);notify('Đã ghi quyết định.');});
    }));
  }
  function qualification() {
    if(!board.can_approve)return;
    const section=field('details');section.append(field('summary','Chuyên môn và ủy quyền duyệt'));
    const own=mandates.reviewers.find(r=>r.self);
    if(own)section.append(field('p','Mã đối chiếu của bạn trong danh sách người duyệt: '+own.id.slice(-6)));
    const list=select(section,'Hồ sơ ủy quyền',mandates.items,selectedMandate);
    if(qualificationOffset)section.append(button('Ủy quyền trang trước',()=>{qualificationOffset-=30;return loadBoard();}));
    if(mandates.more)section.append(button('Ủy quyền trang sau',()=>{qualificationOffset+=30;return loadBoard();}));
    list.onchange=()=>{selectedMandate=list.value;render();};
    const record=mandates.items.find(m=>m.id===selectedMandate);
    if(record){section.append(field('p',`${kinds[record.category]} · ${record.basis} · ${states[record.state]} · ${record.valid_until}`));transitions(section,record,false);}
    const who=select(section,'Người nhận ủy quyền',mandates.reviewers.filter(r=>!r.self).map(r=>({id:r.id,label:r.label || ((r.role==='owner'?'Chủ workspace':'Quản trị viên')+' · '+r.id.slice(-6))})));
    const category=select(section,'Phạm vi chuyên môn',['performance','comparison','regulated','unclassified'].map(id=>({id,label:kinds[id]})));
    const reason=input(section,'Căn cứ xác nhận chuyên môn','', 'textarea'), date=input(section,'Có hiệu lực đến','','datetime-local');
    section.append(button('Lập hồ sơ ủy quyền',()=>{
      if(!who.value || !category.value || !reason.value.trim() || !date.value)throw Error('Hãy điền chuyên môn, người nhận, căn cứ và thời hạn.');
      return send('/revisions',{subject:'review-'+who.value.replaceAll('-','').slice(0,12)+'-'+category.value+'-'+date.value.replace(/\D/g,''),kind:'qualification',visibility:'restricted',expected_revision:0,
        data:{approver_id:who.value,category:category.value,basis:reason.value.trim(),valid_until:new Date(date.value).toISOString()}},async r=>{selectedMandate=r.id;await loadBoard();notify('Hồ sơ đang chờ chủ workspace duyệt.');});
    }));
    if(selectedMandate)section.open=true;root.append(section);
  }
  function editor() {
    const panel=box(data?'Đối chiếu với nguồn':'Soạn từ chứng cứ');
    const choices=board.sources.map(s=>({id:s.id,label:`${s.label} · ${states[s.state]} · bản ${s.revision}`}));
    if(src && !choices.some(c=>c.id===src.id))choices.unshift({id:src.id,label:src.document});
    const source=select(panel,'Nguồn chứng cứ',choices,src?.id);source.onchange=()=>action(()=>chooseSource(source.value));pager(panel,'source');
    if(src) {
      panel.append(field('p',`${src.publisher} · ${src.document} · hiệu lực đến ${src.valid_until}`));
      const pick=select(panel,'Vị trí trong nguồn',src.entries.map(e=>({id:e.locator,label:e.locator})),entry?.locator);
      pick.onchange=()=>{entry=src.entries.find(r=>r.locator===pick.value);render();};
      panel.append(field('p',`Ảnh hưởng của nguồn đang thấy: ${src.impact.more?'ít nhất ':''}${src.impact.snapshots.length} bản chụp.`));
      const log=field('details');log.append(field('summary','Lịch sử nguồn'));
      src.events.forEach(e=>log.append(field('p',states[e.state]+' · '+new Date(e.effective_at).toLocaleString()+(e.reason?' · '+e.reason:''))));
      panel.append(log);
      if(board.can_approve)transitions(panel,src,false);
    }
    if(entry) {
      const both=field('div');both.className='knowledge-grid';panel.append(both);
      const left=box('Trích dẫn gốc');left.append(field('blockquote',entry.excerpt),field('p',entry.assertion.wording),
        field('p',entry.assertion.qualifiers.join(' · ')),field('p',describe(entry.assertion,entry.names)));both.append(left);
      if(board.can_edit) {
        const right=box('Nội dung đề xuất');both.append(right);
        const a=entry.assertion, wording=input(right,'Câu dùng cho Marketing',a.wording,'textarea');
        const qualifiers=input(right,'Điều kiện kèm theo, mỗi dòng một điều kiện',a.qualifiers.join('\n'),'textarea');
        const region=input(right,'Khu vực',a.placement.region),channel=input(right,'Kênh',a.placement.channel), locale=input(right,'Ngôn ngữ',a.placement.locale);
        const order=['availability','payment','warranty'].includes(a.category)?orderFields(right,a.applicability):null;
        const from=input(right,'Bắt đầu áp dụng (giờ địa phương)',localDate(data?.valid_from),'datetime-local');
        const until=input(right,'Kết thúc áp dụng (giờ địa phương)',localDate(data?.valid_until),'datetime-local');
        const save=button(data?'Lưu phiên bản mới':'Lưu bản nháp',()=>{
          const assertion=structuredClone(a);assertion.wording=wording.value.trim();assertion.qualifiers=qualifiers.value.split('\n').map(s=>s.trim()).filter(Boolean);
          Object.assign(assertion.placement,{region:region.value.trim(),channel:channel.value.trim(),locale:locale.value.trim()});
          applyOrder(assertion,order);
          return send('/claim-desk/drafts',{subject:data?.claim.subject || null,expected_revision:data?.claim.revision || 0,source_revision:src.id,locator:entry.locator,assertion,
            valid_from:from.value?new Date(from.value).toISOString():null,valid_until:until.value?new Date(until.value).toISOString():null},async r=>{await loadBoard();await open(r.id);notify('Đã lưu bản nháp để duyệt.');});
        });
        right.append(save);
      }
    }
    if(board.can_edit){
      panel.append(button(captureChoices?'Đóng mục ghi nguồn':'Ghi nguồn mới',async()=>{
        captureChoices=captureChoices?null:await get('/placements');render();
      }));
      if(captureChoices)captureSource(panel);
    }
    root.append(panel);
  }
  function captureSource(panel){
    const form=box('Ghi chứng cứ từ tài liệu');panel.append(form);
    const publisher=input(form,'Đơn vị phát hành'),documentName=input(form,'Tên tài liệu'),locator=input(form,'Vị trí, trang hoặc dòng'),
      excerpt=input(form,'Trích nguyên văn','','textarea'),expiry=input(form,'Nguồn có hiệu lực đến','','datetime-local');
    const visibility=select(form,'Ai được đọc chứng cứ',[{id:'internal',label:'Nhân sự dự án'},...(board.can_approve?[{id:'restricted',label:'Chỉ người duyệt'}]:[])],'internal');
    const original=entry?.assertion;
    const types=original?[original.category]:['description','performance','regulated','comparison'];
    const category=select(form,'Loại nhận định',types.map(id=>({id,label:kinds[id]})),types[0]);
    const product=select(form,'Sản phẩm hoặc dịch vụ',captureChoices.products,original?.placement.product),
      variant=select(form,'Biến thể',captureChoices.variants,original?.placement.variant),
      market=select(form,'Thị trường',captureChoices.markets,original?.placement.market);
    if(captureChoices.products_more || captureChoices.variants_more || captureChoices.markets_more){
      const match=input(form,'Tìm tên sản phẩm hoặc thị trường');
      form.append(button('Lọc danh mục',async()=>{captureChoices=await get('/placements?term='+encodeURIComponent(match.value));render();}));
    }
    const language=input(form,'Ngôn ngữ của chứng cứ',original?.placement.locale||'vi-VN'),region=input(form,'Địa bàn của chứng cứ',original?.placement.region),
      channel=input(form,'Kênh áp dụng',original?.placement.channel||'web'),wording=input(form,'Nội dung được chứng minh',original?.wording,'textarea'),
      qualifiers=input(form,'Điều kiện trong chứng cứ, mỗi dòng một điều kiện',(original?.qualifiers||[]).join('\n'),'textarea');
    const order=original && ['availability','payment','warranty'].includes(original.category)?orderFields(form,original.applicability):null;
    form.append(button('Lưu nguồn chờ duyệt',async()=>{
      if(!publisher.value.trim()||!documentName.value.trim()||!locator.value.trim()||!expiry.value||!excerpt.value.trim()||!product.value||!market.value||!wording.value.trim()||!region.value.trim())throw Error('Cần tài liệu, trích dẫn, thời hạn, nội dung và phạm vi áp dụng.');
      const assertion=original?structuredClone(original):{};
      Object.assign(assertion,{category:category.value,wording:wording.value.trim(),qualifiers:qualifiers.value.split('\n').map(v=>v.trim()).filter(Boolean),
        placement:{product:product.value,variant:variant.value||null,market:market.value,locale:language.value.trim(),region:region.value.trim(),channel:channel.value.trim()}});
      applyOrder(assertion,order);
      const description={publisher:publisher.value.trim(),document:documentName.value.trim(),valid_until:new Date(expiry.value).toISOString(),entries:[{locator:locator.value.trim(),excerpt:excerpt.value.trim(),assertion}]};
      const g=generation;
      const subject='source-'+(await fingerprint(description)).slice(0,36);
      if(g!==generation)return;
      return send('/revisions',{subject,kind:'source',expected_revision:0,visibility:visibility.value,data:description},
        async r=>{captureChoices=null;await loadBoard();await chooseSource(r.id);notify('Đã lưu nguồn ở trạng thái chờ duyệt.');});
    }));
  }
  function localDate(date){if(!date)return '';const t=new Date(date);return new Date(t.getTime()-t.getTimezoneOffset()*60000).toISOString().slice(0,16);}
  function correctionQueue(container){
    const result=field('div');container.append(button('Duyệt đơn vị bán',()=>load(0)),result);
    async function load(offset){
      const g=generation;
      const base='/api/tenants/'+scope.tenant+'/clients/'+scope.client+'/brands/'+scope.brand+'/business-workspace/marketing/clarifications';
      const page=await api(base+'?offset='+offset,'GET',null,false,ctl.signal);
      if(g!==generation||!result.isConnected)return;
      if(!offset)result.replaceChildren();
      for(const issue of page.items){
        const p=issue.proposal,entry=box(issue.product);
        const t=issue.terms, scale=['VND','JPY'].includes(t.currency)?1:100;
        const money=new Intl.NumberFormat('vi-VN',{style:'currency',currency:t.currency}).format(t.amount_minor/scale);
        entry.append(field('p',money+' / '+t.basis_quantity+' '+issue.choices[p.unit]+'. Tối thiểu '+t.moq+
          ', bậc '+t.tier_min+(t.tier_max?'–'+t.tier_max:' trở lên')+'. '+
          ({included:'Đã gồm thuế',excluded:'Chưa gồm thuế',unknown:'Chưa rõ thuế'}[t.tax])+'. '+[...new Set([...t.conditions,...issue.qualifiers])].join(' ')),
          field('p',issue.document+' · '+issue.locator+' · '+issue.excerpt));
        if(p.required_qualification && (p.own||!p.qualifications.length)){
          entry.append(field('p','Chờ người có ủy quyền độc lập với tác giả.'));
        }else{
          const mandate=p.required_qualification?select(entry,'Ủy quyền cho nhận định',p.qualifications.map(id=>({id,label:id.slice(0,8)})),p.qualifications[0]):null;
          const reason=input(entry,'Lý do duyệt đơn vị bán');
          let key=crypto.randomUUID();
          entry.addEventListener('input',()=>{key=crypto.randomUUID();});
          const approve=button('Xác nhận giá và đơn vị',async()=>{
            if(!reason.value.trim())throw Error('Ghi căn cứ duyệt.');
            approve.disabled=true;
            try{
              await api(base+'/approve','POST',{key,proposal:p.id,reason:reason.value.trim(),qualification_revision:mandate?.value||null},false,ctl.signal);
              if(g===generation)await load(0);
            }finally{approve.disabled=false;}
          });
          entry.append(approve);
        }
        result.append(entry);
      }
      if(page.next_offset!==null){
        const more=button('Xem tiếp đề xuất',async()=>{more.remove();await load(page.next_offset);});result.append(more);
      }else if(!result.childElementCount)result.append(field('p','Không có đề xuất đơn vị đang chờ duyệt.'));
    }
  }
  function render(){
    root.replaceChildren();root.append(field('h3','Nguồn và nhận định Marketing'));
    const index=box('Nhận định theo thương hiệu');
    const choose=select(index,'Chọn nhận định',board.claims.map(r=>({id:r.id,label:`${r.label} · bản ${r.revision} · ${states[r.state]}`})),data?.claim.id);
    choose.onchange=()=>action(()=>choose.value?open(choose.value):(data=src=entry=null,render()));
    if(board.can_edit)index.append(button('Soạn nhận định mới',()=>{++requestNo;data=src=entry=null;render();}));
    index.append(button('Kiểm tra lại hiệu lực',revalidate));pager(index,'claim');root.append(index);
    if(board.can_approve)correctionQueue(index);
    if(data) {
      const projection=box('Câu chữ công khai còn hiệu lực');
      if(data.public_wording){const p=data.public_wording;projection.append(field('p',p.wording),field('p',p.qualifiers.join(' · ')),field('p',describe(p)));}
      else projection.append(field('p','Chưa đủ điều kiện dùng câu này cho Marketing.'));
      if(!data.evidence)projection.append(field('p','Chi tiết bằng chứng nằm ngoài phạm vi hiển thị.'));
      root.append(projection);
    }
    if(!data || data.evidence)editor();
    if(data) {
      if(board.can_approve && data.evidence?.binding.state==='draft'){
        const link=box('Xác nhận đối chiếu nguồn');transitions(link,data.evidence.binding,false);root.append(link);}
      const review=box('Duyệt nhận định');review.append(field('p',`Bản ${data.claim.revision} · ${states[data.claim.state]}.`));
      review.append(field('p',`Ảnh hưởng đang thấy: ${data.impact.more?'ít nhất ':''}${data.impact.snapshots.length} bản chụp.`));
      transitions(review,data.claim,true);root.append(review);
      const history=box('Lịch sử');data.revisions.forEach(row=>history.append(button('Xem bản '+row.revision,()=>open(row.id))));
      const entries=field('ul');data.events.forEach(e=>entries.append(field('li',`${states[e.state]} · ${new Date(e.effective_at).toLocaleString()}${e.reason?' · '+e.reason:''}`)));history.append(entries);root.append(history);
    }
    qualification();
  }
  async function revalidate() {
    if(!scope || !board || busy)return;
    const g=generation,id=data?.claim.id;
    try {
      const current=await get(`?claim_offset=${claimOffset}&source_offset=${sourceOffset}`);
      if(current.can_approve!==board.can_approve || current.can_edit!==board.can_edit){
        const context={...scope};await show(context);return;
      }
      if(id){
        const currentDetail=await get('/'+id);
        if(!data || data.claim.id!==id)return;
        if(JSON.stringify(data)!==JSON.stringify(currentDetail)){data=currentDetail;src=entry=null;await open(id);}
      }
    } catch(error) {if(g===generation){reset();notify('Hãy mở lại mục sau khi kiểm tra quyền và kết nối.',true);}}
  }
  return {show,reset,revalidate};
}
