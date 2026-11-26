const productionFrames = new WeakMap();
window.addEventListener('message', e=>{
  if(e.origin==='null' && e.source && ['amc-landing-submit/1','amc-landing-submit/2'].includes(e.data?.type)){
    productionFrames.get(e.source)?.(e.data);
  }
});
function mountProductionStudio(host,api,path,view,kind,isDirty){
  const root=document.createElement('details');root.className='production-studio';host.append(root);
  const add=(parent,tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;parent.append(n);return n;};
  add(root,'summary',kind==='creative'?'Creative Studio · sản xuất ảnh và video':'Landing Studio · trang thử nghiệm');
  const body=add(root,'section'), base=path+'/production';
  const tell=add(body,'p');tell.setAttribute('role','status');
  const controls=add(body,'div'),output=add(body,'div');
  let current;
  const button=(parent,text,fn)=>{
    const b=add(parent,'button',text);b.type='button';
    b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){tell.textContent=e.message;}finally{b.disabled=false;}};
    return b;
  };
  function select(parent,label,options){
    const wrap=add(parent,'label',label),field=add(wrap,'select');
    for(const [v,t] of options)field.add(new Option(t,v));return field;
  }
  async function show(item){
    output.replaceChildren();
    const result=add(output,'div');
    let visit=null,frame=null;
    async function file(name){
      const data=await api(base+'/'+item.id+'/files/'+name);
      const bytes=Uint8Array.from(atob(data.base64),c=>c.charCodeAt(0));
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
      if(hash!==item.files[name].sha256||hash!==data.sha256||bytes.length!==data.bytes)throw new Error('File tải về không khớp bản được duyệt.');
      return {...data,uri:'data:'+data.mime+';base64,'+data.base64};
    }
    if(!item){tell.textContent='Lưu và duyệt nội dung nguồn để tạo bản sản xuất đầu tiên.';return;}
    tell.textContent='Bản sản xuất '+item.version+' · Studio '+item.studio_revision+(item.approval?' · Đã duyệt file':' · Chờ người thứ hai kiểm tra file');
    if(kind==='creative'){
      const stage=add(result,'figure');stage.className='production-canvas';
      const image=add(stage,'img');image.alt='Bản kết xuất từ nội dung và minh họa đã chọn';
      const caption=add(stage,'figcaption');
      const size=select(result,'Tỉ lệ xem',[['landscape','Ngang 16:9'],['portrait','Dọc 4:5'],['square','Vuông 1:1'],['source','Minh họa tổng hợp nguồn']]);
      async function paint(){const name=size.value+'.png';image.src=(await file(name)).uri;caption.textContent=name+' · SHA-256 '+item.files[name].sha256.slice(0,12);}
      size.onchange=()=>paint().catch(e=>tell.textContent=e.message);await paint();
      const film=add(result,'details');add(film,'summary','Storyboard, phụ đề và video sáu giây');
      let loaded=false;film.ontoggle=async()=>{if(!film.open||loaded)return;loaded=true;
        try{const v=add(film,'video');v.controls=true;v.preload='metadata';v.setAttribute('playsinline','');v.src=(await file('preview.webm')).uri;
          const track=add(v,'track');track.kind='captions';track.label='Phụ đề';track.default=true;track.src=(await file('captions.vtt')).uri;
          const master=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob((await file('master.json')).base64),c=>c.charCodeAt(0))));
          for(const s of master.scenes)add(film,'p',s.from+'–'+s.to+'s · '+s.caption);
        }catch(e){tell.textContent=e.message;}}
      add(result,'p','Minh họa hình học do AMC dựng cho sandbox · Be Vietnam Pro, SIL OFL.');
    }else{
      const layout=select(result,'Kích thước bản xem',[['auto','Theo màn hình'],['mobile','Điện thoại']]);
      frame=add(result,'iframe');frame.title='Trang đích sandbox';frame.setAttribute('sandbox','allow-scripts allow-forms');frame.referrerPolicy='no-referrer';
      layout.onchange=()=>frame.classList.toggle('phone',layout.value==='mobile');
      frame.srcdoc=new TextDecoder().decode(Uint8Array.from(atob((await file('landing.html')).base64),c=>c.charCodeAt(0)));
      const wire=f=>productionFrames.set(f.contentWindow,async data=>{
        try{if(!result.isConnected || item.id!==current.id)return;
          if(!visit)throw new Error('Bắt đầu phiên thử trong Landing Studio trước khi gửi.');
          const answers=data.type==='amc-landing-submit/2'
            ? {contract_digest:data.contract_digest,consent:data.consent,answers:data.answers}
            : {quantity:data.quantity,place:data.place,days:data.days};
          const receipt=await api(base+'/'+item.id+'/submissions','POST',{request_id:visit.submit,visit_id:visit.id,...answers});
          const en=item.master.intake_contract?.locale==='en-US';
          let status=en?'Your test quote request was recorded.':'Đã ghi nhận yêu cầu báo giá thử.';
          if(receipt.kind==='appointment')status=en?'Your request was recorded. Staff will review it before confirming an appointment.':
            'Đã ghi nhận đề nghị. Người phụ trách sẽ đối chiếu trước khi xác nhận lịch.';
          else if(receipt.value.missing?.includes('commercial_moq'))status=en?'Your inquiry was recorded for advice. The minimum order must be checked before it qualifies for a quote.':
            'Đã ghi nhận nhu cầu tư vấn. Cần đối chiếu mức tối thiểu trước khi đủ điều kiện báo giá.';
          const message=status+' · '+receipt.id;
          tell.textContent=message;f.contentWindow.postMessage({type:'amc-landing-result/1',ok:true,message},'*');
        }catch(e){f.contentWindow.postMessage({type:'amc-landing-result/1',ok:false,message:e.message},'*');}
      });
      wire(frame);
      const full=button(result,'Xem trang toàn màn hình',()=>{
        const dialog=add(result,'dialog');dialog.className='prod-page-dialog';dialog.setAttribute('aria-label','Xem trang đích toàn màn hình');
        const close=button(dialog,'Đóng bản xem',()=>dialog.close());dialog.showModal();
        const large=add(dialog,'iframe');large.title='Trang đích toàn màn hình';large.setAttribute('sandbox','allow-scripts allow-forms');
        large.referrerPolicy='no-referrer';large.srcdoc=frame.srcdoc;wire(large);close.focus();
        dialog.onclose=()=>{dialog.remove();full.focus();};
      });
      if(item.approval && item.id===current.id)button(result,'Bắt đầu phiên thử',async()=>{
        if(isDirty())throw new Error('Hãy lưu và duyệt nội dung đang sửa.');
        const event=await api(base+'/'+item.id+'/visits','POST',{request_id:crypto.randomUUID()});
        visit={id:event.entity_id,submit:crypto.randomUUID()};tell.textContent='Đã ghi một lượt mở trang tổng hợp.';
      });
    }
    if(!item.approval && item.id===current.id){
      const label=add(result,'label','Nhận xét sau khi xem bản kết xuất');const note=add(label,'textarea');
      button(result,'Duyệt bản sản xuất',async()=>{
        if(isDirty())throw new Error('Hãy lưu và duyệt nội dung đang sửa.');
        await api(base+'/'+item.id+'/approve','POST',{expected_digest:item.digest,note:note.value});await load();
      });
    }
    const downloads=add(result,'details');add(downloads,'summary','Tải file và đối chiếu SHA-256');
    for(const [name,entry] of Object.entries(item.files)){
      const row=add(downloads,'div');add(row,'code',entry.sha256);
      button(row,name,async()=>{const a=document.createElement('a');a.href=(await file(name)).uri;a.download=name;a.click();});
    }
  }
  async function load(){
    const all=(await api(base)).filter(x=>x.kind===kind);current=all[0];controls.replaceChildren();
    if(all.length>1){
      const versions=select(controls,'Lịch sử bản sản xuất',all.map(row=>[row.id,'Bản '+row.version+' · Studio '+row.studio_revision]));
      versions.onchange=()=>show(all.find(row=>row.id===versions.value)).catch(e=>tell.textContent=e.message);
    }
    let palette,motif,layout,custom;
    if(kind==='creative'){
      palette=select(controls,'Bảng màu đề xuất',[['forest','Rừng và chanh'],['cobalt','Cobalt và san hô'],['custom','Chọn màu theo brand']]);
      const paletteForm=add(controls,'div');paletteForm.hidden=true;
      custom=[['Màu chữ và nút','#123d31'],['Màu nhấn','#e5f39a'],['Nền giấy','#fcf9ed']].map(([label,initial])=>{
        const field=add(add(paletteForm,'label',label),'input');field.type='color';field.value=initial;return field;
      });
      palette.onchange=()=>{paletteForm.hidden=palette.value!=='custom';};
      motif=select(controls,'Minh họa tổng hợp',[['arches','Vòm đồng tâm'],['planes','Mảng gấp']]);
      layout=select(controls,'Bố cục master',[['art_first','Minh họa trên'],['text_first','Nội dung trên']]);
      if(current?.design){const design=current.design;palette.value=design.palette;motif.value=design.motif;layout.value=design.layout;
        if(design.palette==='custom'){paletteForm.hidden=false;custom.forEach((field,i)=>field.value=design.colors[i]);}}
    }
    button(controls,kind==='creative'?'Dựng master và các định dạng':'Dựng trang từ các phần đã duyệt',async()=>{
      if(isDirty())throw new Error('Hãy lưu và duyệt nội dung đang sửa.');
      const groups=kind==='creative'?['copy','creative_brief']:['copy','seo'];
      const args={kind,expected_revision:view.revision,expected_plan_digest:view.channel_edition.plan.plan_digest,
        expected_groups:Object.fromEntries(groups.map(g=>[g,view.asset_digests[g]])),expected_version:current?.version||0};
      if(kind==='creative')Object.assign(args,{palette:palette.value==='custom'?'forest':palette.value,
        ...(palette.value==='custom'?{colors:custom.map(c=>c.value)}:{}),motif:motif.value,layout:layout.value});
      await api(base,'POST',args);await load();
    });
    await show(current);
  }
  root.ontoggle=()=>{if(root.open)load().catch(e=>tell.textContent=e.message);};
}
