/* Only the active membership may resolve a deep link. Identifiers in a URL
   select an already authorized option, never a new API resource. */
function createWorkspaceScreens(onHistoryScope) {
  const el = id => document.getElementById(id);
  const legacy = {'#command-center':'overview','#knowledge-title':'knowledge','#campaigns-list':'campaigns',
    '#workspace-forms':'settings','#workforce-panel':'workforce','#review-panel':'reviews','#deliverables-list':'deliverables',
    '#client-form':'settings','#brand-form':'settings','#campaign-form':'settings','#onboarding':'account'};
  let tenant = '', role = '', mode = '', screen = '', revoked = false, onContext = null;
  const parse = () => {
    const [path, query] = location.hash.slice(1).split('?');
    return {view: path.startsWith('/') ? path.slice(1) : legacy[location.hash], params: new URLSearchParams(query)};
  };
  const preferred = () => role === 'client_viewer' ? 'reviews' : 'overview';
  const allowed = view => {
    if (!view) return false;
    if (role === 'client_viewer') return ['reviews','workforce','account'].includes(view);
    if (view === 'operations') return ['admin','owner'].includes(role) && mode === 'agency';
    if (view === 'settings' && role === 'viewer') return false;
    return [...document.querySelectorAll('a[data-route]')].some(a=>a.dataset.route===view);
  };
  function url(view, params, workspace=tenant) {
    const next = new URL(location.href);
    next.searchParams.set('workspace',workspace);
    if (view!=='reviews') next.searchParams.delete('review');
    const query = params.toString();
    next.hash = '/' + view + (query ? '?' + query : '');
    return next;
  }
  function write(next, replace) {
    if (location.href !== next.href) history[replace ? 'replaceState':'pushState'](null,'',next);
    const query=next.hash.includes('?') ? next.hash.slice(next.hash.indexOf('?')) : '';
    for(const link of document.querySelectorAll('a[data-route]')) link.setAttribute('href','#/'+link.dataset.route+query);
  }
  function closeMenus() {
    document.querySelectorAll('.tool-popover:popover-open').forEach(menu=>menu.hidePopover());
    if (el('menu-toggle').getAttribute('aria-expanded') === 'true') el('menu-close').click();
  }
  function draw(view, focus=false) {
    screen = view;
    document.body.dataset.screen = view;
    const title=document.querySelector('a[data-route="'+view+'"]')?.getAttribute('aria-label');
    document.title=(title ? title+' · ' : '')+'AMC';
    for(const pane of document.querySelectorAll('[data-screen]:not(body)')){
      const notice=revoked && pane.id==='knowledge-panel';
      pane.classList.toggle('screen-off',pane.dataset.screen!==view && !notice);
    }
    for(const link of document.querySelectorAll('a[data-route]')){
      if(link.dataset.route===view) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
    }
    el('toolbar-brand-choice').hidden = screen!=='overview' || role==='client_viewer';
    if (focus) {
      closeMenus();
      const pane=[...document.querySelectorAll('[data-screen]:not(body)')].find(p=>p.dataset.screen===view && p.getClientRects().length);
      if(pane){pane.tabIndex=-1; pane.focus({preventScroll:true});}
      window.scrollTo({top:0,behavior:'instant'});
    }
  }
  function navigate(view, {replace=false,focus=true}={}) {
    if(!tenant) return;
    const target=allowed(view) ? view : preferred();
    write(url(target,parse().params),replace);
    draw(target,focus);
    if(target==='knowledge') document.dispatchEvent(new CustomEvent('amc-open-brand',{detail:parse().params.get('brand')}));
    if(target==='overview') onContext?.(parse().params);
  }
  function enter(membership, lost=false) {
    const loc = new URL(location.href);
    const matches=loc.searchParams.get('workspace') === membership.tenant_id;
    const link=parse();
    tenant=membership.tenant_id; role=membership.role; mode=membership.mode; revoked=lost; onContext=null;
    const target=(matches && allowed(link.view)) ? link.view : (loc.searchParams.has('review')?'reviews':preferred());
    write(url(target,matches && role!=='client_viewer' ? link.params : new URLSearchParams()),true);
    el('scope-trigger').hidden=false; el('refresh').hidden=false;
    el('scope-label').textContent=membership.organization_name || 'Không gian làm việc';
    document.body.dataset.workspaceMode=mode;
    draw(target);
  }
  function reset() {
    tenant=role=screen=''; revoked=false; onContext=null;
    delete document.body.dataset.screen; delete document.body.dataset.workspaceMode;
    el('scope-trigger').hidden=true; el('refresh').hidden=true; el('scope-label').textContent='Không gian làm việc';
    el('toolbar-brand').replaceChildren(); el('toolbar-brand-choice').hidden=true;
    document.querySelectorAll('.screen-off').forEach(p=>p.classList.remove('screen-off'));
    document.title='AMC | AI Marketing Company';
    for(const link of document.querySelectorAll('a[data-route]')){
      link.setAttribute('href','#/'+link.dataset.route);
      link.removeAttribute('aria-current');
    }
    closeMenus();
  }
  function context(brand,campaign,replace=true) {
    if (!tenant || role==='client_viewer') return;
    const params = new URLSearchParams();
    if (brand) params.set('brand',brand);
    if (campaign) params.set('campaign',campaign);
    write(url(screen,params),replace);
  }
  document.addEventListener('amc-brand-selection',event=>{
    const previous=parse().params.get('brand');
    if (screen==='knowledge' && tenant===event.detail.tenant && previous && previous!==event.detail.brand)
      context(event.detail.brand,'');
  });
  document.addEventListener('click',event=>{
    const link=event.target.closest('a[href^="#"]');
    if(!link || !tenant || event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const target=link.dataset.route || legacy[link.hash];
    if(!target) return;
    event.preventDefault(); navigate(target);
    if(legacy[link.hash]){
      const targetEl=el(link.hash.slice(1));
      if (targetEl?.id==='campaign-form'){
        const brand=parse().params.get('brand'), select=el('campaign-brand');
        if(brand && [...select.options].some(option=>option.value===brand)) select.value=brand;
      }
      const focus=targetEl?.querySelector('input:not([disabled])') || targetEl;
      focus?.focus();
    }
  });
  window.addEventListener('popstate',()=>{
    if(!tenant) return;
    const requested=new URL(location.href).searchParams.get('workspace');
    if (requested && requested!==tenant && onHistoryScope(requested)) return;
    const parsed=parse();
    navigate(parsed.view,{replace:true});
    if(screen!=='overview') onContext?.(parsed.params);
  });
  return {enter,reset,navigate,context,params:()=>parse().params,bindContext:fn=>{onContext=fn;},
    switching(id){ closeMenus();write(url(screen || preferred(),new URLSearchParams(),id),false); }};
}
