// Theme is the only persistent UI preference. No account or workspace identifier is stored.
(() => {
  const key = 'amc.color-mode';
  const query = window.matchMedia('(prefers-color-scheme: dark)');
  const mode = value => ['light','dark','system'].includes(value) ? value : 'system';
  let preference = 'system';
  try { preference = mode(localStorage.getItem(key)); } catch { /* Session-only preference. */ }
  const apply = () => {
    document.documentElement.dataset.theme = preference === 'system' ? (query.matches ? 'dark' : 'light') : preference;
    const control = document.getElementById('theme-mode');
    if (control) control.value = preference;
  };
  apply();
  query.addEventListener('change', apply);
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) { preference = mode(event.newValue); apply(); }
  });
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    document.getElementById('theme-mode').addEventListener('change', event => {
      preference = mode(event.target.value);
      try { localStorage.setItem(key, preference); } catch { /* Keep the current selection in memory. */ }
      apply();
    });
    const toggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('workspace-sidebar');
    const shade = document.getElementById('nav-backdrop');
    const mobile = matchMedia('(max-width: 900px)');
    function close(returnFocus = false) {
      toggle.setAttribute('aria-expanded','false');
      document.body.classList.remove('drawer-open');
      sidebar.inert = mobile.matches;
      shade.hidden = true;
      if (returnFocus) toggle.focus();
    }
    function open() {
      sidebar.inert = false;
      toggle.setAttribute('aria-expanded','true');
      document.body.classList.add('drawer-open');
      shade.hidden = false;
      [...sidebar.querySelectorAll('a[href]')].find(link=>link.getClientRects().length)?.focus();
    }
    toggle.addEventListener('click', () => toggle.getAttribute('aria-expanded') === 'true' ? close(true) : open());
    shade.addEventListener('click', () => close(true));
    document.getElementById('menu-close').addEventListener('click', () => close(true));
    const rail = document.getElementById('rail-toggle');
    rail.addEventListener('click',()=>{
      const collapsed=document.body.classList.toggle('rail-compact');
      rail.setAttribute('aria-expanded',String(!collapsed));
      rail.setAttribute('aria-label',collapsed?'Mở rộng thanh điều hướng':'Thu gọn thanh điều hướng');
    });
    for(const id of ['account','scope']){
      const trigger=document.getElementById(id+'-trigger'), menu=document.getElementById(id+'-menu');
      trigger.setAttribute('aria-controls',menu.id);trigger.setAttribute('aria-expanded','false');
      menu.addEventListener('toggle',event=>{
        trigger.setAttribute('aria-expanded',String(event.newState==='open'));
        if(event.newState==='open') menu.querySelector('select:not([disabled]),button:not([disabled])')?.focus();
      });
    }
    document.addEventListener('keydown', event => {
      if (toggle.getAttribute('aria-expanded') !== 'true') return;
      if (event.key === 'Escape') { event.preventDefault(); close(true); }
      if (event.key === 'Tab') {
        const links = [...sidebar.querySelectorAll('a,button,select')].filter(node => node.getClientRects().length && !node.disabled);
        const first = links[0], last = links.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    });
    mobile.addEventListener('change', () => close());
    close();
  });
})();
