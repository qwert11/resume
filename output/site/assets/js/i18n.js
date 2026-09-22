(function () {
  var KEY = 'resume-lang';
  var data = window.RESUME_DATA || {};
  var lang = 'en';

  var L = {
    earlier: { uk: 'Раніше', en: 'Earlier' },
    contacts: { uk: 'Контакти', en: 'Contact' },
    stack: { uk: 'Ключові навички', en: 'Key skills' },
    education: { uk: 'Освіта', en: 'Education' },
    full_link: { uk: 'Повне резюме: ', en: 'Full resume: ' },
    export_btn: { uk: 'Експорт', en: 'Export' },
    theme_title: { uk: 'Тема: натисніть, щоб змінити', en: 'Theme: click to change' },
    lang_title: { uk: 'Мова', en: 'Language' }
  };

  function detect() {
    var q = null;
    try { q = new URLSearchParams(location.search).get('lang'); } catch (e) {}
    if (q === 'uk' || q === 'en') return q;
    var tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || '').toLowerCase();
    var nav = (navigator.language || '').toLowerCase();
    if (tz.indexOf('kyiv') >= 0 || tz.indexOf('kiev') >= 0 || nav.indexOf('uk') === 0) return 'uk';
    return 'en';
  }

  function tr(obj, l) {
    return (obj && (obj[l] || obj.en || obj.uk)) || '';
  }

  function setText(sel, value) {
    document.querySelectorAll(sel).forEach(function (el) { el.textContent = value; });
  }

  function downloads() {
    var suffix = lang === 'uk' ? '.uk' : '';
    var map = { '[data-dl-pdf]': 'pdf', '[data-dl-docx]': 'docx', '[data-dl-md]': 'md' };
    Object.keys(map).forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        el.setAttribute('href', 'resume' + suffix + '.' + map[sel]);
      });
    });
  }

  function themeLabel() {
    var ui = data.ui || {};
    var mode = (window.RESUME_THEME && window.RESUME_THEME.mode) || 'auto';
    var el = document.querySelector('[data-theme-cycle]');
    if (!el) return;
    el.textContent = tr(ui[mode], lang);
    el.setAttribute('title', tr(L.theme_title, lang));
    el.setAttribute('data-mode', mode);
  }

  function apply(next, remember) {
    lang = next;
    if (remember) { try { localStorage.setItem(KEY, lang); } catch (e) {} }

    var ui = data.ui || {}, sec = data.sections || {};
    setText('[data-i18n-name]', tr(data.profile && data.profile.name, lang));
    setText('[data-i18n-target-title]', tr(data.titleTextObj, lang));
    setText('[data-i18n-summary]', tr(data.summaryTextObj, lang));

    // top bar
    setText('[data-i18n-profiles-hint]', tr(ui.profiles_hint, lang));
    ['full', 'dotnet', 'delphi', 'web', 'ai'].forEach(function (id) {
      setText('[data-i18n-nav-' + id + ']', tr(ui[id], lang));
    });
    themeLabel();
    setText('[data-i18n-lang-current]', tr(lang === 'uk' ? ui.ua : ui.en, lang));
    document.querySelectorAll('[data-lang]').forEach(function (b) {
      b.textContent = tr(b.dataset.lang === 'uk' ? ui.ua : ui.en, lang);
      b.classList.toggle('active', b.dataset.lang === lang);
    });
    document.querySelectorAll('.dd-lang').forEach(function (d) { d.setAttribute('title', tr(L.lang_title, lang)); });
    setText('[data-i18n-export]', tr(L.export_btn, lang));
    setText('[data-i18n-btn-pdf]', tr(ui.pdf, lang));
    setText('[data-i18n-btn-word]', tr(ui.word, lang));
    setText('[data-i18n-btn-markdown]', tr(ui.markdown, lang));

    // sheet
    setText('[data-i18n-present]', tr(ui.present, lang));
    setText('[data-i18n-earlier]', tr(L.earlier, lang));
    setText('[data-i18n-section-contacts]', tr(L.contacts, lang));
    setText('[data-i18n-section-stack]', tr(L.stack, lang));
    setText('[data-i18n-section-details]', tr(sec.details, lang));
    setText('[data-i18n-section-education]', tr(L.education, lang));
    setText('[data-i18n-section-languages]', tr(sec.languages, lang));
    document.querySelectorAll('[data-i18n-full-link]').forEach(function (el) {
      var short = (el.getAttribute('href') || '').replace(/^https?:\/\//, '').replace(/\/$/, '');
      el.textContent = tr(L.full_link, lang) + short;
    });
    document.querySelectorAll('[data-uk][data-en]').forEach(function (el) {
      el.textContent = lang === 'uk' ? el.dataset.uk : el.dataset.en;
    });

    downloads();
    document.documentElement.lang = lang;
  }

  function closeMenus(except) {
    document.querySelectorAll('details.dd[open]').forEach(function (d) {
      if (d !== except) d.removeAttribute('open');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-lang]').forEach(function (b) {
      b.addEventListener('click', function () {
        apply(b.dataset.lang, true);
        closeMenus();
      });
    });
    // one open dropdown at a time; close on outside click, Escape, or after picking an export
    document.querySelectorAll('details.dd').forEach(function (d) {
      d.addEventListener('toggle', function () { if (d.open) closeMenus(d); });
      d.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', function () { closeMenus(); }); });
    });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('details.dd')) closeMenus();
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenus(); });
    document.addEventListener('resume:thememode', themeLabel);

    var forced = null;
    try { forced = new URLSearchParams(location.search).get('lang'); } catch (e) {}
    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) {}
    apply((forced === 'uk' || forced === 'en') ? forced : (saved || detect()), false);
  });
})();
