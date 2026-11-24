/* Invitations live inside the app. Accepting one refreshes the authenticated workspace list. */
function createRecipientPanel(root, api, notify, enterInvitedWorkspace) {
  let revision = 0;
  function reset() { revision++; root.replaceChildren(); }
  function node(parent, tag, label) {
    const element = document.createElement(tag);
    if (label) element.textContent = label;
    parent.append(element);
    return element;
  }
  function action(parent, caption, run) {
    const control = node(parent, 'button', caption);
    control.type = 'button';
    control.onclick = async () => {
      control.disabled = true;
      try { await run(); } catch (error) { notify(error.message, true); }
      finally { control.disabled = false; }
    };
    return control;
  }
  const roles = {client_viewer:'Khách hàng', viewer:'Nhân viên xem', editor:'Biên tập viên', admin:'Quản trị viên'};
  function field(parent, caption, tag) {
    const control = node(node(parent, 'label', caption), tag);
    control.setAttribute('aria-label', caption);
    return control;
  }
  function options(select, rows, blank) {
    select.replaceChildren(new Option(blank, ''), ...rows.map(item => new Option(item.name, item.id)));
  }
  function permissions(parent, clients, brands, campaigns, grant) {
    const client = field(parent, 'Khách hàng', 'select');
    options(client, clients, 'Chọn khách hàng');
    client.required = true;
    client.value = grant?.client_id || '';
    client.disabled = Boolean(grant);
    const brand = field(parent, 'Thương hiệu', 'select');
    const campaign = field(parent, 'Chiến dịch', 'select');
    function updateCampaigns() {
      options(campaign, campaigns.filter(c => c.brand_id === brand.value), 'Tất cả trong phạm vi');
      campaign.disabled = !brand.value;
    }
    function updateBrands() {
      options(brand, brands.filter(b => b.client_id === client.value), 'Tất cả thương hiệu');
      brand.disabled = !client.value;
      updateCampaigns();
    }
    client.onchange = updateBrands;
    brand.onchange = updateCampaigns;
    updateBrands();
    brand.value = grant?.brand_id || '';
    updateCampaigns();
    campaign.value = grant?.campaign_id || '';
    node(parent, 'p', 'Người nhận được xem các phiên bản đã chia sẻ trong phạm vi này.');
    function flag(caption, checked) {
      const input = field(parent, caption, 'input');
      input.type = 'checkbox';
      input.checked = Boolean(checked);
      return input;
    }
    const comment = flag('Cho phép bình luận', grant?.can_comment);
    const decide = flag('Cho phép duyệt, từ chối hoặc yêu cầu sửa', grant?.can_decide);
    return {client, rights:() => ({brand_id:brand.value || null, campaign_id:campaign.value || null,
      can_comment:comment.checked, can_decide:decide.checked})};
  }
  function offer(i, accept) {
    const box = node(root, 'section');
    box.className = 'panel';
    node(box, 'h4', 'Lời mời từ '+i.workspace_name);
    const terms = node(box, 'dl');
    terms.style.overflowWrap = 'anywhere';
    function term(label, value) {
      node(terms, 'dt', label);
      node(terms, 'dd', value);
    }
    function scopeLabel(name, id, all) {
      if (!id) return all;
      return name ? name+' ('+id+')' : id;
    }
    term('Vai trò', roles[i.role]);
    if (i.role === 'client_viewer') {
      term('Khách hàng', scopeLabel(i.client_name, i.client_id));
      term('Thương hiệu', scopeLabel(i.brand_name, i.brand_id, 'Tất cả thương hiệu của khách hàng'));
      term('Chiến dịch', scopeLabel(i.campaign_name, i.campaign_id, 'Tất cả chiến dịch trong phạm vi trên'));
      term('Bình luận', i.can_comment ? 'Được phép' : 'Không được phép');
      term('Duyệt, từ chối hoặc yêu cầu sửa', i.can_decide ? 'Được phép' : 'Không được phép');
    }
    term('Hết hạn', new Date(i.expires_at).toLocaleString('vi-VN'));
    action(box, 'Chấp nhận lời mời', accept);
  }
  async function linked(secret, onStale) {
    reset();
    const ticket = revision;
    const i = await api('/api/me/invitation-link','POST',{token:secret});
    if (ticket !== revision) return;
    offer(i, async () => {
      try {
        await api('/api/me/invitation-link/accept','POST',{token:secret});
      } catch (error) {
        if (error.status !== 404) throw error;
        if (ticket === revision) {
          reset();
          onStale();
        }
        return;
      }
      if (ticket === revision) await enterInvitedWorkspace(i.tenant_id);
    });
  }
  async function show(tenant, role, clients, brands, campaigns, expanded = Boolean(root.querySelector(":scope > details[open]"))) {
    const ticket = ++revision;
    root.replaceChildren();
    const base = '/api/tenants/'+encodeURIComponent(tenant);
    const admin = ['admin','owner'].includes(role);
    const refresh = () => ticket === revision && show(tenant, role, clients, brands, campaigns, true);
    let inbox, grants, invites;
    try {
      [inbox, grants, invites] = await Promise.all([api('/api/me/invitations'),
        admin ? api(base+'/recipients') : [], admin ? api(base+'/invitations') : []]);
    } catch (error) {
      if (ticket !== revision) return;
      node(root, 'p', 'Không tải được lời mời và quyền truy cập.');
      action(root, 'Thử tải lại quyền', refresh);
      return;
    }
    if (ticket !== revision) return;
    for (const i of inbox) offer(i, async () => {
      await api('/api/me/invitations/'+i.id+'/accept', 'POST');
      if (ticket === revision) await enterInvitedWorkspace(i.tenant_id);
    });
    if (!admin) return;
    const panel = node(root, 'details');
    panel.className = 'panel';
    panel.open = expanded;
    node(panel, 'summary', 'Quản lý người nhận và lời mời');
    node(panel, 'h4', 'Mời người nhận');
    const form = node(panel, 'form');
    const email = field(form, 'Email người nhận', 'input');
    email.type = 'email';
    email.required = true;
    const roleSelect = field(form, 'Vai trò được mời', 'select');
    for (const [key, label] of Object.entries(roles)) {
      if (key !== 'admin' || role === 'owner') roleSelect.add(new Option(label, key));
    }
    const scope = node(form, 'fieldset');
    const fields = permissions(scope, clients, brands, campaigns);
    roleSelect.onchange = () => {
      scope.disabled = roleSelect.value !== 'client_viewer';
      scope.hidden = scope.disabled;
    };
    const submit = node(form, 'button', 'Tạo lời mời trong ứng dụng');
    form.onsubmit = async event => {
      event.preventDefault();
      submit.disabled = true;
      try {
        const terms = {email:email.value, role:roleSelect.value};
        if (terms.role === 'client_viewer') Object.assign(terms,{client_id:fields.client.value},fields.rights());
        await api(base+'/invitations','POST',terms);
        await refresh();
      } catch (error) { notify(error.message, true); }
      finally { submit.disabled = false; }
    };
    node(panel, 'h4', 'Lời mời chưa sử dụng');
    if (!invites.length) node(panel,'p','Chưa có lời mời.');
    for (const i of invites) {
      const row = node(panel,'div');
      node(row, 'span', i.email+' · '+(i.client_name || roles[i.role])+' · '+(i.state==='expired'?'Đã hết hạn':'Đang chờ'));
      action(row, 'Gửi lại lời mời', async () => { await api(base+'/invitations/'+i.id+'/resend', 'POST'); await refresh(); });
      action(row, 'Thu hồi lời mời', async () => { await api(base+'/invitations/'+i.id, 'DELETE'); await refresh(); });
    }
    node(panel, 'h4', 'Người nhận đang có quyền');
    if (!grants.length) node(panel,'p','Chưa có người nhận.');
    for (const grant of grants) {
      const row = node(panel, 'details');
      node(row, 'summary', (grant.email || grant.user_id)+' · '+(clients.find(c=>c.id===grant.client_id)?.name || grant.client_id));
      const edit = permissions(row, clients, brands, campaigns, grant);
      action(row, 'Lưu quyền', async () => {
        await api(base+'/members/'+grant.user_id+'/review-rights','PUT',edit.rights());
        await refresh();
      });
      action(row, 'Thu hồi quyền xem', async () => {
        if (!window.confirm('Thu hồi toàn bộ quyền truy cập của người nhận này?')) return;
        await api(base+'/members/'+grant.user_id+'/client-scope','DELETE');
        await refresh();
      });
    }
  }
  return {reset,show,linked};
}
