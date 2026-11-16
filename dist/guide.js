'use strict';
window.CasteloGuide={
 html(){return `<section class="guide-reader" aria-label="Leitor do guia comercial"><div class="guide-toolbar"><div class="guide-navigation"><button class="button outline small" data-guide="prev" aria-label="Página anterior">← Anterior</button><label class="guide-select"><span class="visually-hidden">Ir para a página</span><select id="guide-page">${Array.from({length:28},(_,i)=>`<option value="${i+1}">Página ${i+1} de 28</option>`).join('')}</select></label><button class="button outline small" data-guide="next" aria-label="Próxima página">Próxima →</button></div><button class="button outline small" data-guide="zoom" aria-pressed="false">Ampliar página ＋</button></div><p class="guide-hint">Folheie pelas setas ou escolha uma página. Use “Ampliar página” para ler os detalhes.</p><div class="guide-stage" tabindex="0" aria-label="Página do guia. Use as setas do teclado para folhear."><img id="guide-image" src="assets/guia/pagina-01.jpg" alt="Guia comercial do parceiro — página 1 de 28" width="1600" height="1132"></div><p id="guide-status" class="viewer-note" role="status" aria-live="polite">Página 1 de 28</p></section>`},
 mount(host){
  const reader=host.querySelector('.guide-reader'),stage=reader.querySelector('.guide-stage'),img=reader.querySelector('#guide-image'),select=reader.querySelector('#guide-page'),status=reader.querySelector('#guide-status');
  const prev=reader.querySelector('[data-guide=prev]'),next=reader.querySelector('[data-guide=next]'),zoomButton=reader.querySelector('[data-guide=zoom]');
  let page=1,zoom=false,touch=null;
  const path=n=>`assets/guia/pagina-${String(n).padStart(2,'0')}.jpg`;
  function setZoom(value){zoom=value;stage.classList.toggle('is-zoomed',zoom);zoomButton.setAttribute('aria-pressed',zoom);zoomButton.textContent=zoom?'Ajustar à janela −':'Ampliar página ＋';stage.scrollTop=0;stage.scrollLeft=0}
  function go(n){page=Math.max(1,Math.min(28,n));select.value=page;prev.disabled=page===1;next.disabled=page===28;setZoom(false);status.textContent=`Carregando página ${page} de 28…`;img.alt=`Guia comercial do parceiro — página ${page} de 28`;img.src=path(page)}
  function loaded(){status.textContent=`Página ${page} de 28`;if(page<28){const preload=new Image();preload.src=path(page+1)}}
  function failed(){status.textContent='Esta página não carregou. Verifique sua conexão e selecione a página novamente.'}
  function keys(e){if(e.target.matches('input,select,textarea')||zoom)return;if(e.key==='ArrowLeft'){e.preventDefault();go(page-1)}if(e.key==='ArrowRight'){e.preventDefault();go(page+1)}}
  prev.addEventListener('click',()=>go(page-1));next.addEventListener('click',()=>go(page+1));select.addEventListener('change',()=>go(Number(select.value)));
  zoomButton.addEventListener('click',()=>setZoom(!zoom));img.addEventListener('load',loaded);img.addEventListener('error',failed);reader.addEventListener('keydown',keys);
  stage.addEventListener('touchstart',e=>{touch=e.touches.length===1?{x:e.touches[0].clientX,y:e.touches[0].clientY}:null},{passive:true});
  stage.addEventListener('touchend',e=>{if(touch&&!zoom){const p=e.changedTouches[0],dx=p.clientX-touch.x,dy=p.clientY-touch.y;if(Math.abs(dx)>60&&Math.abs(dy)<50)go(page+(dx<0?1:-1))}touch=null},{passive:true});
  prev.disabled=true;if(img.complete&&img.naturalWidth)loaded();
  return ()=>{reader.removeEventListener('keydown',keys);img.removeEventListener('load',loaded);img.removeEventListener('error',failed)};
 }
};
