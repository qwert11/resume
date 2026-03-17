(function(){
  const STORAGE_KEY = "resume-theme-mode";
  const MODES = ["auto", "light", "dark"];

  function lerp(a,b,t){ return a + (b-a)*t; }
  function mix(c1,c2,t){
    return [
      Math.round(lerp(c1[0], c2[0], t)),
      Math.round(lerp(c1[1], c2[1], t)),
      Math.round(lerp(c1[2], c2[2], t))
    ];
  }
  function rgb(arr){ return `rgb(${arr[0]}, ${arr[1]}, ${arr[2]})`; }
  function setVar(name, value){ document.documentElement.style.setProperty(name, value); }

  let timer = null;

  function seasonFactor(month){
    // 0 winter dark bias, 1 summer light bias
    // Jan=0, Jul=6
    const summerPeak = Math.cos(((month - 6) / 12) * Math.PI * 2);
    return (1 - summerPeak) / 2;
  }

  function applyAutoTheme(){
    const now = new Date();
    const hour = now.getHours() + now.getMinutes()/60 + now.getSeconds()/3600;
    const month = now.getMonth(); // 0..11
    const summer = seasonFactor(month);

    // daily cycle: 0 night, 1 day with season bias
    const base = (Math.cos(((hour - 12) / 24) * Math.PI * 2) + 1) / 2;
    const t = Math.min(1, Math.max(0, base * (0.75 + summer * 0.35)));

    const bg = mix([8, 13, 26], [236, 242, 252], t * 0.18);
    const panel = mix([22, 32, 59], [250, 252, 255], t * 0.10);
    const line = mix([42, 57, 102], [195, 208, 238], t * 0.32);
    const text = mix([237, 242, 255], [28, 36, 52], t * 0.08);
    const muted = mix([182, 195, 226], [87, 102, 128], t * 0.10);
    const accent = mix([122, 162, 255], [78, 122, 245], t * 0.12);
    const accentSoft = mix([159, 224, 255], [94, 146, 245], t * 0.12);
    const chip = mix([33, 49, 92], [235, 240, 252], t * 0.08);

    setVar('--bg', rgb(bg));
    setVar('--panel', rgb(panel));
    setVar('--line', rgb(line));
    setVar('--text', rgb(text));
    setVar('--muted', rgb(muted));
    setVar('--accent', rgb(accent));
    setVar('--accent-soft', rgb(accentSoft));
    setVar('--chip', rgb(chip));
  }

  function applyLightTheme(){
    setVar('--bg', 'rgb(241,245,255)');
    setVar('--panel', 'rgb(255,255,255)');
    setVar('--line', 'rgb(198,210,237)');
    setVar('--text', 'rgb(32,40,56)');
    setVar('--muted', 'rgb(95,110,135)');
    setVar('--accent', 'rgb(88,124,245)');
    setVar('--accent-soft', 'rgb(76,150,235)');
    setVar('--chip', 'rgb(236,241,253)');
  }

  function applyDarkTheme(){
    setVar('--bg', 'rgb(11,16,32)');
    setVar('--panel', 'rgb(22,32,59)');
    setVar('--line', 'rgb(42,57,102)');
    setVar('--text', 'rgb(237,242,255)');
    setVar('--muted', 'rgb(182,195,226)');
    setVar('--accent', 'rgb(122,162,255)');
    setVar('--accent-soft', 'rgb(159,224,255)');
    setVar('--chip', 'rgb(33,49,92)');
  }

  function stopAuto(){
    if(timer){
      clearInterval(timer);
      timer = null;
    }
  }

  function startAuto(){
    stopAuto();
    applyAutoTheme();
    timer = setInterval(applyAutoTheme, 1000);
  }

  function setMode(mode){
    if(!MODES.includes(mode)) mode = 'auto';
    localStorage.setItem(STORAGE_KEY, mode);
    document.querySelectorAll('[data-theme-mode]').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-theme-mode') === mode);
    });
    if(mode === 'auto') startAuto();
    else {
      stopAuto();
      if(mode === 'light') applyLightTheme();
      if(mode === 'dark') applyDarkTheme();
    }
  }

  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('[data-theme-mode]').forEach(btn => {
      btn.addEventListener('click', () => setMode(btn.getAttribute('data-theme-mode')));
    });
    const saved = localStorage.getItem(STORAGE_KEY) || 'auto';
    setMode(saved);
  });
})();
