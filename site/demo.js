const picker = document.querySelector('.sample-picker');
const samples = [...document.querySelectorAll('[data-sample]')];

function showSample(id) {
  for (const sample of samples) {
    sample.hidden = sample.id !== id;
  }
  for (const control of picker.querySelectorAll('button')) {
    control.setAttribute('aria-pressed', String(control.getAttribute('aria-controls') === id));
  }
}

function showLanguage(sample, language) {
  for (const control of sample.querySelectorAll('[data-language]')) {
    control.setAttribute('aria-pressed', String(control.dataset.language === language));
  }
  for (const transcript of sample.querySelectorAll('[data-transcript]')) {
    transcript.hidden = transcript.dataset.transcript !== language;
  }
}

function showLinkedSample() {
  const target = document.getElementById(location.hash.slice(1));
  const sample = target?.closest('[data-sample]');
  if (!sample) return;

  showSample(sample.id);
  if (target.closest('[data-transcript="original"]')) showLanguage(sample, 'original');
  if (target.hasAttribute('tabindex')) target.focus({ preventScroll: true });
  target.scrollIntoView();
}

picker.addEventListener('click', (event) => {
  const control = event.target.closest('button');
  if (!control) return;

  const id = control.getAttribute('aria-controls');
  showSample(id);
  history.replaceState(null, '', `#${id}`);
});

for (const sample of samples) {
  const languages = sample.querySelector('.language-switch');
  if (languages) {
    languages.hidden = false;
    languages.addEventListener('click', (event) => {
      const control = event.target.closest('button');
      if (control) showLanguage(sample, control.dataset.language);
    });
  }

  sample.addEventListener('click', (event) => {
    if (event.target.closest('.evidence a, .amount-source')) showLanguage(sample, 'original');
  });
}

showSample(samples[0].id);
picker.hidden = false;
showLinkedSample();
window.addEventListener('hashchange', showLinkedSample);
