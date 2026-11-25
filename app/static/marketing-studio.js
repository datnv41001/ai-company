/* All values are rendered as text. Only a deliberate edit/save changes a working revision. */
const studioLabels = {
  research:'Nghiên cứu người mua',strategy:'Chiến lược',measurement:'Kế hoạch đo lường',copy:'Nội dung trang',seo:'SEO',
  buyer_problem:'Vấn đề của người mua',research_question:'Câu hỏi nghiên cứu',evidence:'Dữ kiện và điều kiện',
  hypothesis:'Giả thuyết cần kiểm chứng',positioning:'Định vị',channel_choice:'Kênh đề xuất',rationale:'Lý do lựa chọn',
  execution:'Cách triển khai',test_hypothesis:'Thử nghiệm',measurable_action:'Sự kiện cần đo',measurement_method:'Cách đo',
  headline:'Tiêu đề',value_proposition:'Giá trị cho người mua',benefit:'Lợi ích có căn cứ',commercial_terms:'Điều kiện thương mại',
  call_to_action:'Hành động mong muốn',page_title:'Tiêu đề SEO',meta_description:'Mô tả tìm kiếm',search_intent:'Ý định tìm kiếm'
};
let studioHintSequence=0;
function mountMarketingStudio(host,api,path,role,afterSave) {
  const add=(p,tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;p.append(e);return e;};
  const panel=add(host,'details');panel.className='marketing-studio';
  add(panel,'summary','Biên tập tài liệu Marketing');
  const body=add(panel,'div');
  const states={missing:'Thiếu nội dung',repetition:'Trùng nội dung ở trường khác',placeholder:'Cần thay nội dung hướng dẫn',
    buyer_action:'Chưa khớp hành động đã giao',missing_declaration:'Thiếu công bố hoặc điều kiện đã duyệt',relevance:'Cần liên hệ rõ hơn với sản phẩm được giao',
    contradiction:'Mâu thuẫn cần sửa',unresolved:'Cần xác minh',needs_correction:'Cần đối chiếu cách viết',reviewed:'Đã xác minh',verified:'Khớp nguồn',editorial:'Nội dung biên tập',
    missing_qualifier:'Thiếu điều kiện áp dụng',unsupported_format:'Cách trình bày chưa đối chiếu được',unsupported_assertion:'Chưa có căn cứ cho nhận định này',
    known_contradiction:'Mâu thuẫn với nguồn hoặc quy tắc đã duyệt',semantic_interpretation:'Cần người có chuyên môn xác minh ý nghĩa'};
  let view,group,draft,dirty=false,openRequest=0;
  const use=()=>body.isConnected && panel.open;
  function button(p,title,fn) {
    const b=add(p,'button',title);b.type='button';
    b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){if(use())note(e.message);}finally{b.disabled=false;}};
    return b;
  }
  function note(text){const e=body.querySelector('[role=status]');if(e)e.textContent=text;}
  function install(value){
    view=value;draft=structuredClone(view.groups);dirty=false;
    if(!draft[group])group=Object.keys(draft)[0];
    draw();
  }
  function draw(){
    body.replaceChildren();
    const status=add(body,'p',view.mode==='proposal'?'Bản đề xuất · chờ biên tập và lưu':('Bản làm việc · lần lưu '+view.revision));
    status.setAttribute('role','status');
    const nav=add(body,'div');nav.className='studio-nav';nav.setAttribute('aria-label','Phần tài liệu');
    for(const id of Object.keys(draft)){
      const b=button(nav,studioLabels[id],()=>{group=id;draw();});
      b.setAttribute('aria-pressed',String(id===group));
    }
    const layout=add(body,'div');layout.className='studio-layout';
    const edit=add(layout,'section');edit.setAttribute('aria-label',studioLabels[group]);
    add(edit,'h4',studioLabels[group]);
    add(edit,'p',view.approvals[group]?'Đã có quyết định duyệt phần này.':'Chờ người duyệt độc lập.');
    for(const [key,value] of Object.entries(draft[group])){
      const label=add(edit,'label',studioLabels[key]);
      const input=add(label,'textarea');input.value=value;input.rows=key==='commercial_terms'||key==='evidence'?4:2;
      input.maxLength=['commercial_terms','evidence'].includes(key)?30000:5000;
      input.oninput=()=>{draft[group][key]=input.value;dirty=true;note('Có thay đổi chưa lưu');};
      const issues=view.quality_issues.filter(i=>i.group===group && i.field===key).map(i=>states[i.reason]);
      const evidence=view.findings.filter(i=>i.field==='studio.'+group+'.'+key);
      const ids=[];
      for(const item of new Set([...issues,...evidence.map(i=>states[i.outcome==='reviewed'?'reviewed':i.diagnostic]||states[i.outcome])])){
        if(!item)continue;
        const finding=add(edit,'small',item);finding.id='studio-finding-'+(++studioHintSequence);ids.push(finding.id);
      }
      if(ids.length)input.setAttribute('aria-describedby',ids.join(' '));
    }
    const side=add(layout,'aside');side.setAttribute('aria-label','Nguồn được duyệt');add(side,'h4','Nguồn được duyệt');
    for(const src of view.references){add(side,'strong',src.handle);add(side,'p',src.text);}
    const publicView=add(side,'details');add(publicView,'summary','Bản xem trước dành cho khách');add(publicView,'h5',view.preview.title);add(publicView,'p',view.preview.body);
    const history=add(side,'details');add(history,'summary','Lịch sử tài liệu ('+view.history.length+')');
    for(const entry of view.history){const row=add(history,'details');add(row,'summary','Lần lưu '+entry.revision);
      for(const [key,value] of Object.entries(entry.groups[group]||{})){add(row,'strong',studioLabels[key]);add(row,'p',value);}}
    const trace=add(side,'details');add(trace,'summary','Thông tin kiểm toán');add(trace,'p',view.version);add(trace,'code',view.asset_digests[group]);
    button(edit,'Lưu bản biên tập',async()=>{
      const v=await api(path,'PATCH',{expected_revision:view.revision,groups:draft});
      if(use()){install(v);if(afterSave)afterSave(v);}
    });
    if(['admin','owner'].includes(role) && view.status==='submitted' && !view.approvals[group]){
      const rationale=add(edit,'label','Nhận xét về chất lượng và mức phù hợp');const reason=add(rationale,'textarea');reason.maxLength=500;
      button(edit,'Duyệt riêng phần '+studioLabels[group],async()=>{
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
