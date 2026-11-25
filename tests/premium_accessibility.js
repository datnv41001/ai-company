/* Inspect rendered text in its actual component; alpha layers are composed from canvas to foreground. */
(root) => {
  const parse = value => {
    const parts = value.match(/[\d.]+/g);
    if (!parts || parts.length < 3) return null;
    return [...parts.slice(0, 3).map(Number), Number(parts[3] ?? 1)];
  };
  const over = (front, back) => {
    const a = front[3] + back[3] * (1 - front[3]);
    return [...front.slice(0, 3).map((c, i) => a ? (c * front[3] + back[i] * back[3] * (1-front[3]))/a : 0), a];
  };
  const luminance = rgb => {
    const [r,g,b] = rgb.map(c => c/255).map(c => c <= .04045 ? c/12.92 : ((c+.055)/1.055)**2.4);
    return .2126*r + .7152*g + .0722*b;
  };
  const seen = new Set(), rows = [], unresolved = [];
  function sample(el, label, pseudo) {
    if (!label || !el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}) ||
        el.closest('[aria-hidden=true], [inert], [hidden], option, svg, button:disabled, input:disabled, select:disabled')) return;
    const ink = getComputedStyle(el,pseudo || null);
    const fg = parse(ink.color);
    const chain = [];
    for (let node=el;node;node=node.parentElement) chain.push(getComputedStyle(node));
    const colorKey = chain.map(s=>[s.backgroundColor,s.backgroundImage,s.opacity].join('/')).join('|');
    const key = [ink.color,ink.fontSize,ink.fontWeight,colorKey,pseudo].join(':');
    if (seen.has(key)) return;
    seen.add(key);
    const size=parseFloat(ink.fontSize), bold=Number(ink.fontWeight)>=700;
    const required=size>=24 || (bold && size>=56/3) ? 3 : 4.5;
    const item = {label:label.slice(0,60),tag:el.tagName.toLowerCase(),color:ink.color,px:size,required};
    if(!fg) {unresolved.push({...item,reason:'unsupported foreground'});return;}
    // Ignore decorative ancestors fully obscured by an opaque component surface.
    const layers = [];
    for (const s of chain) {
      const color = parse(s.backgroundColor);
      if (!color || s.backgroundImage!=='none' || s.opacity!=='1') {
        unresolved.push({...item,reason:s.backgroundImage!=='none'?'background image':'opacity or unsupported background'}); return;
      }
      layers.push(color);
      if (color[3]===1) break;
    }
    const bg = layers.reverse().reduce((back,layer)=>over(layer,back),[255,255,255,1]);
    if (pseudo) fg[3] *= Number(ink.opacity);
    const L1=luminance(over(fg,bg)), L2=luminance(bg);
    const ratio=(Math.max(L1,L2)+.05)/(Math.min(L1,L2)+.05);
    rows.push({...item,background:bg.slice(0,3).map(Math.round),ratio,pass:ratio>=required});
  }
  const walker = document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){
    const node=walker.currentNode, el=node.parentElement;
    if(el && !el.closest('script, style, select, textarea, [class~="sr-only"], [class~="visually-hidden"]')) sample(el,node.textContent.trim());
  }
  for(const el of root.querySelectorAll('input:not([type=hidden]),textarea')){
    if(el.value) sample(el,el.getAttribute('aria-label') || el.name || 'input value');
    else if(el.placeholder) sample(el,el.placeholder,'::placeholder');
  }
  for(const el of root.querySelectorAll('select')) sample(el,el.selectedOptions[0]?.textContent?.trim());
  return {checked:rows,unresolved};
}
