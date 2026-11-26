const GITHUB_SOURCE = Object.freeze({
  repo: 'peo906/ksy_digimon', branch: 'main', folder: '진화표_작업/그림', interval: 5 * 60 * 1000
});
const githubSync = {busy: false, commit: null, checked: null, attempted: 0, retryAt: 0};

function githubImageUpdates(files, commit, nodes) {
  if (!Array.isArray(files) || !/^[a-f0-9]{40}$/.test(commit)) throw new Error('GitHub 자료 형식을 확인할 수 없어요.');
  const images = new Map();
  for (const file of files) {
    if (file.type !== 'file' || !/\.png$/i.test(file.name)) continue;
    if (file.path !== GITHUB_SOURCE.folder + '/' + file.name || !/^[a-f0-9]{40}$/.test(file.sha)) {
      throw new Error('그림 파일 경로를 확인할 수 없어요.');
    }
    const name = file.name.slice(0, -4).normalize('NFC');
    if (images.has(name)) throw new Error('같은 이름의 그림이 중복되어 있어요: ' + name);
    const path = file.path.split('/').map(encodeURIComponent).join('/');
    images.set(name, `https://raw.githubusercontent.com/${GITHUB_SOURCE.repo}/${commit}/${path}`);
  }
  return nodes.map(n => ({id: n.id, ready: images.has(n.name.normalize('NFC')),
    image: images.get(n.name.normalize('NFC')) || null}));
}

async function githubJson(path) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`https://api.github.com/repos/${GITHUB_SOURCE.repo}/${path}`, {
      headers: {Accept: 'application/vnd.github+json'}, cache: 'no-store', signal: controller.signal
    });
    if (!response.ok) {
      if (response.status === 403 || response.status === 429) {
        const reset = Number(response.headers.get('x-ratelimit-reset')) * 1000;
        githubSync.retryAt = Math.max(Date.now() + GITHUB_SOURCE.interval, reset || 0);
        throw new Error('GitHub 요청 제한으로 잠시 쉬었다가 다시 확인해요.');
      }
      throw new Error(`GitHub 연결 실패 (${response.status})`);
    }
    return await response.json();
  } finally { clearTimeout(timer); }
}

function preloadGithubImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    const timer = setTimeout(() => finish(false), 15000);
    function finish(ok) {
      clearTimeout(timer); image.onload = null; image.onerror = null;
      if (ok) resolve(); else reject(new Error('그림을 불러오지 못했어요. 기존 자료를 유지합니다.'));
    }
    image.onload = () => finish(image.naturalWidth > 0);
    image.onerror = () => finish(false);
    image.src = url;
  });
}

function showGithubStatus(message, error = false) {
  $('sync-status').textContent = message;
  $('github-sync').classList.toggle('sync-error', error);
  $('sync-now').disabled = githubSync.busy || Date.now() < githubSync.retryAt;
  $('sync-now').textContent = githubSync.busy ? '확인 중…' : '지금 동기화';
}

async function syncGithubImages(force = false) {
  const now = Date.now();
  if (githubSync.busy || now < githubSync.retryAt || (!force && now - githubSync.attempted < GITHUB_SOURCE.interval)) return;
  githubSync.busy = true; githubSync.attempted = now;
  showGithubStatus('GitHub의 최신 그림을 확인하고 있어요.');
  try {
    const commit = await githubJson('commits/' + GITHUB_SOURCE.branch);
    if (!/^[a-f0-9]{40}$/.test(commit.sha)) throw new Error('GitHub 버전을 확인할 수 없어요.');
    if (commit.sha !== githubSync.commit) {
      const folder = GITHUB_SOURCE.folder.split('/').map(encodeURIComponent).join('/');
      const files = await githubJson(`contents/${folder}?ref=${commit.sha}`);
      const updates = githubImageUpdates(files, commit.sha, DATA.nodes);
      // 모든 새 그림의 로딩이 끝난 뒤 한 번에 반영해 실패 시 기존 그림과 집계를 보존한다.
      await Promise.all(updates.filter(n => n.ready && n.image !== byId.get(n.id).image).map(n => preloadGithubImage(n.image)));
      const left = $('viewport').scrollLeft, top = $('viewport').scrollTop, catalogTop = $('catalog').scrollTop;
      updates.forEach(n => Object.assign(byId.get(n.id), n));
      githubSync.commit = commit.sha;
      renderStats(); render();
      $('viewport').scrollLeft = left; $('viewport').scrollTop = top; $('catalog').scrollTop = catalogTop;
    }
    githubSync.checked = new Date();
    const time = githubSync.checked.toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Seoul'});
    githubSync.busy = false;
    showGithubStatus(`연동 완료 · 그림 ${DATA.nodes.filter(n => n.ready).length}종 · ${time} 확인 (한국 시간)`);
  } catch (error) {
    githubSync.busy = false;
    const detail = error.name === 'AbortError' ? '연결 시간이 초과됐어요.' :
      error.name === 'TypeError' ? '네트워크에 연결할 수 없어요.' :
      error.name === 'SyntaxError' ? 'GitHub 응답을 읽을 수 없어요.' : error.message;
    showGithubStatus(`${detail} ${githubSync.checked ? '마지막 동기화 자료' : '저장된 자료'}로 표시 중입니다.`, true);
  }
}

function startGithubSync() {
  $('sync-now').addEventListener('click', () => syncGithubImages(true));
  window.addEventListener('online', () => syncGithubImages(true));
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) syncGithubImages();
  });
  setInterval(() => { if (!document.hidden) syncGithubImages(); }, GITHUB_SOURCE.interval);
  syncGithubImages();
}
