(function () {
  var KEY = 'resume-theme-mode';
  var root = document.documentElement;

  function byClock() {
    var h = new Date().getHours();
    return (h >= 7 && h < 20) ? 'light' : 'dark';
  }

  function paint(mode) {
    var theme = (mode === 'auto') ? byClock() : mode;
    root.setAttribute('data-theme', theme);
  }

  function setMode(mode) {
    try { localStorage.setItem(KEY, mode); } catch (e) {}
    paint(mode);
    document.querySelectorAll('[data-theme-mode]').forEach(function (b) {
      b.classList.toggle('active', b.dataset.themeMode === mode);
    });
  }

  var saved = 'auto';
  try { saved = localStorage.getItem(KEY) || 'auto'; } catch (e) {}
  paint(saved);

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-theme-mode]').forEach(function (b) {
      b.addEventListener('click', function () { setMode(b.dataset.themeMode); });
    });
    setMode(saved);
  });
})();
