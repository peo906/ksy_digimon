const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('index.template.html', 'utf8');
const source = html.slice(html.indexOf('function enableDragPan('), html.indexOf("enableDragPan($('viewport'))"));
const events = {}, windowEvents = {}, classes = new Set();
let captured = null;
const viewport = {
  scrollLeft: 50, scrollTop: 60, clientWidth: 500, clientHeight: 400,
  getBoundingClientRect: () => ({left: 0, top: 0}), focus() {},
  addEventListener: (type, fn) => events[type] = fn,
  setPointerCapture: id => captured = id,
  hasPointerCapture: id => captured === id,
  releasePointerCapture: () => captured = null,
  classList: {add: name => classes.add(name), remove: name => classes.delete(name)}
};
const context = vm.createContext({window: {addEventListener: (type, fn) => windowEvents[type] = fn}});
vm.runInContext(source, context);
context.enableDragPan(viewport);
const event = (extra = {}) => ({pointerType: 'mouse', button: 0, pointerId: 1,
  clientX: 100, clientY: 100, target: {closest: () => null}, preventDefault() {}, ...extra});
events.pointerdown(event());
events.pointermove(event({clientX: 70, clientY: 50}));
assert.equal(viewport.scrollLeft, 80);
assert.equal(viewport.scrollTop, 110);
assert(classes.has('is-dragging'));
events.pointerup(event());
assert.equal(captured, null);
assert(!classes.has('is-dragging'));
for (const extra of [{target: {closest: () => ({})}}, {pointerType: 'touch'}, {button: 2}, {clientX: 501}]) {
  events.pointerdown(event(extra));
  events.pointermove(event({clientX: 0, clientY: 0}));
  assert.equal(viewport.scrollLeft, 80);
}
events.pointerdown(event());
windowEvents.blur();
events.pointermove(event({clientX: 0}));
assert.equal(viewport.scrollLeft, 80);
events.pointerdown(event());
events.pointercancel(event());
assert.equal(captured, null);
console.log('Drag pan: movement, release, card clicks, touch, scrollbar, blur and cancellation passed.');
