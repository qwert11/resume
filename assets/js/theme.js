(function () {
  var KEY = 'resume-theme-mode';
  var ORDER = ['auto', 'light', 'dark'];
  var root = document.documentElement;
  var mode = 'auto';

  function byClock() {
    var h = new Date().getHours();
    return (h >= 7 && h < 20) ? 'light' : 'dark';
  }

  function paint() {
    root.setAttribute('data-theme', mode === 'auto' ? byClock() : mode);
    root.setAttribute('data-theme-mode', mode);
  }

  function set(next) {
    mode = ORDER.indexOf(next) >= 0 ? next : 'auto';
    try { localStorage.setItem(KEY, mode); } catch (e) {}
    paint();
    document.dispatchEvent(new CustomEvent('resume:thememode', { detail: { mode: mode } }));
  }

  try { mode = localStorage.getItem(KEY) || 'auto'; } catch (e) {}
  paint();

  window.RESUME_THEME = {
    get mode() { return mode; },
    set: set,
    cycle: function () { set(ORDER[(ORDER.indexOf(mode) + 1) % ORDER.length]); }
  };

  document.addEventListener('DOMContentLoaded', function () {
    // One button cycles Auto → Light → Dark; its label is set by i18n.js.
    document.querySelectorAll('[data-theme-cycle]').forEach(function (b) {
      b.addEventListener('click', function () { window.RESUME_THEME.cycle(); });
    });
    set(mode);
  });
})();
