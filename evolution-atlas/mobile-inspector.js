const mobileInspector = matchMedia('(max-width: 800px)');
let inspectorTrigger = null;

function syncInspectorLayout() {
  if (mobileInspector.matches) {
    $('mobile-inspector-slot').append($('inspector'));
  } else {
    if ($('inspector-dialog').open) $('inspector-dialog').close();
    document.querySelector('.workspace').append($('inspector'));
  }
}

function openMobileInspector(trigger) {
  if (!mobileInspector.matches) return;
  const dialog = $('inspector-dialog');
  if (!dialog.open) {
    inspectorTrigger = {id: trigger.dataset.select, tab: state.tab};
    dialog.showModal();
    document.documentElement.classList.add('inspector-open');
    $('inspector-close').focus({preventScroll: true});
  }
  dialog.scrollTop = 0;
}

function closeMobileInspector() {
  if ($('inspector-dialog').open) $('inspector-dialog').close();
}

function startMobileInspector() {
  syncInspectorLayout();
  mobileInspector.addEventListener('change', syncInspectorLayout);
  $('inspector-close').addEventListener('click', closeMobileInspector);
  $('inspector-dialog').addEventListener('close', () => {
    document.documentElement.classList.remove('inspector-open');
    if (!inspectorTrigger) return;
    const selectors = {dex: '.dex-card', tree: '.node', jogress: '.recipe-person'};
    document.querySelector(`${selectors[inspectorTrigger.tab]}[data-select="${inspectorTrigger.id}"]`)?.focus({preventScroll: true});
    inspectorTrigger = null;
  });
  $('inspector-dialog').addEventListener('click', e => {
    if (e.target !== $('inspector-dialog')) return;
    const r = e.target.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) closeMobileInspector();
  });
}
