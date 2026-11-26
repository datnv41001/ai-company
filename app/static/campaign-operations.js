/* Render from scoped API receipts. Controls reuse the campaign's revision and retry handling. */
function campaignOperationForms({plan,production,ops,actions,sales,add,details,field,pick,command,sandbox,actor}) {
  const groupFor = {landing:'copy',seo:'seo',strategy:'client_strategy',measurement:'client_measurement',
    ad:'ad',social:'social',calendar:'calendar',creative_brief:'creative_brief'};
  const options = [];
  for (const asset of production.assets) {
    const group=groupFor[asset.kind];
    if (!group || !asset.approval_receipt || !['approved','shared'].includes(asset.status)) continue;
    const placement=['paid_media','sandbox_ad_slot','rehearse_placement','Vị trí quảng cáo'];
    const routes=({copy:[['website','sandbox_page','render_preview','Trang web'],placement],ad:[placement],
      seo:[['organic_search','sandbox_search','render_preview','Kết quả tìm kiếm']],
      social:[['organic_social','sandbox_social','render_preview','Mạng xã hội']]})[group]||[['internal','sandbox_review','render_preview','Duyệt nội bộ']];
    for (const [channel,destination,action_type,name] of routes) options.push({asset,group,channel,destination,action_type,name});
  }
  if (options.length) {
    const f=add(details(actions,'Lên lịch cho một nhóm nội dung đã duyệt'),'form');
    const target=pick(f,'Tài sản và đích mô phỏng',options.map((o,i)=>[String(i),o.asset.title+' · '+o.name]));
    const mode=pick(f,'Cách thực hiện',[['scheduled','Bộ điều phối cục bộ'],['manual','Chạy bằng tay']]);
    const id=field(f,'Mã lịch nhóm','text'), due=field(f,'Thời gian đến hạn','datetime-local'), fee=field(f,'Dự toán (VND)','number','0');
    command(f,'Giao tác vụ sandbox',()=>{
      const o=options[Number(target.value)];
      return sandbox(plan,{kind:'schedule',action_id:id.value,due_at:new Date(due.value).toISOString(),cost_vnd:fee.valueAsNumber,
        deliverable_id:o.asset.deliverable_id,expected_revision:o.asset.revision,expected_digest:o.asset.document_digest,
        target:{contract:'sandbox-capability/1',action_type:o.action_type,channel:o.channel,destination:o.destination,group:o.group,group_digest:o.asset.digest,mode:mode.value}});
    },{form:true});
  }
  if(production.assets.some(asset=>!asset.approval_receipt))add(actions,'small','Chỉ nhóm nội dung trên bản giao đã qua QA và có biên nhận duyệt riêng mới xuất hiện trong danh sách điều phối.');
  if (plan.buyer_action==='appointment' && plan.selling_unit) {
    const f=add(details(sales,'Yêu cầu lịch dịch vụ'),'form');
    const id=field(f,'Mã lịch hẹn','text'), qty=field(f,'Số lượng ('+plan.selling_unit+')','number','1'),
      when=field(f,'Giờ mong muốn','datetime-local'), place=field(f,'Nơi phục vụ','text'), purpose=field(f,'Nội dung dịch vụ','text');
    field(f,'Khách yêu cầu liên hệ để đặt lịch','checkbox');
    let observed;
    command(f,'Ghi nhận lịch hẹn',()=>sandbox(plan,{kind:'appointment',contract:'service-appointment/1',appointment_id:id.value,product_id:plan.product_id,
      unit:plan.selling_unit,quantity:qty.value,location:place.value,requested_for:new Date(when.value).toISOString(),service_scope:purpose.value,
      contact_purpose:'appointment_request',occurred_at:observed??=new Date().toISOString()}),{form:true});
  }
  const names={requested:'Đã yêu cầu',confirmed:'Đã xác nhận',assigned:'Đã phân công',completed:'Đã phục vụ',cancelled:'Đã hủy',no_show:'Khách vắng mặt'};
  for(const row of ops.appointments){
    const box=details(sales,row.id+' · '+names[row.state]);
    const slot=row.confirmed_for||row.requested_for;
    add(box,'p',[row.service_scope,row.location,slot?new Date(slot).toLocaleString('vi-VN'):'Chờ chọn giờ'].filter(Boolean).join(' · '));
    for(const h of row.history) if(h.feedback)add(box,'p',h.feedback);
    const next={requested:['confirm','cancel'],confirmed:['assign','cancel','no_show'],assigned:['complete','cancel','no_show']}[row.state]||[];
    for(const step of next){
      if(step==='complete' && row.assignee_id!==actor)continue;
      const label={confirm:'Xác nhận lịch hẹn',assign:'Nhận phụ trách lịch',complete:'Hoàn thành dịch vụ',cancel:'Hủy lịch hẹn',no_show:'Ghi nhận vắng mặt'}[step];
      const f=add(details(box,label),'form');
      const when=step==='confirm'?field(f,'Giờ hẹn đã thống nhất','datetime-local'):null;
      const note=['complete','cancel','no_show'].includes(step)?field(f,'Kết quả và phản hồi','text'):null;
      let observed;
      command(f,'Lưu '+label.toLocaleLowerCase('vi'),()=>sandbox({id:row.plan_id},{kind:'appointment_decision',appointment_id:row.id,expected_revision:row.revision,
        step,occurred_at:observed??=new Date().toISOString(),...(when?{confirmed_for:new Date(when.value).toISOString()}:{}),...(note?{feedback:note.value}:{}),
        ...(step==='assign'?{assignee_id:actor}:{})}),{form:true});
    }
  }
}
