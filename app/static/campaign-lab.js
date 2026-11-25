function createCampaignLab(api) {
  const by = id => document.getElementById(id);
  const panel = by('campaign-lab'), select = by('lab-campaign'), form = by('lab-form');
  const status = by('lab-status'), results = by('lab-results'), submit = form.querySelector('button');
  const number = new Intl.NumberFormat('vi-VN');
  const states = {proposed:'Đề xuất', planned:'Đã lên kế hoạch', approved:'Đã duyệt', scheduled:'Đã lên lịch',
    authorized:'Đã cho phép', executed:'Đã mô phỏng thực thi', cancelled:'Đã hủy', failed:'Thất bại'};
  let tenant = '', controller = null;
  function element(tag, value, className) {
    const node = document.createElement(tag);
    if (value != null) node.textContent = value;
    if (className) node.className = className;
    return node;
  }
  function clear() {
    controller?.abort();
    controller = null;
    results.replaceChildren();
    status.textContent = '';
    submit.disabled = false;
    panel.removeAttribute('aria-busy');
  }
  function scope(nextTenant, campaigns) {
    const previous = select.value;
    if (tenant !== nextTenant || !campaigns.some(item => item.id === previous)) clear();
    tenant = nextTenant;
    panel.hidden = !campaigns.length;
    select.replaceChildren(...campaigns.map(item => new Option(item.name, item.id)));
    if (campaigns.some(item => item.id === previous)) select.value = previous;
  }
  function metricGrid(pairs) {
    const grid = element('div', null, 'lab-metrics');
    for (const [label, value, unit] of pairs) {
      const card = element('div', null, 'metric');
      const display = Number.isFinite(value) ? number.format(value) + (unit || '') : 'Chưa đo';
      card.append(element('span', label), element('strong', display));
      grid.append(card);
    }
    return grid;
  }
  function render(data) {
    const report = data.report;
    results.append(element('h4', 'Kế hoạch và sản xuất'), element('p', data.plan.objective), element('p', data.plan.strategy),
      metricGrid([['Gói công việc', data.plan.work_packages.length], ['Tài sản đã tạo', data.assets.length],
        ['Tài sản duyệt mô phỏng', data.work_units.fixture_accepted],
        ['Tác vụ đã mô phỏng thực thi', data.actions.filter(a => a.state === 'executed').length]]));
    const list = element('ul', null, 'lab-list');
    for (const asset of data.assets) {
      const li = element('li'), detail = element('details');
      detail.append(element('summary', asset.title), element('p', asset.body),
        element('small', 'Phiên bản ' + asset.revision + ' · ' + (states[asset.status] || asset.status)));
      li.append(detail);
      list.append(li);
    }
    results.append(list, element('h4', 'Nhật ký thực thi mô phỏng'));
    const actions = element('ul');
    for (const action of data.actions) {
      const title = data.assets.find(asset => asset.id === action.asset_id)?.title || action.id;
      actions.append(element('li', title + ' · ' + action.history.map(step => states[step] || step).join(' → ')));
    }
    results.append(actions, element('h4','Phễu bán hàng mô phỏng'),
      metricGrid([['Phiên truy cập',report.sessions], ['Yêu cầu báo giá',report.rfqs],
        ['Lead đủ điều kiện',report.qualified_leads], ['Bàn giao Sales',report.sales_handoffs],
        ['Báo giá',report.quotations], ['Đơn đã ghi nhận',report.orders], ['Đơn đã hủy',report.cancelled_orders],
        ['Doanh thu xác nhận',report.confirmed_revenue_vnd,' ₫'], ['Doanh thu có nguồn',report.attributed_revenue_vnd,' ₫'],
        ['Chi phí Marketing',report.marketing_cost_vnd,' ₫']]),
      element('h4','Đề xuất cho vòng tiếp theo'), element('p',data.recommendation));
  }
  select.addEventListener('change', clear);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!tenant || !select.value || submit.disabled) return;
    clear();
    const requestedCampaign = select.value, request = new AbortController();
    controller = request;
    submit.disabled = true;
    panel.setAttribute('aria-busy','true');
    status.textContent = 'Đang chạy kịch bản và đối soát các sự kiện…';
    try {
      const data = await api('/api/tenants/' + encodeURIComponent(tenant) + '/campaigns/' +
        encodeURIComponent(requestedCampaign) + '/execution-lab/replay','POST',null,false,request.signal);
      if (controller !== request) return;
      if (data.synthetic !== true || data.campaign_id !== requestedCampaign) throw Error('Phạm vi kết quả không khớp.');
      render(data);
      status.textContent = 'Đã hoàn tất mô phỏng với dữ liệu tổng hợp.';
    } catch (error) {
      if (controller !== request) return;
      results.replaceChildren();
      status.textContent = error.message;
    } finally {
      if (controller === request) {
        submit.disabled = false;
        panel.removeAttribute('aria-busy');
      }
    }
  });
  return {scope};
}
