const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const classes = new Set(), listeners = {}, elements = {};
let parent, focused;
const media = {matches:true, addEventListener(type,fn){this.change=fn;}};
const inspector = {};
elements.inspector = inspector;
elements['mobile-inspector-slot'] = {append(node){assert.equal(node,inspector);parent='popup';}};
elements['inspector-close'] = {addEventListener(type,fn){listeners.closeClick=fn;}, focus(){focused='close';}};
elements['inspector-dialog'] = {
  open:false, scrollTop:100,
  addEventListener(type,fn){listeners[type]=fn;},
  showModal(){this.open=true;}, close(){this.open=false;listeners.close();},
  getBoundingClientRect(){return {left:10,right:300,top:10,bottom:700};}
};
const ctx = vm.createContext({
  matchMedia:()=>media, $:id=>elements[id], state:{tab:'dex'},
  document:{
    documentElement:{classList:{add:x=>classes.add(x),remove:x=>classes.delete(x)}},
    querySelector:selector=>selector==='.workspace'?{append(){parent='desktop';}}:{focus(){focused=selector;}}
  }
});
vm.runInContext(fs.readFileSync('mobile-inspector.js','utf8'),ctx);
ctx.startMobileInspector();
assert.equal(parent,'popup');
assert.equal(elements['inspector-dialog'].open,false,'mobile startup stays closed');
ctx.openMobileInspector({dataset:{select:'n4'}});
assert(elements['inspector-dialog'].open);
assert(classes.has('inspector-open'));
assert.equal(focused,'close');
listeners.closeClick();
assert(!classes.has('inspector-open'));
assert.equal(focused,'.dex-card[data-select="n4"]');
ctx.openMobileInspector({dataset:{select:'n4'}});
listeners.click({target:elements['inspector-dialog'],clientX:0,clientY:0});
assert.equal(elements['inspector-dialog'].open,false,'backdrop closes');
ctx.openMobileInspector({dataset:{select:'n4'}});
media.matches=false;media.change();
assert.equal(parent,'desktop');
assert(!elements['inspector-dialog'].open);
ctx.openMobileInspector({dataset:{select:'n4'}});
assert(!elements['inspector-dialog'].open,'desktop uses the side panel');
console.log('모바일 상세 팝업 검증 통과: 초기 닫힘, 열기, 배경·버튼 닫기, 스크롤 잠금, 포커스 복귀, PC 패널 전환.');
