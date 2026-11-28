/* Scoped internal Studio. Every save and QA decision is checked against its displayed edition. */
let guideFieldSequence = 0;
function mountProductGuide(parent, api, documentPath) {
  const panel = document.createElement('section');
  panel.className = 'product-guide-studio';
  panel.setAttribute('aria-label', 'Studio hướng dẫn sử dụng');
  parent.append(panel);
  const path = documentPath + '/studio/product-guide';
  let generation = 0;

  function add(host, tag, value) {
    const el = document.createElement(tag);
    if (value !== undefined) el.textContent = value;
    host.append(el);
    return el;
  }

  function action(host, text, fn) {
    const button = add(host, 'button', text);
    button.type = 'button';
    button.addEventListener('click', async () => {
      if (button.disabled) return;
      button.disabled = true;
      try { await fn(); }
      catch (err) { if (button.isConnected) failed(err); }
      finally { if (button.isConnected) button.disabled = false; }
    });
    return button;
  }

  function failed(err) {
    generation++;
    panel.replaceChildren();
    const notice = add(panel, 'p', [403, 404, 409, 412].includes(err.status)
      ? 'Quyền, nguồn hoặc phiên bản của hướng dẫn đã thay đổi. Tải lại để kiểm tra.' : err.message);
    notice.setAttribute('role', 'alert');
    action(panel, 'Tải lại hướng dẫn', load);
  }

  function choices(host, label, values, selected) {
    const select = add(add(host, 'label', label), 'select');
    select.setAttribute('aria-label', label);
    for (const [value, text] of Object.entries(values)) select.add(new Option(text, value));
    select.value = selected;
    return select;
  }

  function preview(host, edition, title, layout) {
    host.replaceChildren();
    const article = add(host, 'article');
    article.className = 'guide-component';
    article.lang = edition.locale;
    const vi = edition.locale === 'vi-VN';
    article.setAttribute('aria-label', 'Bản xem trước trên trang sản phẩm');
    add(article, 'h4', title);
    add(article, 'p', (vi ? 'Dành cho ' : 'For ') + edition.audience).className = 'guide-audience';
    add(article, 'p', edition.use_case);
    add(article, 'h5', vi ? 'Cách sử dụng' : 'How to use');
    const list = add(article, layout === 'checklist' ? 'ul' : 'ol');
    list.className = layout === 'checklist' ? 'guide-checklist' : 'guide-steps';
    for (const step of edition.steps) add(list, 'li', step);
    if (edition.limitations.length) {
      const limits = add(article, 'section');
      limits.className = 'guide-limitations';
      add(limits, 'h5', vi ? 'Điều kiện sử dụng' : 'Conditions of use');
      for (const text of edition.limitations) add(limits, 'p', text);
    }
    if (edition.wording !== [...edition.steps, ...edition.limitations].join(' ')) add(article, 'p', edition.wording);
    add(article, 'p', edition.cta).className = 'guide-cta';
  }

  function render(view) {
    panel.replaceChildren();
    const edition = view.guide;
    const states = {draft:'Bản nháp',submitted:'Chờ QA độc lập',approved:'QA nội bộ đã duyệt',changes_requested:'Cần sửa',rejected:'QA đã từ chối'};
    add(panel, 'h3', 'Hướng dẫn trên trang sản phẩm');
    const state = add(panel, 'p', (states[view.status] || view.status) + ' · Phiên bản ' + view.revision);
    state.setAttribute('role', 'status');
    const grid = add(panel, 'div');
    grid.className = 'guide-grid';
    const column = add(grid, 'div');
    const sample = add(grid, 'div');
    let h = edition.choices.heading;
    let l = edition.choices.layout;
    let displayTitle = edition.title;
    const draw = () => preview(sample, edition, displayTitle, l);
    const controls = add(column, 'section');
    if (view.can_edit) {
      add(controls, 'h4', 'Biên tập hướng dẫn');
      const heading = add(add(controls, 'label', 'Tiêu đề'), 'input');
      heading.value = edition.title;
      heading.maxLength = 160;
      const id = 'guide-title-'+(++guideFieldSequence);
      const options = add(controls, 'datalist');
      options.id = id;
      heading.setAttribute('list', id);
      for (const value of [...Object.values(view.titles), ...view.source_titles]) options.append(new Option(value,value));
      const hint = add(controls, 'small', 'Có thể dùng nguyên văn một bước đã duyệt làm tiêu đề. Danh sách gợi ý có các tiêu đề phù hợp.');
      hint.id = id+'-hint';
      heading.setAttribute('aria-describedby', hint.id);
      const layout = choices(controls, 'Cách trình bày các bước', {numbered:'Các bước đánh số',checklist:'Danh sách kiểm tra'}, l);
      const buttons = add(controls, 'div');
      buttons.className = 'guide-actions';
      const save = action(buttons, 'Lưu phiên bản', async () => {
        const updated = await api(path,'PATCH',{heading:h,layout:l,...(h==='source'?{custom_title:heading.value}:{}),
          expected_qa_revision:view.revision,expected_content_digest:view.content_digest});
        if (panel.isConnected) render(updated);
      });
      save.disabled = true;
      const submit = view.status === 'draft' ? action(buttons, 'Gửi QA độc lập', async () => {
        await api(documentPath+'/submit','POST',{expected_qa_revision:view.revision,expected_content_digest:view.content_digest});
        await load();
      }) : null;
      function changed() {
        h = Object.keys(view.titles).find(key => view.titles[key] === heading.value) || 'source';
        const valid = h !== 'source' || view.source_titles.includes(heading.value);
        if (valid) displayTitle = heading.value;
        heading.setAttribute('aria-invalid', String(!valid));
        l = layout.value;
        const dirty = heading.value !== edition.title || l !== edition.choices.layout;
        save.disabled = !dirty || !valid;
        if (submit) submit.disabled = dirty || !valid;
        state.textContent = !valid ? 'Tiêu đề chưa khớp nguồn. Nhập nguyên văn một bước hoặc chọn tiêu đề trong danh sách.'
          : dirty ? 'Có thay đổi chưa lưu · Phiên bản '+view.revision : (states[view.status] || view.status)+' · Phiên bản '+view.revision;
        draw();
      }
      layout.addEventListener('change', changed);
      heading.addEventListener('input', changed);
    }

    const source = add(column, 'details');
    source.className = 'guide-source';
    add(source, 'summary', 'Đối chiếu nguồn của hướng dẫn');
    add(source, 'blockquote', edition.wording);
    const refs = add(source, 'ul');
    if (edition.source_map.title === 'P1') add(refs, 'li', 'Tiêu đề · P1');
    edition.source_map.steps.forEach((ref, index) => add(refs, 'li', 'Bước '+(index+1)+' · '+ref));
    add(source, 'p', 'Đối tượng và lời kêu gọi hành động lấy từ brief đã duyệt.');
    if (view.qa_receipt) add(source, 'p', 'Biên nhận QA cho phiên bản '+view.revision+' · '+view.qa_receipt);
    if (view.can_review) {
      const form = add(column, 'form');
      add(form, 'h4', 'Quyết định Content QA');
      const decision = choices(form, 'Kết luận', {approved:'Duyệt nội bộ',rejected:'Từ chối'}, 'approved');
      const note = add(add(form, 'label', 'Nhận xét đối chiếu nguồn'), 'textarea');
      note.required = true;
      note.minLength = 5;
      note.maxLength = 1000;
      const submit = add(form, 'button', 'Ghi quyết định QA');
      submit.type = 'submit';
      form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity() || submit.disabled) return;
        submit.disabled = true;
        try {
          await api(documentPath+'/review','POST',{expected_qa_revision:view.revision,expected_content_digest:view.content_digest,
            decision:decision.value,note:note.value.trim()});
          await load();
        } catch (err) { if (panel.isConnected) failed(err); }
      });
    }
    draw();
    action(column, 'Kiểm tra lại phiên bản', load);
  }

  async function load() {
    const ticket = ++generation;
    panel.replaceChildren();
    add(panel, 'p', 'Đang kiểm tra nguồn và quyền hiện tại…').setAttribute('role','status');
    try {
      const view = await api(path);
      if (ticket === generation && panel.isConnected) render(view);
    } catch (err) { if (ticket === generation && panel.isConnected) failed(err); }
  }
  load();
}
