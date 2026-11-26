/* All values are rendered as text. Only a deliberate edit/save changes a working revision. */
const studioLabels = {
  research:'Nghiên cứu người mua',strategy:'Chiến lược',measurement:'Kế hoạch đo lường',copy:'Nội dung trang',seo:'SEO',
  buyer_problem:'Vấn đề của người mua',research_question:'Câu hỏi nghiên cứu',evidence:'Dữ kiện và điều kiện',
  hypothesis:'Giả thuyết cần kiểm chứng',positioning:'Định vị',channel_choice:'Kênh đề xuất',rationale:'Lý do lựa chọn',
  execution:'Cách triển khai',test_hypothesis:'Thử nghiệm',measurable_action:'Sự kiện cần đo',measurement_method:'Cách đo',
  headline:'Tiêu đề',value_proposition:'Giá trị cho người mua',benefit:'Lợi ích có căn cứ',commercial_terms:'Điều kiện thương mại',
  call_to_action:'Hành động mong muốn',page_title:'Tiêu đề SEO',meta_description:'Mô tả tìm kiếm',search_intent:'Ý định tìm kiếm',
  client_strategy:'Chiến lược giao khách',client_measurement:'Đo lường giao khách',target:'Đối tượng',decision:'Lựa chọn chiến lược',
  activation:'Triển khai trên kênh',next_decision:'Quyết định tiếp theo',conversion:'Hành động của người mua',method:'Phương pháp đo'
};
let studioHintSequence=0;
function mountMarketingStudio(host,api,path,role,afterSave) {
  const add=(p,tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;p.append(e);return e;};
  const panel=add(host,'details');panel.className='marketing-studio';
  add(panel,'summary','Biên tập tài liệu Marketing');
  const body=add(panel,'div');
  const states={missing:'Thiếu nội dung',repetition:'Nội dung bị lặp, cần biên tập lại',entity_only:'Cần diễn giải ý nghĩa, hiện chỉ có tên hoặc đối tượng trong brief',placeholder:'Cần thay nội dung hướng dẫn',
    buyer_action:'Chưa khớp hành động đã giao',private_context:'Cần bỏ nội dung chỉ dùng nội bộ khỏi bản giao khách',missing_declaration:'Thiếu công bố hoặc điều kiện đã duyệt',relevance:'Cần liên hệ rõ hơn với sản phẩm được giao',
    contradiction:'Mâu thuẫn cần sửa',unresolved:'Cần xác minh',needs_correction:'Cần đối chiếu cách viết',reviewed:'Đã xác minh',verified:'Khớp nguồn',editorial:'Nội dung biên tập',
    missing_qualifier:'Thiếu điều kiện áp dụng',unsupported_format:'Cách trình bày chưa đối chiếu được',unsupported_assertion:'Chưa có căn cứ cho nhận định này',
    known_contradiction:'Mâu thuẫn với nguồn hoặc quy tắc đã duyệt',semantic_interpretation:'Cần người có chuyên môn xác minh ý nghĩa'};
  let view,group,draft,dirty=false,openRequest=0;
  let edition=false;
  let journeyIndex='', dismissed=new Set();
  const use=()=>body.isConnected && panel.open;
  function button(p,title,fn) {
    const b=add(p,'button',title);b.type='button';
    b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){if(use())note(e.message);}finally{b.disabled=false;}};
    return b;
  }
  function note(text){const e=body.querySelector('[role=status]');if(e)e.textContent=text;}
  function setDirty(value){
    dirty=value;host.dataset.studioDirty=String(value);
    host.dispatchEvent(new Event('studiochange'));
  }
  function install(value){
    if(view?.revision!==value.revision){journeyIndex='';dismissed.clear();}
    view=value;draft=structuredClone(view.groups);setDirty(false);
    edition=Boolean(view.delivery_version);
    if(!draft[group])group=Object.keys(draft)[0];
    draw();
  }
  function draw(){
    body.replaceChildren();
    const status=add(body,'p',view.mode==='proposal'?'Bản đề xuất · chờ biên tập và lưu':('Bản làm việc · lần lưu '+view.revision));
    status.setAttribute('role','status');
    const spec=view.customer_edition;
    const name=k=>studioLabels[k]||spec.labels[k]||k;
    const count=Object.keys(view.approvals).length;
    add(body,'p',count+'/'+Object.keys(draft).length+' phần đã được duyệt ở lần lưu '+view.revision+'.');
    if(!edition){
      button(body,'Soạn bộ tài liệu giao khách',()=>{
        Object.assign(draft,structuredClone(spec.groups));edition=true;setDirty(true);
        group=Object.keys(spec.fields)[0];draw();
      });
    }
    const nav=add(body,'div');nav.className='studio-nav';nav.setAttribute('aria-label','Phần tài liệu');
    for(const id of Object.keys(draft)){
      const b=button(nav,name(id),()=>{group=id;draw();});
      if(id!==group)b.className='secondary';
      b.setAttribute('aria-pressed',String(id===group));
    }
    const layout=add(body,'div');layout.className='studio-layout';
    const edit=add(layout,'section');edit.setAttribute('aria-label',name(group));
    add(edit,'h4',name(group));
    const journeys=view.buyer_journeys;
    if(journeys?.eligible.length){
      const selector=add(edit,'label','Ngành và loại sản phẩm áp dụng cho đề xuất');
      const choose=add(selector,'select');choose.add(new Option('Chọn sau khi đối chiếu brief',''));
      journeys.eligible.forEach((v,i)=>choose.add(new Option(v.industry+' · '+v.product_type+' · '+v.unit,String(i))));
      choose.add(new Option('Ngành hoặc loại sản phẩm khác','other'));
      choose.value=journeyIndex;choose.onchange=()=>{journeyIndex=choose.value;draw();};
      if(journeyIndex==='other')add(edit,'small','Dùng quy trình chung cho tổ hợp này. Có thể bổ sung thông tin từ brief trước khi chọn lại.');
    }else if(journeys){
      add(edit,'small','Dùng quy trình chung. Xác nhận ngành, loại sản phẩm, kênh và đơn vị bán trước khi chọn playbook chuyên ngành.');
    }
    if(edition)add(edit,'p',Object.hasOwn(spec.fields,group)?'Thuộc bộ tài liệu giao khách.':'Chỉ dành cho đội ngũ nội bộ.');
    const state=add(edit,'p',view.approvals[group]?'Đã duyệt phần này':'Chờ duyệt độc lập');
    state.className='studio-decision';state.dataset.signed=String(Boolean(view.approvals[group]));
    for(const [key,value] of Object.entries(draft[group])){
      const label=add(edit,'label',name(key));
      const input=add(label,'textarea');input.value=value;input.rows=key==='commercial_terms'||key==='evidence'?4:2;
      input.maxLength=['commercial_terms','evidence'].includes(key)?30000:5000;
      input.dataset.field=key;
      input.oninput=()=>{draft[group][key]=input.value;setDirty(true);note('Có thay đổi chưa lưu · QA áp dụng cho bản đã lưu.');};
      const issues=view.quality_issues.filter(i=>i.group===group && i.field===key).map(i=>states[i.reason]);
      const evidence=view.findings.filter(i=>i.field==='studio.'+group+'.'+key);
      const ids=[];
      for(const item of new Set([...issues,...evidence.map(i=>states[i.outcome==='reviewed'?'reviewed':i.diagnostic]||states[i.outcome])])){
        if(!item)continue;
        const finding=add(edit,'small',item);finding.id='studio-finding-'+(++studioHintSequence);ids.push(finding.id);
      }
      if(ids.length)input.setAttribute('aria-describedby',ids.join(' '));
      const sourceHandles=[...new Set(evidence.flatMap(i=>i.handles||[]))];
      const refs=view.references.filter(r=>sourceHandles.includes(r.handle));
      if(refs.length){
        const refsPanel=add(edit,'details');add(refsPanel,'summary','Nguồn của trường này ('+refs.length+')');
        for(const ref of refs){add(refsPanel,'strong',ref.handle);add(refsPanel,'p',ref.text);}
      }
      const suggestion=view.suggestions[group]?.[key];
      const selected=journeys?.eligible[journeyIndex], field=group+'.'+key, offer=selected?.fields[field];
      if(offer && offer.text!==value && !dismissed.has(journeyIndex+field)){
        const box=add(edit,'details');add(box,'summary','So sánh đề xuất theo hành trình mua');
        add(box,'strong','Nội dung hiện tại');const original=add(box,'p',input.value);
        box.ontoggle=()=>{if(box.open)original.textContent=input.value;};
        add(box,'strong',offer.kind==='hypothesis'?'Giả thuyết đề xuất':'Đề xuất biên tập');
        add(box,'p',offer.text);add(box,'p',selected.reason);
        add(box,'small',journeys.version+' · '+journeys.channel+' · '+selected.unit);
        for(const ref of view.references.filter(r=>journeys.source_handles.includes(r.handle)))add(box,'p',ref.handle+' · '+ref.text);
        button(box,'Dùng và biên tập',()=>{input.value=offer.text;input.dispatchEvent(new Event('input'));box.open=false;input.focus();});
        button(box,'Bỏ qua đề xuất',()=>{dismissed.add(journeyIndex+field);box.remove();input.focus();});
      }
      if(suggestion && suggestion!==value){
        const proposal=add(edit,'details');add(proposal,'summary','Xem đề xuất từ brief đã ghim');
        add(proposal,'p',suggestion);
        button(proposal,'Dùng đề xuất cho trường này',()=>{
          input.value=suggestion;input.dispatchEvent(new Event('input'));proposal.open=false;input.focus();
        });
      }
    }
    const side=add(layout,'aside');side.setAttribute('aria-label','Nguồn được duyệt');add(side,'h4','Nguồn được duyệt');
    for(const src of view.references){add(side,'strong',src.handle);add(side,'p',src.text);}
    const pending=view.findings.filter(i=>i.field.startsWith('studio.') && !['verified','reviewed','editorial'].includes(i.outcome));
    const qa=add(side,'details');add(qa,'summary','QA của bản đã lưu');
    const problems=new Map();
    for(const i of view.quality_issues)problems.set(i.group+'.'+i.field,states[i.reason]||'Cần sửa nội dung');
    for(const i of pending)problems.set(i.field.slice(7),states[i.diagnostic]||states[i.outcome]||'Cần xác minh');
    if(!problems.size)add(qa,'p',view.mode==='saved'?'Chưa có trường cần sửa trong kết quả hiện tại.':'Lưu nội dung để kiểm tra bằng chứng.');
    for(const [field,reason] of problems){
      const [g,k]=field.split('.');
      button(qa,name(g)+' · '+name(k)+' — '+reason,()=>{group=g;draw();editField(k);});
    }
    function editField(key){const e=Array.from(body.querySelectorAll('textarea')).find(x=>x.dataset.field===key);if(e)e.focus();}
    const publicView=add(side,'details');add(publicView,'summary','Bản xem trước dành cho khách');
    if(edition){
      const title=add(publicView,'h5');const content=add(publicView,'div');content.className='studio-edition-preview';
      const updatePreview=()=>{
        title.textContent=draft.copy?.headline||spec.title;
        content.replaceChildren();
        for(const [g,fields] of Object.entries(spec.fields)){
          const section=add(content,'section');add(section,'h6',spec.labels[g]);
          const list=add(section,'dl');
          for(const k of fields){add(list,'dt',spec.labels[k]);add(list,'dd',draft[g][k]||'—');}
        }
      };
      publicView.ontoggle=updatePreview;edit.addEventListener('input',updatePreview);updatePreview();
    }else{add(publicView,'h5',view.preview.title);add(publicView,'p',view.preview.body);}
    const history=add(side,'details');add(history,'summary','Lịch sử tài liệu ('+view.history.length+')');
    for(const entry of view.history){const row=add(history,'details');add(row,'summary','Lần lưu '+entry.revision);
      const previous=view.history.find(item=>item.revision<entry.revision);
      for(const [key,value] of Object.entries(entry.groups[group]||{})){
        add(row,'strong',name(key));const before=previous?.groups[group]?.[key];
        if(before!==undefined && before!==value){add(row,'small','Trước đó');add(row,'del',before);add(row,'small','Ở lần lưu này');}
        add(row,'p',value);
      }}
    const trace=add(side,'details');add(trace,'summary','Thông tin kiểm toán');add(trace,'p',view.version);add(trace,'code',view.asset_digests[group]);
    button(edit,'Lưu bản biên tập',async()=>{
      const v=await api(path,'PATCH',{expected_revision:view.revision,groups:draft,...(edition?{delivery_version:spec.version}:{})});
      if(use()){install(v);if(afterSave)afterSave(v);}
    });
    if(['admin','owner'].includes(role) && view.status==='submitted' && !view.approvals[group]){
      const rationale=add(edit,'label','Nhận xét về chất lượng và mức phù hợp');const reason=add(rationale,'textarea');reason.maxLength=500;
      button(edit,'Duyệt riêng phần '+name(group),async()=>{
        if(dirty)throw new Error('Hãy lưu các thay đổi trước khi duyệt.');
        const v=await api(path+'/approvals','POST',{expected_revision:view.revision,expected_asset_digest:view.asset_digests[group],group,note:reason.value});
        if(use())install(v);
      });
    }
    if(dirty)note('Có thay đổi chưa lưu');
  }
  panel.addEventListener('toggle',async()=>{
    const ticket=++openRequest;
    if(!panel.open || view)return;
    body.textContent='Đang tải tài liệu…';
    try{const v=await api(path);if(use() && openRequest===ticket)install(v);}
    catch(e){if(use() && openRequest===ticket)body.textContent=e.message;}
  });
}
