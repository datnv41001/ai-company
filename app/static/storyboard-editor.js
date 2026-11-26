/* All editable controls are proposals. The Workforce API reconstructs each accepted revision. */
window.storyboardEditor = (() => {
  const purposes = {hook:"Mở đầu", proof:"Bằng chứng", terms:"Điều khoản", conditions:"Điều kiện", action:"Kêu gọi hành động"};
  const unchanged = ["", "Giữ nguyên"];
  function element(parent, tag, text) {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    parent.append(item);
    return item;
  }
  function field(parent, title, name, tag, options) {
    const label = element(parent, "label", title);
    const input = element(label, tag);
    input.name = name;
    for (const [value, caption] of options || []) element(input, "option", caption).value = value;
    return input;
  }
  function cell(parent) {
    const grid = element(parent, "div");
    grid.className = "board-field-grid";
    return grid;
  }
  function numbers(value) {
    if (!/^\s*\d+(\s*,\s*\d+)*\s*$/.test(value)) throw new Error("Dùng số nguyên, ngăn cách bằng dấu phẩy.");
    return value.split(",").map(Number);
  }
  function draw(panel, record, save, message) {
    panel.replaceChildren();
    element(panel, "summary", "Biên tập storyboard");
    const status = element(panel, "p", message || ("Phiên bản " + record.revision + " · " + record.storyboard.product));
    status.dataset.boardStatus = "";
    status.tabIndex = -1;
    status.setAttribute("role", "status");
    const board = record.storyboard;
    const form = element(panel, "form");
    const first = cell(form);
    const mode = field(first, "Cách biên tập", "mode", "select", [["editorial","Sửa bản giao"], ["controlled_hook","Thử riêng câu mở"]]);
    const hooks = [unchanged, ["direct","Mở trực tiếp"], ["audience","Hỏi người xem"], ["product_question","Hỏi về sản phẩm"], ["observation","Gợi quan sát"]];
    if (board.version === "amc.storyboard/2") hooks.push(["style_alternate","Đổi câu cùng phong cách brief"]);
    const hook = field(first, "Câu mở", "hook_variant", "select", hooks);
    element(form, "p", "Câu hiện tại · " + board.hook).className = "board-current-hook";
    const hold = element(form, "p", "Khóa thân bài, thời lượng từng cảnh, hình, CTA và offer. Hai bản cùng ở chế độ ngoại tuyến, chưa phân phối hoặc gắn trang đích.");
    hold.hidden = true;
    const editorial = element(form, "div");
    const shotSelect = field(editorial, "Cảnh cần sửa", "shot", "select", board.shots.map((s, i) => [
      String(i + 1), (i + 1) + " · " + (purposes[s.purpose] || s.purpose) + " · " + s.start_s + "–" + s.end_s + " giây",
    ]));
    const scenes = board.shots.map((s, i) => {
      const scene = element(editorial, "div");
      scene.className = "board-shot";
      scene.hidden = i !== 0;
      element(scene, "p", s.visual);
      const grid = cell(scene);
      const framing = field(grid, "Chỉ dẫn khung hình", "framing", "select", [
        unchanged, ["detail","Cận chi tiết"], ["wide","Toàn cảnh"], ["hold","Giữ khung"], ["original","Chỉ dẫn gốc"],
      ]);
      let spoken, lead;
      if (s.purpose === "proof") {
        spoken = field(grid, "Lời dẫn nói", "narration", "select", [unchanged, ["as_caption","Đọc caption"], ["look","Hãy xem."], ["listen","Lưu ý."]]);
        lead = field(scene, "Dẫn vào thẻ bằng chứng", "proof_lead", "select", [unchanged, ["none","Chỉ đọc dữ kiện"], ["observe","Quan sát."], ["read","Đọc thẻ."]]);
      }
      const caption = field(scene, "Caption · giữ đủ từ khi ngắt dòng", "caption", "textarea");
      caption.rows = 2; caption.maxLength = 79; caption.value = s.caption;
      return {scene, framing, spoken, lead, caption};
    });
    shotSelect.onchange = () => scenes.forEach((s, i) => { s.scene.hidden = i !== Number(shotSelect.value) - 1; });
    const layout = element(editorial, "details");
    element(layout, "summary", "Thời lượng và thứ tự cảnh");
    const timeline = cell(layout);
    const order = field(timeline, "Thứ tự · số cảnh cách nhau bằng dấu phẩy", "shot_order", "input");
    const times = field(timeline, "Số giây theo thứ tự trên", "durations", "input");
    const originalOrder = board.shots.map((_,i) => i + 1).join(", ");
    const originalTimes = board.shots.map(s => s.end_s - s.start_s).join(", ");
    order.value = originalOrder; times.value = originalTimes;
    const note = field(editorial, "Ghi chú cho người dựng", "editor_note", "textarea");
    note.maxLength = 300; note.rows = 2; note.value = board.editorial.editor_note || "";
    const submit = element(form, "button", "Lưu phiên bản");
    submit.type = "submit"; submit.dataset.boardSave = "";
    mode.onchange = () => {
      editorial.hidden = mode.value === "controlled_hook";
      hold.hidden = !editorial.hidden;
      hook.required = editorial.hidden;
    };
    form.onsubmit = async event => {
      event.preventDefault();
      if (submit.disabled) return;
      const body = {expected_qa_revision: record.revision, expected_content_digest: record.content_digest, mode: mode.value};
      if (hook.value) body.hook_variant = hook.value;
      submit.disabled = true;
      try {
        if (mode.value === "editorial") {
          const edits = [];
          scenes.forEach(({framing, spoken, lead, caption}, i) => {
            const edit = {shot: i + 1};
            if (framing.value) edit.framing = framing.value;
            if (spoken?.value) edit.narration = spoken.value;
            if (lead?.value) edit.proof_lead = lead.value;
            if (caption.value !== board.shots[i].caption) edit.caption = caption.value;
            if (Object.keys(edit).length > 1) edits.push(edit);
          });
          if (edits.length) body.shot_edits = edits;
          if (order.value !== originalOrder) body.shot_order = numbers(order.value);
          if (times.value !== originalTimes) body.durations = numbers(times.value);
          if (note.value !== (board.editorial.editor_note || "")) body.editor_note = note.value;
          if (Object.keys(body).length === 3) throw new Error("Chọn ít nhất một thay đổi để lưu.");
        }
        await save(body);
      } catch (err) {
        status.textContent = err.message; status.focus();
      } finally {
        submit.disabled = false;
      }
    };
    if (message) status.focus();
  }

  async function mount(parent, {run, tenantId, api}) {
    const panel = element(parent, "details");
    panel.dataset.boardEditor = "";
    panel.className = "storyboard-editor";
    panel.hidden = true;
    const path = "/api/tenants/" + encodeURIComponent(tenantId) + "/workforce/runs/" + encodeURIComponent(run.id) + "/storyboard-edition";
    function denied(err) {
      if (![401,403,404].includes(err.status)) return false;
      panel.remove();
      return true;
    }
    async function load(message) {
      try {
        const record = await api(path);
        if (!panel.isConnected) return;
        panel.hidden = false;
        draw(panel, record, save, message);
      } catch (err) {
        if (denied(err) || !panel.isConnected) return;
        panel.replaceChildren(); panel.hidden = false;
        element(panel, "summary", "Biên tập storyboard");
        element(panel, "p", err.message).setAttribute("role", "status");
        element(panel, "button", "Tải lại bản hiện hành").onclick = () => load();
      }
    }
    async function save(body) {
      try {
        const next = await api(path, "POST", body);
        if (panel.isConnected) draw(panel, next, save, "Đã lưu phiên bản " + next.revision + ". Bản sửa đang chờ gửi QA.");
      } catch (err) {
        if (denied(err)) return;
        if (err.status === 412) await load("Đã tải lại bản hiện hành. Hãy đối chiếu và nhập lại thay đổi.");
        else throw err;
      }
    }
    await load();
  }
  return {mount};
})();
