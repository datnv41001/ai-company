/* Grant and case state are scoped to one authenticated actor, workspace and campaign. */
function createCampaignRoleDesk(api) {
  const by = id => document.getElementById(id);
  const panel = by('campaign-role-desk'), campaign = by('desk-campaign'), controls = by('desk-controls');
  const cases = by('desk-cases'), notice = by('desk-notice');
  const roles = {marketing_operator:'Điều phối Marketing',sales_recipient:'Nhân viên Sales',service_assignee:'Người thực hiện dịch vụ',
    reviewer:'Người phản biện',business_owner:'Người phụ trách kinh doanh'};
  const labels = {request:'Yêu cầu',requested:'Mới tiếp nhận',qualified:'Đủ điều kiện',received:'Chờ bổ sung',assigned:'Đã phân công',
    confirmed:'Đã xác nhận',completed:'Hoàn thành',cancelled:'Đã hủy',no_show:'Khách vắng mặt',accepted:'Sales đã nhận',quoted:'Đã báo giá',
    ordered:'Đã đặt hàng',rejected:'Đã từ chối',assign:'Phân công',reassign:'Chuyển người phụ trách',confirm:'Xác nhận lịch',
    reschedule:'Đổi lịch',cancel:'Hủy',complete:'Xác nhận hoàn thành',accept:'Tiếp nhận',reject:'Từ chối',quote:'Đã gửi báo giá',
    order:'Đã nhận đơn',review_feedback:'Gửi nhận xét'};
  let tenant='', actor='', membership='', cid='', active='', epoch=0;
  const node=(parent,tag,text)=>{const n=document.createElement(tag); if(text!=null)n.textContent=text; parent.append(n);return n;};
  function field(form,label,type,options) {
    const wrapper=node(form,'label',label), el=node(wrapper,options?'select':'input');
    if(options)for(const [value,name] of options)el.add(new Option(name,value));
    else {el.type=type;el.required=true;}
    return el;
  }
  const root=()=>'/api/tenants/'+encodeURIComponent(tenant)+'/campaigns/'+encodeURIComponent(cid)+'/business-desk';
  function clear() {epoch++;controls.replaceChildren();cases.replaceChildren();notice.textContent='';}
  function scope(t,r,rows,user) {
    const same=t===tenant && r===membership && user===actor && rows.some(x=>x.id===cid);
    if(!same){clear();cid='';active='';}
    tenant=t;actor=user;membership=r;
    panel.hidden=!t || r==='client_viewer' || !rows.length;
    campaign.replaceChildren(new Option('Chọn chiến dịch',''),...rows.map(c=>new Option(c.name,c.id)));campaign.value=cid;
  }
  async function post(form,path,payload) {
    const generation=epoch;
    const button=form.querySelector('button');button.disabled=true;
    try {await api(path,'POST',payload);if(generation===epoch)await load();}
    catch(e){if(generation===epoch){notice.textContent=e.message;button.disabled=false;}}
  }
  function submit(form,title,onSubmit) {
    const btn=node(form,'button',title);btn.type='submit';
    form.addEventListener('submit',e=>{e.preventDefault();if(form.reportValidity())onSubmit();});
  }
  function manager(grants) {
    const group=node(controls,'details');node(group,'summary','Phân quyền theo chiến dịch');
    const form=node(group,'form'),subject=field(form,'Mã thành viên nội bộ','text');
    const role=field(form,'Vai trò được giao',null,Object.entries(roles));
    const mode=field(form,'Thay đổi quyền',null,[['grant','Cấp quyền'],['withdraw','Thu hồi']]);
    const key=crypto.randomUUID();
    submit(form,'Lưu phân quyền',()=>{
      const current=grants.find(g=>g.subject===subject.value.trim() && g.role===role.value);
      post(form,root()+'/grants',{key,subject:subject.value.trim(),role:role.value,enabled:mode.value==='grant',expected_revision:current?.revision||0});
    });
    for(const g of grants.filter(x=>x.effective))node(group,'p',roles[g.role]+' · '+g.subject);
  }
  function actions(entity,state) {
    let result=[];
    const routes=['marketing_operator','business_owner'].includes(active);
    if(entity==='appointments'){
      if(routes)result=({requested:['confirm','cancel'],confirmed:['assign','reschedule','cancel'],assigned:['reassign','reschedule','cancel']})[state]||[];
      if(active==='service_assignee' && state==='assigned')result=['complete','no_show','cancel'];
    }else{
      if(routes)result=({qualified:['assign'],assigned:['reassign','cancel'],accepted:['cancel'],quoted:['cancel'],ordered:['cancel'],confirmed:['cancel']})[state]||[];
      if(active==='sales_recipient')result=({assigned:['accept','reject'],accepted:['quote','reject'],quoted:['order','reject']})[state]||[];
    }
    if(['reviewer','business_owner'].includes(active))result=[...result,'review_feedback'];
    return result;
  }
  function renderCase(x) {
    const value=x.value, card=node(cases,'article');card.className='panel';
    node(card,'h4',(x.entity==='leads'?'Yêu cầu báo giá':'Lịch dịch vụ')+' · '+value.id);
    if(value.intake){
      for(const f of value.intake.fields){
        const answer=value.intake.answers[f.id];
        if(answer!==undefined)node(card,'p',f.label+' · '+(f.options?.find(o=>o.value===answer)?.label||answer)+(f.unit?' '+f.unit:''));
      }
      if(value.missing?.includes('commercial_moq'))node(card,'p','Cần đối chiếu số lượng đặt tối thiểu trước khi chuyển Sales.');
    }
    node(card,'p',(labels[value.state]||value.state)+' · Lần cập nhật '+value.revision);
    if(value.location)node(card,'p',value.location);
    if(value.confirmed_for)node(card,'p','Lịch xác nhận · '+new Date(value.confirmed_for).toLocaleString('vi-VN'));
    const options=actions(x.entity,value.state);if(!options.length)return;
    const form=node(card,'form'),step=field(form,'Thao tác',null,options.map(s=>[s,labels[s]])),fields=node(form,'div');
    let extra,reason;
    function update() {
      fields.replaceChildren();extra=null;reason=null;
      if(['assign','reassign'].includes(step.value))extra=field(fields,'Mã người nhận có quyền trong chiến dịch','text');
      if(['confirm','reschedule'].includes(step.value))extra=field(fields,'Thời gian hẹn','datetime-local');
      if(['review_feedback','cancel','complete','no_show','reassign','reschedule','accept','reject'].includes(step.value))reason=field(fields,'Nhận xét và lý do','text');
    }
    step.addEventListener('change',update);update();
    let previous='',key='';
    submit(form,'Ghi nhận',()=>{
      const kind=step.value==='review_feedback'?'review_feedback':x.entity==='leads'?'sales':'appointment_decision';
      const payload={kind,plan_id:value.plan_id,expected_revision:value.revision};
      if(kind==='review_feedback')Object.assign(payload,{entity:x.entity,entity_id:value.id,note:reason.value});
      else {
        payload[kind==='sales'?'rfq_id':'appointment_id']=value.id;payload.step=step.value;
        if(extra) {if(extra.type==='datetime-local')payload.confirmed_for=new Date(extra.value).toISOString();else payload.assignee_id=extra.value.trim();}
        if(reason)payload[kind==='sales'?'reason':'feedback']=reason.value;
      }
      const logical=JSON.stringify(payload);
      if(logical!==previous){key=crypto.randomUUID();previous=logical;form.dataset.at=new Date().toISOString();}
      if(kind!=='review_feedback')payload.occurred_at=form.dataset.at;
      post(form,root()+'/'+active+'/decisions',{...payload,request_id:key});
    });
  }
  async function load() {
    clear();if(!cid)return;
    const generation=epoch,path=root();notice.textContent='Đang tải bàn giao…';
    try {
      const access=await api(path+'/access');if(generation!==epoch)return;
      const grantList=access.may_manage?await api(path+'/grants'):[];if(generation!==epoch)return;
      if(access.may_manage)manager(grantList);
      if(!access.roles.length){notice.textContent='Tài khoản chưa được giao vai trò trong chiến dịch này.';return;}
      if(!access.roles.includes(active))active=access.roles[0];
      const chooser=field(controls,'Vai trò đang làm việc',null,access.roles.map(r=>[r,roles[r]]));chooser.value=active;
      chooser.addEventListener('change',()=>{active=chooser.value;load();});
      const state=await api(path+'/'+active+'/inbox');if(generation!==epoch)return;
      notice.textContent=state.items.length?state.items.length+' hồ sơ trong phạm vi phụ trách.':'Chưa có hồ sơ được giao.';
      for(const x of state.items)renderCase(x);
      for(const f of state.feedback)node(cases,'p',f.entity_id+' · Nhận xét lần '+f.reviewed_revision+' · '+f.note);
    }catch(e){if(generation===epoch)notice.textContent=e.message;}
  }
  campaign.addEventListener('change',()=>{cid=campaign.value;active='';load();});
  return {scope,clear:()=>{cid='';active='';clear();panel.hidden=true;}};
}
