/* An internal Content assignment is always read back from the scoped Studio endpoint. */
function mountStrategyHandoff(parent, api, path, dirty) {
  function add(target, tag, text) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    target.append(node);
    return node;
  }
  const statusLabels = {
    needs_review: 'Chờ QA bản đã lưu', needs_decision: 'Chờ quyết định chiến lược',
    hold: 'Tạm giữ bàn giao', draft_for_approval: 'Được lập bản nháp nội bộ'
  };
  const reasonLabels = {
    save_and_approve: 'Lưu bản biên tập, duyệt từng phần và hoàn tất QA cho đúng phiên bản.',
    independent_reviewer_required: 'Cần người duyệt độc lập với tác giả và người sửa bản hiện tại.',
    current_authority_required: 'Xác nhận lại quyền dùng nguồn và thẩm quyền phê duyệt hiện tại.',
    qualified_decision_required: 'Người có thẩm quyền cần ghi quyết định dựa trên nguồn.',
    qualification_withdrawn: 'Kiểm lại ủy quyền của người duyệt trước khi giao việc.',
    contradictory_evidence: 'Đối chiếu hai nguồn trái chiều với người phụ trách nghiên cứu.',
    conflicting_source: 'Giải quyết bằng chứng trái chiều trước khi chọn phương án.',
    missing_evidence: 'Bổ sung căn cứ cho quyết định.', clarify_commission: 'Làm rõ đối tượng và tình huống mua trong brief.',
    missing_product_fact: 'Chọn dữ kiện sản phẩm được phép dùng nguyên văn và đủ điều kiện.',
    asset_placement_mismatch: 'Chọn tài sản có quyền dùng đúng vị trí đã duyệt.',
    asset_option_mismatch: 'Đối chiếu loại tài sản với mục đích của phương án.',
    missing_observation: 'Bổ sung nguồn quan sát trực tiếp đúng đối tượng.',
    source_purpose_mismatch: 'Kiểm tra mục đích sử dụng của nguồn được chọn.',
    buyer_scope_mismatch: 'Đối chiếu đối tượng với phạm vi brief đã ghim.',
    strategy_placement_mismatch: 'Sửa kênh của Strategy cho khớp vị trí được phép, rồi duyệt lại.',
    recipient_required: 'Chọn một người nhận Content đang có quyền trong phạm vi này.',
    recipient_authority_required: 'Kiểm tra lại quyền hiện tại của người nhận đã chỉ định.',
    recipient_only: 'Chuyển phiếu cho người nhận Content được chỉ định.',
    observation_unverified: 'Đối chiếu loại bằng chứng và trích nguyên văn đoạn quan sát.',
    asset_required: 'Xác định tài sản và vị trí được phép trước khi giao việc cho Content.',
  };
  const outcomes = {
    supported: 'Có căn cứ cho đề xuất', conflicting: 'Nguồn trái chiều',
    insufficient: 'Thiếu bằng chứng', needs_clarification: 'Cần làm rõ nhiệm vụ'
  };
  const roleLabels = {
    'Content lead': 'Phụ trách Content', 'Marketing lead': 'Trưởng Marketing',
    'Independent QA': 'QA độc lập', 'Research lead': 'Phụ trách Research',
    'Studio editor and independent QA': 'Biên tập viên Studio và QA độc lập',
    'Independent Marketing reviewer': 'Người duyệt Marketing độc lập',
    'Knowledge owner and independent QA': 'Chủ nguồn và QA độc lập',
    'Knowledge owner and qualified reviewer': 'Chủ nguồn và người duyệt có ủy quyền',
    'Qualified Marketing reviewer': 'Người duyệt Marketing có ủy quyền',
    'Strategy editor and knowledge owner': 'Biên tập viên Strategy và chủ nguồn'
  };
  function role(value) { return roleLabels[value] || value; }
  const optionLabels = {explain_use:'Giải thích cách sử dụng', explain_terms:'Làm rõ điều kiện mua'};
  const assetLabels = {web_use_guide:'Hướng dẫn sử dụng trên trang sản phẩm', web_terms_panel:'Khối thông tin điều kiện mua trên web',
    counter_use_card:'Thẻ minh họa cách dùng tại quầy', counter_terms_card:'Thẻ thông tin điều kiện mua tại quầy'};
  const concepts = {'Prepare an internal outline of the buyer situation and questions for review.':
    'Phác dàn ý về tình huống của người mua và những câu hỏi cần đối chiếu.',
    'Explain the product in use':'Phác cách giải thích tình huống sử dụng sản phẩm.',
    'Clarify the offer before purchase':'Chuẩn bị dàn ý giải thích điều kiện mua.'};
  const panel = add(parent, 'details');
  panel.className = 'strategy-handoff';
  const summary = add(panel, 'summary', 'Bàn giao từ Strategy cho Content');
  const content = add(panel, 'div');
  let sequence = 0;
  function field(list, name, value) {
    if (value === null || value === undefined || value === '') return;
    const entry = add(list, 'div');
    add(entry, 'dt', name);
    add(entry, 'dd', value);
  }
  function lines(target, values) {
    const list = add(target, 'ul');
    for (const value of values) add(list, 'li', value);
  }
  function button(target, text, action) {
    const b = add(target, 'button', text);
    b.type = 'button';
    b.addEventListener('click', action);
    return b;
  }
  function message(target, text, error=false) {
    const node = add(target, 'p', text);
    node.setAttribute('role', error ? 'alert' : 'status');
    node.className = error ? 'strategy-error' : 'strategy-status';
    return node;
  }
  function errorMessage(error) {
    if (error.status === 404 || error.status === 403) return 'Phiếu hiện không có trong phạm vi truy cập của bạn.';
    if (error.status === 409 || error.status === 412) return 'Phiên bản, quyền hoặc điều kiện duyệt đã thay đổi. Tải lại phiếu để đối chiếu.';
    return error.message || 'Chưa tải được phiếu bàn giao.';
  }
  function show(view) {
    content.replaceChildren();
    const banner = add(content, 'section');
    banner.className = 'strategy-verdict';
    banner.dataset.status = view.status;
    const heading = add(banner, 'h4', statusLabels[view.status] || 'Kiểm tra điều kiện bàn giao');
    heading.tabIndex = -1;
    add(banner, 'p', 'Bản Studio v' + view.revision + (view.placement ? ' · '+view.placement : ''));
    const order = view.work_order;
    if (order) {
      const assignment = add(content, 'section');
      assignment.className = 'strategy-assignment';
      add(assignment, 'h5', 'Việc được giao cho Content');
      const list = add(assignment, 'dl');
      field(list, 'Người nhận', role(order.recipient)); field(list, 'Tài sản', assetLabels[order.asset_type] || order.asset);
      field(list, 'Mục đích', order.purpose); field(list, 'Vị trí', order.placement);
      field(list, 'Đối tượng', order.buyer_persona || order.audience); field(list, 'Mục tiêu', order.objective);
      field(list, 'Thông điệp', order.message);
      field(list, 'Phê duyệt tiếp theo', order.approval);
      if (order.claim_limits?.length) { add(assignment, 'strong', 'Giới hạn khi viết'); lines(assignment, order.claim_limits); }
    } else {
      add(banner, 'p', 'Tạm giữ việc giao tài sản theo kênh.');
    }
    const next = add(content, 'section');
    next.className = 'strategy-next';
    add(next, 'h5', 'Bước tiếp theo');
    if (view.reasons?.length) lines(next, view.reasons.map(r => reasonLabels[r] || r));
    const actions = add(next, 'dl');
    field(actions, 'Người xử lý', role(view.next_owner));
    if (view.internal_concept) field(actions, 'Có thể chuẩn bị nội bộ', concepts[view.internal_concept] || view.internal_concept);
    field(actions, 'Đo lường', view.measurement_status === 'approved_definition_only' ? 'Đã duyệt định nghĩa chỉ số; chờ quyền thực hiện phép đo.' : 'Chưa có hợp đồng đo lường được duyệt');
    field(actions, 'Thực thi', 'Xuất bản, thử nghiệm và chi ngân sách cần phê duyệt riêng.');
    if (view.permitted_product_wording?.length) {
      add(next, 'strong', 'Dữ kiện được phép dùng'); lines(next, view.permitted_product_wording);
    }

    if (view.research?.buyer_problem || view.strategy?.positioning || view.references?.length) {
      const research = add(content, 'details');
      add(research, 'summary', 'Research, Strategy và nguồn của bản này');
      const review = add(research, 'dl');
      field(review, 'Vấn đề người mua', view.research?.buyer_problem);
      field(review, 'Câu hỏi nghiên cứu', view.research?.research_question);
      field(review, 'Giả thuyết', view.research?.hypothesis);
      field(review, 'Ghi nhận trong bản Research', view.research?.evidence);
      field(review, 'Định vị đề xuất', view.strategy?.positioning);
      field(review, 'Lý do lựa chọn', view.strategy?.rationale);
      field(review, 'Kênh đề xuất', view.strategy?.channel_choice);
      field(review, 'Cách triển khai', view.strategy?.execution);
      for (const choice of view.options || []) field(review, optionLabels[choice.id] || choice.label, choice.tradeoff);
      for (const ref of view.references || []) {
        const source = add(research, 'article');
        add(source, 'h6', 'Nguồn ' + ref.handle);
        add(source, 'blockquote', ref.excerpt || ref.statement);
        if (ref.publisher) add(source, 'p', 'Đơn vị cung cấp nguồn · ' + ref.publisher);
        if (ref.qualifiers?.length) lines(source, ref.qualifiers);
        if (ref.source_revision) add(source, 'small', 'Revision nguồn · ' + ref.source_revision);
        if (ref.locator) add(source, 'p', 'Vị trí đoạn căn cứ · ' + ref.locator);
        if (ref.recorded_at) add(source, 'small', 'Ghi nhận · ' + ref.recorded_at);
        if (ref.permitted_use) add(source, 'p', 'Phạm vi sử dụng · ' + ref.permitted_use);
        if (ref.effective_until) add(source, 'small', 'Có hiệu lực đến · ' + ref.effective_until);
      }
    }
    if (view.provenance?.brief_id) {
      const lineage = add(content, 'details');
      add(lineage, 'summary', 'Đề xuất của worker và dấu vết QA');
      const record = add(lineage, 'dl');
      field(record, 'Brief', view.provenance?.brief_id); field(record, 'Lượt Workforce', view.provenance?.run_id);
      field(record, 'Bản đã duyệt', view.provenance?.final_qa_digest);
      field(record, 'Receipt QA', view.provenance?.qa_receipt); field(record, 'Người QA', view.provenance?.final_reviewer);
      field(record, 'Đề xuất vấn đề người mua của Research', view.provenance?.worker_proposals?.research?.buyer_problem);
      field(record, 'Đề xuất định vị của Strategy', view.provenance?.worker_proposals?.strategy?.positioning);
    }
    if (view.decision) {
      const decision = add(content, 'details');
      add(decision, 'summary', 'Quyết định đã ghi và người xác nhận');
      const facts = add(decision, 'dl');
      const d = view.decision;
      field(facts, 'Kết luận', outcomes[d.evidence_state] || d.evidence_state);
      field(facts, 'Diễn giải đã kiểm', d.interpretation); field(facts, 'Đối tượng', d.buyer_persona);
      field(facts, 'Tình huống mua', d.buying_situation); field(facts, 'Giới hạn mẫu', d.sample_limit);
      field(facts, 'Người xác nhận', d.actor); field(facts, 'Receipt', d.receipt_id);
      field(facts, 'Thời điểm ghi nhận', d.at);
      field(facts, 'Phương án', optionLabels[d.option] || d.option);
      field(facts, 'Tài sản đã đối chiếu', assetLabels[d.asset_type] || d.asset_type);
      field(facts, 'Nguồn quan sát', d.support_handle); field(facts, 'Nguồn trái chiều', d.contrary_handle);
      field(facts, 'Nguồn dữ kiện sản phẩm', d.product_handle);
      field(facts, 'Trích đoạn đã đối chiếu', d.observation_excerpt);
    }
    if (view.can_decide && !view.decision) decisionForm(view);
    button(content, 'Tải lại phiếu bàn giao', () => load(true));
    return heading;
  }
  function decisionForm(view) {
    const form = add(content, 'form');
    form.className = 'strategy-decision-form';
    add(form, 'h5', 'Ghi quyết định trên bản đã QA');
    const grid = add(form, 'div');
    grid.className = 'strategy-form-grid';
    function control(title, tag) {
      const label = add(grid, 'label', title);
      return add(label, tag);
    }
    function choices(title, rows, required=true) {
      const select = control(title, 'select');
      select.required = required;
      select.add(new Option(required ? 'Chọn…' : 'Chưa chọn', ''));
      for (const [id, label] of rows) select.add(new Option(label, id));
      return select;
    }
    function input(title, value='') {
      const node = control(title, 'textarea');
      node.rows = 2;
      node.required = true;
      node.minLength = 3;
      node.maxLength = 500;
      node.value = value;
      return node;
    }
    const state = choices('Kết luận về căn cứ', Object.entries(outcomes));
    const mandate = choices('Ủy quyền phê duyệt', view.qualifications.map(q => [q.id, (q.category || 'Ủy quyền')+' · '+q.id]));
    const recipient = choices('Người nhận việc Content', (view.recipients || []).map(r => [r.id, r.role+' · '+r.id]), false);
    const option = choices('Phương án chiến lược', view.options.map(o => [o.id, optionLabels[o.id] || o.label]));
    const tradeoff = add(grid, 'p');
    tradeoff.className = 'strategy-tradeoff'; tradeoff.setAttribute('aria-live', 'polite');
    const asset = choices('Tài sản được đề nghị', [], false);
    function assets() {
      const selected = view.options.find(o => o.id === option.value);
      tradeoff.textContent = selected?.tradeoff || '';
      asset.options.length = 1;
      for (const a of view.assets.filter(a => a.option === option.value)) {
        asset.add(new Option((assetLabels[a.id] || a.label) + ' · ' + a.placement, a.id));
      }
    }
    option.addEventListener('change', assets);
    const referenceChoices = rows => rows.map(r => [r.handle, r.handle+' · '+r.statement]);
    const researchSources = view.references.filter(r => r.category === 'description' && r.research_spans?.length);
    const productSources = view.references.filter(r => r.category === 'description' && r.positioning_spans?.length && !r.research_spans?.length);
    const support = choices('Quan sát làm căn cứ', referenceChoices(researchSources), false);
    const observation = choices('Loại bằng chứng quan sát', [
      ['observed_behaviour', 'Hành vi đã quan sát'], ['buyer_statement', 'Lời người mua'], ['hypothesis', 'Giả thuyết']
    ]);
    observation.value = 'hypothesis';
    const excerpt = input('Trích nguyên văn đoạn quan sát');
    excerpt.required = false;
    excerpt.maxLength = 1800;
    const contrary = choices('Nguồn trái chiều', referenceChoices(view.references), false);
    const product = choices('Nguồn dữ kiện sản phẩm', referenceChoices(productSources), false);
    if (!researchSources.length || !productSources.length) {
      add(form, 'p', 'Để lập bản nháp, liên kết vấn đề người mua trong Research với quan sát và định vị trong Strategy với một dữ kiện sản phẩm riêng. Lưu và gửi QA độc lập cho bản sửa.');
    }
    const persona = input('Người có quyết định mua', view.audience || '');
    const situation = input('Tình huống mua');
    const interpretation = input('Diễn giải đối chiếu với nguồn');
    const limit = input('Giới hạn mẫu và khả năng suy rộng');
    const notice = message(form, '');
    const submit = add(form, 'button', 'Ghi quyết định nội bộ');
    submit.type = 'submit';
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (dirty()) {notice.textContent = 'Hãy lưu bản đang biên tập và tải lại phiếu trước khi ghi quyết định.'; return;}
      const payload = {expected_revision:view.revision, expected_content_digest:view.content_digest,
        qualification_revision:mandate.value, option:option.value, asset_type:asset.value || null, evidence_state:state.value,
        support_handle:support.value || null, contrary_handle:contrary.value || null, product_handle:product.value || null,
        recipient_id:recipient.value || null, observation_kind:observation.value, observation_excerpt:excerpt.value || null,
        interpretation:interpretation.value, buyer_persona:persona.value, buying_situation:situation.value, sample_limit:limit.value};
      submit.disabled = true;
      const ticket = ++sequence;
      notice.textContent = 'Đang ghi quyết định…';
      try {
        await api(path, 'POST', payload);
        if (current(ticket)) await load(true);
      } catch (error) {
        if (!current(ticket)) return;
        if (error.status === 403 || error.status === 404) return failed(error);
        notice.textContent = errorMessage(error);
        submit.disabled = false;
      }
    });
  }
  function current(ticket) {return panel.isConnected && panel.open && ticket === sequence;}
  function failed(error) {
    content.replaceChildren();
    message(content, errorMessage(error), true);
    button(content, 'Tải lại phiếu bàn giao', () => load(true));
  }
  async function load(focus=false) {
    const ticket = ++sequence;
    content.replaceChildren();
    message(content, 'Đang kiểm tra bản đã lưu và quyền hiện tại…');
    try {
      const response = await api(path);
      if (current(ticket)) {
        const heading = show(response);
        if (focus) heading.focus();
      }
    } catch (error) {
      if (current(ticket)) failed(error);
    }
  }
  panel.addEventListener('toggle', () => {
    if (panel.open) load();
    else {sequence++; content.replaceChildren();}
  });
  return summary;
}
