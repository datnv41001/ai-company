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
    sidebar.addEventListener('click', event => {
      const anchor = event.target.closest('a[href^="#"]');
      if (!anchor) return;
      const target = document.getElementById(anchor.hash.slice(1));
      if (!target) return;
      if (target.closest('[inert], [hidden], .hidden')) return;
      sidebar.querySelectorAll('a[aria-current]').forEach(link => link.removeAttribute('aria-current'));
      anchor.setAttribute('aria-current','location');
      if (mobile.matches) close();
      target.tabIndex = -1;
      target.focus({preventScroll:true});
    });
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
