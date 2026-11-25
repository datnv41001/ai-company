/* The catalog holds source material in memory only. Changing identity clears the view before any read. */
function createCatalogPane(root, api) {
  const kinds = {
    product: 'Sản phẩm',
    service: 'Dịch vụ',
    variant: 'Biến thể',
    market: 'Thị trường',
    offer: 'Giá bán',
    availability: 'Tồn kho',
    policy: 'Điều khoản',
    guidelines: 'Hướng dẫn thương hiệu',
    icp: 'Chân dung khách hàng',
    segment: 'Phân khúc',
    objective: 'Mục tiêu',
    company_objective: 'Mục tiêu chung doanh nghiệp',
    kpi: 'Chỉ số KPI',
  };
  const states = {
    draft: 'Nháp',
    approved: 'Đã duyệt',
    expired: 'Hết hạn',
    pending_effective: 'Chưa có hiệu lực',
    withdrawn: 'Đã thu hồi',
    superseded: 'Đã thay thế',
    disputed: 'Tranh chấp',
  };
  const titles = {
    name: 'Tên',
    sku: 'SKU',
    code: 'Mã danh mục',
    product: 'Sản phẩm hoặc dịch vụ',
    variant: 'Biến thể',
    market: 'Thị trường',
    locale: 'Ngôn ngữ',
    locales: 'Ngôn ngữ phục vụ',
    channel: 'Kênh',
    region: 'Địa bàn',
    amount: 'Giá theo đơn vị tiền tệ',
    currency: 'Tiền tệ',
    unit: 'Đơn vị',
    basis_quantity: 'Số lượng cơ sở',
    moq: 'Đặt hàng tối thiểu',
    tier_min: 'Từ số lượng',
    tier_max: 'Đến số lượng',
    tax: 'Thuế',
    condition_ids: 'Điều kiện bán',
    payment: 'Thanh toán',
    warranty: 'Bảo hành',
    shipping: 'Vận chuyển',
    status: 'Tình trạng',
    observed_at: 'Quan sát lúc',
    valid_from: 'Hiệu lực từ',
    valid_until: 'Hiệu lực đến',
    buyer: 'Loại khách',
    payment_type: 'Hình thức thanh toán',
    service_level: 'Gói dịch vụ',
    minimum: 'Số lượng từ',
    maximum: 'Số lượng đến',
    policy: 'Điều khoản áp dụng',
    availability: 'Quan sát kho',
    guidance: 'Hướng dẫn',
    tone: 'Giọng thương hiệu',
    description: 'Mô tả',
    basis: 'Căn cứ',
    needs: 'Nhu cầu',
    source: 'Nguồn chứng cứ',
    owner: 'Người phụ trách',
    parent: 'Mục tiêu cha trong thương hiệu',
    company_parent: 'Mục tiêu chung làm cha',
    company_objective: 'Mục tiêu chung để đo',
    campaign_id: 'Chiến dịch',
    level: 'Cấp mục tiêu',
    objective: 'Mục tiêu',
    method: 'Cách đo',
    window: 'Kỳ đo',
    baseline: 'Mốc ban đầu',
    target: 'Chỉ tiêu',
    actual: 'Thực tế',
    visibility: 'Phạm vi đọc',
    reason: 'Lý do quyết định',
    preferred_revision: 'Nguồn ưu tiên',
    title: 'Tên',
    quantity_unit: 'Đơn vị số lượng',
  };
  const pick = {
    channel: ['web', 'store', 'email', 'retail', 'wholesale', 'search', 'social', 'marketplace'],
    region: ['VN-HN', 'VN-SG', 'VN-DN'],
    locale: ['vi-VN', 'en', 'en-US'],
    currency: ['VND', 'USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'SGD', 'THB'],
    unit: ['piece', 'box', 'm²', 'tonne', 'kg', 'service', 'machine', 'participant', 'subscription_month', 'subscription_year'],
    tax: ['included', 'excluded', 'unknown'],
    status: ['available', 'unavailable', 'unknown'],
    buyer: ['retail', 'wholesale'],
    payment_type: ['prepaid', 'credit'],
    service_level: ['standard', 'extended'],
    basis: ['hypothesis', 'fact'],
    level: ['company', 'brand', 'campaign'],
    visibility: ['internal', 'public', 'restricted'],
  };
  const units = pick.unit;
  const friendly = {
    hypothesis: 'Giả thuyết',
    fact: 'Có căn cứ',
    available: 'Còn hàng',
    unavailable: 'Hết hàng',
    unknown: 'Chưa rõ',
    included: 'Đã gồm thuế',
    excluded: 'Chưa gồm thuế',
    company: 'Doanh nghiệp (trong hồ sơ thương hiệu)',
    brand: 'Thương hiệu',
    campaign: 'Chiến dịch',
    internal: 'Nội bộ',
    public: 'Công khai',
    restricted: 'Hạn chế',
    prepaid: 'Trả trước',
    credit: 'Trả sau',
    retail: 'Bán lẻ',
    wholesale: 'Bán buôn',
    standard: 'Tiêu chuẩn',
    extended: 'Mở rộng',
    piece: 'Cái',
    box: 'Hộp',
    service: 'Dịch vụ',
    cash_on_delivery: 'Thanh toán khi nhận hàng',
    pickup: 'Nhận tại cửa hàng',
    delivery: 'Giao hàng',
    'VN-HN': 'Hà Nội',
    'VN-SG': 'TP.HCM',
    'VN-DN': 'Đà Nẵng',
  };
  const placement = ['product', 'variant?', 'market', 'locale', 'channel', 'region'];
  const terms = ['buyer?', 'payment_type?', 'service_level?', 'quantity_unit?', 'minimum?', 'maximum?'];
  const forms = {
    product: ['name', 'code'],
    service: ['name', 'code'],
    variant: ['name', 'code', 'product'],
    market: ['name', 'code', 'locales'],
    guidelines: ['guidance', 'tone?'],
    icp: ['name', 'description', 'needs?', 'basis', 'source?', 'market?'],
    segment: ['name', 'description', 'needs?', 'basis', 'source?', 'market?'],
    company_objective: ['name', 'owner'],
    objective: ['name', 'level', 'parent?', 'company_parent?', 'campaign_id?', 'owner'],
    kpi: ['name', 'objective?', 'company_objective?', 'unit', 'method', 'window', 'owner', 'source?', 'baseline?', 'target?', 'actual?'],
    offer: [
      ...placement,
      'policy',
      'availability?',
      'amount',
      'currency',
      'unit',
      'basis_quantity',
      'moq',
      'tier_min',
      'tier_max?',
      'tax',
      'condition_ids?',
      'valid_from?',
      'valid_until?',
    ],
    availability: [...placement, 'status', 'observed_at', 'valid_until', ...terms],
    policy: [...placement, 'warranty?', 'payment?', 'shipping?', ...terms, 'valid_from?', 'valid_until?'],
  };
  const refs = {
    product: 'product',
    variant: 'variant',
    market: 'market',
    policy: 'policy',
    availability: 'availability',
    source: 'source',
    objective: 'objective',
    parent: 'objective',
    company_parent: 'company_objective',
    company_objective: 'company_objective',
  };
  let scope,
    epoch = 0,
    controller,
    clientRoot,
    companyPath,
    path,
    canWrite = false,
    canApprove = false,
    kind,
    cursor,
    pages = [],
    actorKey,
    typedSearch,
    details,
    form,
    list,
    message,
    filter,
    pager,
    kindSelect;
  const el = (tag, txt) => {
    const node = document.createElement(tag);
    if (txt !== undefined) node.textContent = txt;
    return node;
  };
  function button(label, action) {
    const b = el('button', label);
    b.type = 'button';
    b.addEventListener('click', () => guard(action));
    return b;
  }
  function guard(fn) {
    const token = epoch;
    Promise.resolve()
      .then(() => {
        if (token === epoch) return fn();
      })
      .catch((err) => {
        if (token !== epoch || err?.name === 'AbortError') return;
        if ([401, 403, 404].includes(err.status)) {
          reset();
          root.textContent = 'Quyền truy cập hoặc phạm vi đã thay đổi. Mở lại hồ sơ để xem dữ liệu hiện tại.';
          return;
        }
        message.textContent = err.message === 'Revision is outside its validity interval'
          ? 'Chỉ có thể duyệt trong khoảng hiệu lực đã lưu. Hãy kiểm tra ngày bắt đầu và ngày kết thúc.'
          : err.message || 'Chưa tải được dữ liệu. Thử lại.';
      });
  }
  function reset() {
    epoch++;
    controller?.abort();
    scope = null;
    pages = [];
    cursor = '';
    root.replaceChildren();
  }
  function options(input, values, optional = false) {
    if (optional) input.add(new Option('Chưa chọn', ''));
    for (const v of values) input.add(new Option(friendly[v] || v, v));
  }
  function makeRow(parent, name, input) {
    const label = el('label', titles[name] || name);
    label.append(input);
    parent.append(label);
  }
  function note(text) {
    message.textContent = text;
  }
  async function get(url) {
    return api(url, 'GET', null, false, controller.signal);
  }
  function collection(itemKind) {
    return itemKind === 'company_objective' ? companyPath : path + '/items';
  }
  function labelOf(row) {
    return row.kind === 'availability' ? friendly[row.label] || row.label : row.label;
  }
  function selected(ctx) {
    return ctx === epoch && scope;
  }
  async function show(context) {
    reset();
    scope = context;
    const life = epoch;
    controller = new AbortController();
    const tenant = context.tenant?.id || context.tenant,
      client = context.client?.id || context.client,
      brand = context.brand?.id || context.brand;
    if (!tenant || !client || !brand || context.role === 'client_viewer') return;
    actorKey = ['catalog', context.actor?.id || context.actor, tenant, client, brand].join('/');
    clientRoot = '/api/tenants/' + encodeURIComponent(tenant);
    companyPath = clientRoot + '/clients/' + encodeURIComponent(client) + '/company-objectives';
    path =
      clientRoot + '/clients/' + encodeURIComponent(client) + '/brands/' + encodeURIComponent(brand) + '/catalog';
    canWrite = ['editor', 'admin', 'owner'].includes(context.role);
    canApprove = ['admin', 'owner'].includes(context.role);
    root.className = 'marketing-catalog';
    root.append(el('h3', 'Danh mục Marketing'));
    const tools = el('div');
    tools.className = 'catalog-tools';
    kindSelect = el('select');
    kindSelect.setAttribute('aria-label', 'Loại dữ liệu');
    for (const [v, l] of Object.entries(kinds)) kindSelect.add(new Option(l, v));
    typedSearch = el('input');
    typedSearch.type = 'search';
    typedSearch.placeholder = 'Tìm tên hoặc SKU';
    typedSearch.setAttribute('aria-label', 'Tìm danh mục');
    const submit = button('Tìm', () => reload(true));
    tools.append(kindSelect, typedSearch, submit);
    if (canWrite) tools.append(button('Thêm mới', () => edit()));
    kindSelect.onchange = () => guard(() => reload(true));
    typedSearch.onkeydown = (e) => {
      if (e.key === 'Enter') submit.click();
    };
    message = el('p');
    message.setAttribute('role', 'status');
    list = el('ul');
    list.className = 'catalog-list';
    pager = el('nav');
    pager.setAttribute('aria-label', 'Trang danh mục');
    details = el('section');
    details.className = 'catalog-detail';
    root.append(tools, message, list, pager, details);
    await reload(true);
    const key = sessionStorage.getItem(actorKey + '/pending');
    if (!key || !selected(life)) return;
    try {
      const savedKind = sessionStorage.getItem(actorKey + '/kind');
      const base = savedKind === 'company_objective' ? companyPath : path;
      const record = await get(base + '/commands/' + encodeURIComponent(key));
      if (selected(life)) {
        kindSelect.value = record.kind;
        await reload(true);
        await inspect(record.id);
        note('Đã khôi phục lần lưu trước.');
        sessionStorage.removeItem(actorKey + '/pending');
      }
    } catch (err) {
      if (selected(life) && err.status !== 404) note('Chưa xác nhận được lần lưu trước.');
    }
  }
  async function reload(first = false) {
    const life = epoch,
      queryId = Symbol();
    filter = queryId;
    if (first) {
      cursor = '';
      pages = [];
      details.replaceChildren();
    }
    kind = kindSelect.value;
    const q = new URLSearchParams({ kind, q: typedSearch.value, after: cursor || '', limit: '12' });
    const result = await get(collection(kind) + '?' + q);
    if (!selected(life) || queryId !== filter) return;
    list.replaceChildren();
    pager.replaceChildren();
    for (const row of result.items) {
      const li = el('li');
      li.append(
        button(labelOf(row), () => inspect(row.id)),
        el('span', [row.code, row.scope_label, states[row.state] || row.state].filter(Boolean).join(' · ')),
      );
      list.append(li);
    }
    if (pages.length)
      pager.append(
        button('Trang trước', async () => {
          cursor = pages.pop();
          await reload();
        }),
      );
    if (result.next)
      pager.append(
        button('Trang sau', async () => {
          pages.push(cursor);
          cursor = result.next;
          await reload();
        }),
      );
    note(result.items.length ? '' : 'Chưa có kết quả.');
  }
  function values(data) {
    const obj = { ...data, ...data.placement, ...data.price, ...data.applicability };
    if (data.applicability?.unit) obj.quantity_unit = data.applicability.unit;
    if (data.applicability?.option) {
      for (const k of ['buyer', 'payment_type', 'service_level'])
        if (pick[k].includes(data.applicability.option)) obj[k] = data.applicability.option;
    }
    if (Array.isArray(obj.locales)) obj.locales = obj.locales.join(', ');
    return obj;
  }
  async function inspect(id) {
    const life = epoch,
      record = await get(collection(kind) + '/' + encodeURIComponent(id));
    if (!selected(life)) return;
    record.references ??= {};
    details.replaceChildren(el('h4', labelOf(record)));
    const lines = el('dl'),
      flat = values(record.data);
    for (const raw of forms[record.kind] || []) {
      const key = raw.replace('?', '');
      let v = record.references[key]?.label ?? flat[key];
      if (key === 'code') v = record.code;
      if (record.references[key]?.status === 'restricted') v = 'Quyền đọc hạn chế';
      if (v === null || v === undefined || v === '') v = 'Chưa có';
      if (Array.isArray(v)) v = v.map((x) => friendly[x] || x).join(', ') || 'Chưa có';
      lines.append(el('dt', titles[key]), el('dd', friendly[v] || v));
    }
    details.append(el('p', (states[record.state] || record.state) + ' · Phiên bản ' + record.revision), lines);
    if (record.identity === 'unmapped') details.append(el('p', 'Bản ghi cũ chưa có mã danh mục đã xác nhận.'));
    if (record.evidence_state === 'missing') details.append(el('p', 'Chưa liên kết chứng cứ.'));
    if (
      canWrite &&
      record.identity !== 'unmapped' &&
      !record.data.price?.unmapped_conditions?.length &&
      !Object.values(record.references).some((x) => x.status === 'restricted')
    )
      details.append(button('Chỉnh sửa', () => edit(record)));
    const allowed = {
      draft: ['approved', 'disputed', 'withdrawn'],
      approved: ['disputed', 'superseded', 'withdrawn'],
      disputed: ['withdrawn', 'superseded'],
      superseded: ['withdrawn'],
    };
    if (canApprove && allowed[record.state]) {
      const entry = el('div');
      entry.className = 'catalog-tools';
      const why = el('input');
      why.setAttribute('aria-label', 'Lý do quyết định');
      why.placeholder = 'Lý do quyết định';
      entry.append(why);
      const preferred = el('select');
      if (['availability', 'policy'].includes(record.kind) && allowed[record.state].includes('superseded')) {
        const holder = el('div');
        makeRow(holder, 'preferred_revision', preferred);
        entry.append(holder);
        guard(() => lookup(holder, 'preferred_revision', preferred, null, record.kind, record.id));
      }
      const decisionKeys = new Map();
      for (const state of allowed[record.state])
        entry.append(
          button(
            { approved: 'Duyệt', disputed: 'Ghi tranh chấp', superseded: 'Thay thế', withdrawn: 'Thu hồi' }[state],
            async () => {
              if (!why.value.trim()) {
                why.focus();
                return note('Nhập lý do quyết định.');
              }
              const preferredId = state === 'superseded' ? preferred.value : '';
              const intention = JSON.stringify([state, why.value.trim(), preferredId]);
              if (!decisionKeys.has(intention)) decisionKeys.set(intention, crypto.randomUUID());
              await api(
                (record.kind === 'company_objective' ? companyPath : path.replace(/\/catalog$/, '/knowledge') + '/revisions') + '/' + record.id + '/events',
                'POST',
                {
                  key: decisionKeys.get(intention),
                  state,
                  reason: why.value.trim(),
                  expected_sequence: record.sequence,
                  expected_digest: record.digest,
                  ...(preferredId ? { preferred_revision: preferredId } : {}),
                },
                false,
                controller.signal,
              );
              if (!selected(life)) return;
              await reload();
              await inspect(id);
              note('Đã ghi quyết định vào lịch sử.');
            },
          ),
        );
      details.append(entry);
    }
  }
  async function lookup(group, key, input, existing, lookupKind = null, excluded = null) {
    const life = epoch;
    let call = 0;
    const search = el('input');
    search.type = 'search';
    search.setAttribute('aria-label', 'Tìm ' + titles[key]);
    search.placeholder = 'Tìm theo tên';
    group.prepend(search);
    const load = async () => {
      const seq = ++call;
      let rows;
      if (refs[key] === 'company_objective') {
        rows = (await get(companyPath + '?' + new URLSearchParams({approved_only: 'true', q: search.value, limit: '40'}))).items;
      } else if (key === 'campaign_id') {
        const all = await get(clientRoot + '/campaigns');
        rows = all
          .filter(
            (r) =>
              r.brand_id === (scope?.brand?.id || scope?.brand) &&
              r.name.toLowerCase().includes(search.value.toLowerCase()),
          )
          .map((r) => ({ id: r.id, label: r.name }));
      } else {
        const wanted = key === 'product' ? ['product', 'service'] : [lookupKind || refs[key]],
          sets = await Promise.all(
            wanted.map((k) =>
              get(path + '/items?' + new URLSearchParams({ kind: k, q: search.value, limit: '40' })),
            ),
          );
        rows = sets.flatMap((s) => s.items);
        if (key === 'parent') {
          const level = form?.elements.namedItem('level')?.value;
          rows = rows.filter((r) => r.level === (level === 'campaign' ? 'brand' : 'company'));
        }
        if (key === 'preferred_revision') rows = rows.filter((r) => r.id !== excluded && r.state === 'approved');
      }
      if (!selected(life) || !input.isConnected || seq !== call) return;
      const prior = input.value || existing?.id;
      input.replaceChildren(new Option('Chọn theo tên', ''));
      for (const row of rows)
        input.add(new Option([labelOf(row), row.code, row.scope_label].filter(Boolean).join(' · '), row.id));
      if (prior && !rows.some((r) => r.id === prior) && existing?.id === prior)
        input.add(new Option(existing.label, prior));
      input.value = prior || '';
    };
    search.oninput = () => guard(load);
    await load();
  }
  function pack(raw) {
    const obj = { ...raw };
    delete obj.code;
    delete obj.visibility;
    const selectKeys = (keys, target) => {
      for (const k of keys)
        if (k in obj) {
          target[k] = obj[k];
          delete obj[k];
        }
    };
    if (['offer', 'policy', 'availability'].includes(kind)) {
      obj.placement = {};
      selectKeys(
        placement.map((k) => k.replace('?', '')),
        obj.placement,
      );
    }
    if (kind === 'offer') {
      obj.price = {};
      selectKeys(
        ['amount', 'currency', 'unit', 'basis_quantity', 'moq', 'tier_min', 'tier_max', 'tax', 'condition_ids'],
        obj.price,
      );
    }
    if (['policy', 'availability'].includes(kind)) {
      const a = {};
      selectKeys(['buyer', 'payment_type', 'service_level', 'minimum', 'maximum'], a);
      if (obj.quantity_unit) a.unit = obj.quantity_unit;
      delete obj.quantity_unit;
      if (Object.keys(a).length) obj.applicability = a;
    }
    if (kind === 'market')
      obj.locales = obj.locales
        .split(',')
        .map((v) => v.trim())
        .filter(Boolean);
    return obj;
  }
  async function edit(record = null) {
    const life = epoch;
    kind = record?.kind || kindSelect.value;
    details.replaceChildren(el('h4', (record ? 'Chỉnh sửa ' : 'Thêm ') + kinds[kind]));
    form = el('form');
    form.className = 'catalog-form';
    details.append(form);
    const v = record ? values(record.data) : {},
      controls = {},
      loads = [];
    for (const raw of kind === 'company_objective' ? forms[kind] : [...forms[kind], 'visibility']) {
      const optional = raw.endsWith('?'),
        key = raw.replace('?', '');
      let input;
      const box = el('div');
      form.append(box);
      let choices = key === 'quantity_unit' ? units : pick[key];
      if (key === 'unit' && kind === 'kpi') choices = null;
      if (refs[key] || key === 'campaign_id') {
        input = el('select');
        makeRow(box, key, input);
        loads.push(lookup(box, key, input, record?.references[key]));
      } else {
        if (key === 'condition_ids') {
          input = el('select');
          input.multiple = true;
          options(input, ['prepaid', 'cash_on_delivery', 'pickup', 'delivery']);
        } else if (choices) {
          input = el('select');
          options(
            input,
            choices.filter((x) => x !== 'restricted' || canApprove),
            optional,
          );
        } else {
          input = el(['description', 'guidance', 'needs', 'method'].includes(key) ? 'textarea' : 'input');
          if (['valid_from', 'valid_until', 'observed_at'].includes(key)) {
            input.type = 'datetime-local';
          }
          if (
            [
              'amount',
              'basis_quantity',
              'moq',
              'tier_min',
              'tier_max',
              'minimum',
              'maximum',
              'baseline',
              'target',
              'actual',
            ].includes(key)
          )
            input.inputMode = 'decimal';
        }
        makeRow(box, key, input);
      }
      controls[key] = input;
      input.name = key;
      input.required = !optional;
      let value = key === 'visibility' ? record?.visibility || 'internal' : key === 'code' ? record?.code : v[key];
      if (value != null) {
        if (input.multiple) {
          for (const o of input.options) o.selected = value.includes(o.value);
        } else if (input.type === 'datetime-local') {
          const d = new Date(value);
          input.value = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
          input.dataset.initialDisplay = input.value;
        } else if (!refs[key] && key !== 'campaign_id') input.value = value;
      }
      if (key === 'code' && record) input.readOnly = true;
    }
    if (kind === 'objective') {
      const scopeHint = el('p');
      scopeHint.id = 'catalog-objective-guidance';
      controls.level.setAttribute('aria-describedby', scopeHint.id);
      form.prepend(scopeHint);
      const adjust = () => {
        const level = controls.level.value;
        scopeHint.textContent = {
          company: 'Mục tiêu này chỉ dùng trong hồ sơ thương hiệu. Để các thương hiệu cùng dùng, chọn loại “Mục tiêu chung doanh nghiệp”.',
          brand: 'Chọn một mục tiêu chung đã duyệt hoặc một mục tiêu cha cũ trong hồ sơ thương hiệu.',
          campaign: 'Chọn chiến dịch và mục tiêu cha cấp thương hiệu của chiến dịch này.',
        }[level];
        for (const [key, active] of Object.entries({
          company_parent: level === 'brand', parent: level !== 'company', campaign_id: level === 'campaign',
        })) {
          controls[key].closest('.catalog-form > div').hidden = !active;
          if (!active) controls[key].value = '';
        }
        controls.parent.parentElement.parentElement.querySelector('input[type=search]').dispatchEvent(new Event('input'));
      };
      controls.level.addEventListener('change', adjust);
      adjust();
    }
    const submit = el('button', 'Lưu bản nháp');
    submit.type = 'submit';
    form.append(submit);
    form.onsubmit = (event) => {
      event.preventDefault();
      guard(async () => {
        const raw = {};
        for (const [key, input] of Object.entries(controls)) {
          let value = input.multiple ? [...input.selectedOptions].map((o) => o.value) : input.value.trim();
          if (value && input.type === 'datetime-local')
            value = value === input.dataset.initialDisplay ? v[key] : new Date(value).toISOString();
          if (value !== '' && value !== null) raw[key] = value;
        }
        if (kind === 'objective' && raw.level === 'brand' && Boolean(raw.parent) === Boolean(raw.company_parent))
          return note('Chọn đúng một mục tiêu cha cho thương hiệu.');
        if (kind === 'objective' && raw.level === 'campaign' && (!raw.campaign_id || !raw.parent))
          return note('Chọn chiến dịch và mục tiêu cha cấp thương hiệu.');
        if (kind === 'kpi' && Boolean(raw.objective) === Boolean(raw.company_objective))
          return note('Chọn đúng một mục tiêu để đo KPI.');
        const body = {
          ...(kind === 'company_objective' ? { name: raw.name, owner: raw.owner } : { kind, data: pack(raw), visibility: raw.visibility }),
          expected_revision: record?.revision || 0,
          ...(raw.code ? { code: raw.code } : {}),
          ...(record ? { subject: record.subject } : {}),
        };
        const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(body)));
        if (!selected(life)) return;
        const fp = [...new Uint8Array(bytes)].map((x) => x.toString(16).padStart(2, '0')).join('');
        const old = sessionStorage.getItem(actorKey + '/pending');
        const key = old && sessionStorage.getItem(actorKey + '/digest') === fp ? old : crypto.randomUUID();
        sessionStorage.setItem(actorKey + '/pending', key);
        sessionStorage.setItem(actorKey + '/kind', kind);
        sessionStorage.setItem(actorKey + '/digest', fp);
        submit.disabled = true;
        try {
          const saved = await api(collection(kind), 'POST', { ...body, key }, false, controller.signal);
          if (!selected(life)) return;
          sessionStorage.removeItem(actorKey + '/pending');
          await reload();
          await inspect(saved.id);
          note('Đã lưu bản nháp.');
        } finally {
          if (selected(life)) submit.disabled = false;
        }
      });
    };
    await Promise.all(loads);
  }
  return { show, reset };
}
