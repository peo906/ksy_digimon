const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const nodes = [
  {id:'a', name:'아구몬', ready:true, image:'data:old', image2:null},
  {id:'b', name:'에렉몬', ready:false, image:null, image2:null}
];
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {textContent:'', disabled:false, scrollLeft:73, scrollTop:91, classList:{toggle(){}}});
  return elements.get(id);
};
let commit = 'a'.repeat(40), files = [], failFetch = false, failImage = false, requests = 0;
const file = name => ({name:name+'.png', path:'진화표_작업/그림/'+name+'.png', type:'file', sha:'c'.repeat(40)});
const context = vm.createContext({
  DATA:{nodes}, byId:new Map(nodes.map(n=>[n.id,n])), $:element,
  renderStats(){}, render(){}, setTimeout, clearTimeout, AbortController,
  window:{addEventListener(){}}, document:{hidden:false,addEventListener(){}},
  Image:class {
    naturalWidth = 96;
    set src(value) { queueMicrotask(()=>failImage ? this.onerror?.() : this.onload?.()); }
  },
  async fetch(url) {
    requests++;
    if (failFetch) throw new TypeError('network unavailable');
    return {ok:true, json:async()=>url.includes('/commits/')?{sha:commit}:files};
  }
});
vm.runInContext(fs.readFileSync('github-sync.js','utf8'), context);
(async()=>{
  files=[file('아구몬'),file('에렉몬')];
  await context.syncGithubImages(true);
  assert(nodes.every(n=>n.ready));
  assert(nodes[1].image.includes(commit));
  assert(nodes[1].image.includes(encodeURIComponent('에렉몬.png')));
  assert.equal(element('viewport').scrollLeft,73);
  assert.equal(element('viewport').scrollTop,91);
  const firstRequests=requests;
  await context.syncGithubImages(true);
  assert.equal(requests-firstRequests,1,'unchanged commit skips image directory');
  commit='b'.repeat(40);files=[file('에렉몬')];
  await context.syncGithubImages(true);
  assert.equal(nodes[0].ready,false,'deletion becomes missing');
  assert.equal(nodes[0].image,null);
  assert(nodes[1].image.includes(commit),'replacement uses immutable commit URL');
  const snapshot=JSON.stringify(nodes);
  failFetch=true;
  await context.syncGithubImages(true);
  assert.equal(JSON.stringify(nodes),snapshot,'network failure preserves prior data');
  assert(element('sync-status').textContent.includes('마지막 동기화 자료'));
  failFetch=false;failImage=true;commit='d'.repeat(40);files=[file('아구몬')];
  await context.syncGithubImages(true);
  assert.equal(JSON.stringify(nodes),snapshot,'image loading failure is atomic');
  failImage=false;files={error:'bad response'};
  await context.syncGithubImages(true);
  assert.equal(JSON.stringify(nodes),snapshot,'malformed response preserves prior data');
  assert.throws(()=>context.githubImageUpdates([file('아구몬'),file('아구몬')],commit,nodes));
  assert.throws(()=>context.githubImageUpdates([], 'main',nodes));
  const nfd=file('에렉몬'.normalize('NFD'));
  assert(context.githubImageUpdates([nfd],commit,nodes).find(n=>n.id==='b').ready,'Unicode filenames normalize');
  const pose2={name:'아구몬_02.png',path:'진화표_작업/그림/아구몬_02.png',type:'file',sha:'e'.repeat(40)};
  const withPose=context.githubImageUpdates([file('아구몬'),pose2],commit,nodes).find(n=>n.id==='a');
  assert(withPose.image2.includes(encodeURIComponent('아구몬_02.png')),'기본자세02 파일을 추가 이미지로 인식');
  console.log('GitHub 동기화 검증 통과: 추가, 교체, 삭제, 변경 없음, 통신·그림 오류 보존, 잘못된 응답, 한글 파일명.');
})().catch(error=>{console.error(error);process.exitCode=1;});
