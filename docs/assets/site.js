document.querySelector('#menu')?.addEventListener('click', () => {
  const open = document.body.classList.toggle('nav-open');
  document.querySelector('#menu').setAttribute('aria-expanded', String(open));
});
document.querySelector('#search')?.addEventListener('input', (event) => {
  const query = event.target.value.toLowerCase().trim();
  document.querySelectorAll('aside details').forEach(group => {
    let matches = 0;
    const moduleMatch = group.querySelector('summary').textContent.toLowerCase().includes(query);
    group.querySelectorAll('a').forEach(link => {
      const match = !query || moduleMatch || link.textContent.toLowerCase().includes(query);
      link.hidden = !match;
      if (match) matches++;
    });
    group.hidden = matches === 0;
    if (query && matches) group.open = true;
  });
});
document.querySelectorAll('pre').forEach(pre => {
  if (!pre.querySelector('code')) return;
  const button = document.createElement('button');
  button.className = 'copy';
  button.textContent = 'Copy';
  button.setAttribute('aria-label', 'Copy code block');
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(pre.querySelector('code').textContent);
      button.textContent = 'Copied';
      setTimeout(() => { button.textContent = 'Copy'; }, 1600);
    } catch { button.textContent = 'Select code'; }
  });
  pre.append(button);
});
const complete = document.querySelector('#complete');
if (complete) {
  const key = 'hydra-practice:v1:' + complete.dataset.key;
  const show = done => {
    complete.textContent = done ? 'Mark incomplete' : 'Mark lesson complete';
    complete.dataset.done = String(done);
    document.querySelector('#saved').textContent = done ? '✓ Saved in this browser' : '';
  };
  try { show(localStorage.getItem(key) === 'true'); } catch { show(false); }
  complete.addEventListener('click', () => {
    const done = complete.dataset.done !== 'true';
    try { localStorage.setItem(key, String(done)); show(done); }
    catch { document.querySelector('#saved').textContent = 'Browser storage is unavailable.'; }
  });
}
