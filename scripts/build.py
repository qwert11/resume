"""Build the one-page resume.

Data comes from github.com/qwert11/resume2 (see fetch_source.py); `onepager.yaml`
decides what fits on the single A4 page. Output: output/site/index.html plus
resume.pdf / .docx / .md in English and Ukrainian.
"""
from pathlib import Path
from datetime import date
import argparse, json, shutil

from jinja2 import Environment, FileSystemLoader
from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from utils import load_yaml, ensure_dir
import fetch_source

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
TEMPLATES = ROOT / 'templates'
ASSETS = ROOT / 'assets'
OUTPUT = ROOT / 'output'
LANGS = ['en', 'uk']

FONT_CANDIDATES = [
    ('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
     'DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ('DejaVuSans', 'C:/Windows/Fonts/DejaVuSans.ttf',
     'DejaVuSans-Bold', 'C:/Windows/Fonts/DejaVuSans-Bold.ttf'),
    ('ArialUnicode', 'C:/Windows/Fonts/arial.ttf',
     'ArialUnicode-Bold', 'C:/Windows/Fonts/arialbd.ttf'),
]
_fonts = {'regular': 'Helvetica', 'bold': 'Helvetica-Bold'}

LABELS = {
    'contacts': {'uk': 'Контакти', 'en': 'Contact'},
    'stack': {'uk': 'Ключові навички', 'en': 'Key skills'},
    'education': {'uk': 'Освіта', 'en': 'Education'},
    'earlier': {'uk': 'Раніше', 'en': 'Earlier'},
    'full_resume': {'uk': 'Повне резюме', 'en': 'Full resume'},
}


def register_fonts():
    for reg_name, reg_path, bold_name, bold_path in FONT_CANDIDATES:
        if Path(reg_path).exists() and Path(bold_path).exists():
            pdfmetrics.registerFont(TTFont(reg_name, reg_path))
            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
            _fonts['regular'], _fonts['bold'] = reg_name, bold_name
            return
    print('warning: no Unicode TTF found, PDF falls back to Helvetica (Latin only)')


# ---------------------------------------------------------------- helpers

def t(value, lang):
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    return value.get(lang) or value.get('en') or value.get('uk') or ''


def norm(value):
    if isinstance(value, dict):
        return {'uk': value.get('uk') or value.get('en') or '', 'en': value.get('en') or value.get('uk') or ''}
    return {'uk': value or '', 'en': value or ''}


def collect(cfg, full_resume):
    master = load_yaml(DATA / 'master.yaml')['profile']
    experience = {e['id']: e for e in load_yaml(DATA / 'experience.yaml')}
    education = load_yaml(DATA / 'education.yaml')['education']
    languages = load_yaml(DATA / 'languages.yaml')['languages']

    by_value = {m['value']: m for m in master['metrics']}
    metrics = [by_value[v] for v in cfg['metrics'] if v in by_value][:4]

    # Positions shown in full, with the bullets picked as milestones (by index in experience.yaml).
    jobs, shown = [], set()
    for spec in cfg['jobs']:
        e = experience.get(spec['id'])
        if not e:
            print(f"warning: job '{spec['id']}' not found in experience.yaml")
            continue
        idx = spec.get('bullets') or list(range(len(e['bullets']['en'])))
        picked = dict(e, bullets={
            lang: [e['bullets'][lang][i] for i in idx if i < len(e['bullets'][lang])]
            for lang in LANGS if lang in e['bullets']
        })
        jobs.append(picked)
        shown.add(spec['id'])
    earlier = [e for e in experience.values() if e['id'] not in shown]

    skill_groups = [{'label': norm(g['label']), 'items': [norm(s) for s in g['items']]} for g in cfg['skills']]

    return {
        'profile': master,
        'title_obj': master['titles'][cfg['title_key']],
        'summary_obj': master['summary'][cfg['summary_key']],
        'metrics': metrics,
        'skill_groups': skill_groups,
        'jobs': jobs,
        'earlier': earlier,
        'education': [education[i] for i in cfg.get('education', [0]) if i < len(education)],
        'languages': languages,
        'full_resume': full_resume + (cfg['route'] + '/' if cfg['route'] else ''),
        'route': cfg['route'],
        'id': cfg['id'],
    }


def period(item, present_word):
    end = present_word if item['end'] == 'present' else item['end']
    return f"{item['start']} — {end}"


def earlier_line(items, lang, present_word):
    """Older positions compressed into one line: role, company (years)."""
    parts = []
    for e in sorted(items, key=lambda x: x['start'], reverse=True):
        years = f"{e['start'][:4]}–{(present_word if e['end'] == 'present' else e['end'][:4])}"
        parts.append(f"{t(e['title'], lang)}, {t(e['company'], lang)} ({years})")
    return ' · '.join(parts)


def doc_model(b, lang):
    p = b['profile']
    present = t(p['ui']['present'], lang)
    sec = {k: t(v, lang) for k, v in p['sections'].items()}
    sec.update({k: v[lang] for k, v in LABELS.items()})
    return {
        'name': t(p['name'], lang),
        'title': t(b['title_obj'], lang),
        'summary': t(b['summary_obj'], lang),
        'location': t(p['location'], lang),
        'contacts': [c['label'] for c in p['contacts']],
        'labels': sec,
        'metrics': [f"{m['value']} {t(m['unit'], lang)} — {t(m['label'], lang)}".replace('  ', ' ')
                    for m in b['metrics']],
        'skills': [(t(g['label'], lang), [t(s, lang) for s in g['items']]) for g in b['skill_groups']],
        'jobs': [{
            'company': t(e['company'], lang),
            'title': t(e['title'], lang),
            'period': period(e, present),
            'city': t(e['city'], lang),
            'bullets': e['bullets'][lang if lang in e['bullets'] else 'en'],
        } for e in b['jobs']],
        'earlier': earlier_line(b['earlier'], lang, present),
        'education': [f"{t(e['specialty'], lang)} — {t(e['institution'], lang)} ({e['period']})"
                      for e in b['education']],
        'languages': [f"{t(l['name'], lang)} — {t(l['level'], lang)}" for l in b['languages']],
        'full_resume': b['full_resume'],
    }


# ---------------------------------------------------------------- documents

def build_docx(path, s):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10)
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Pt(40)
        section.left_margin = section.right_margin = Pt(46)

    doc.add_heading(s['name'], 0)
    par = doc.add_paragraph()
    par.add_run(s['title']).bold = True
    doc.add_paragraph(' · '.join(s['contacts'] + [s['location']]))
    doc.add_paragraph(s['summary'])
    doc.add_paragraph(' · '.join(s['metrics']))

    doc.add_heading(s['labels']['stack'], level=1)
    for label, items in s['skills']:
        par = doc.add_paragraph()
        par.add_run(f'{label}: ').bold = True
        par.add_run(', '.join(items))

    doc.add_heading(s['labels']['details'], level=1)
    for e in s['jobs']:
        par = doc.add_paragraph()
        par.add_run(f"{e['title']}, {e['company']}, {e['city']}").bold = True
        doc.add_paragraph(e['period'])
        for line in e['bullets']:
            doc.add_paragraph(line, style='List Bullet')
    if s['earlier']:
        doc.add_paragraph(f"{s['labels']['earlier']}: {s['earlier']}")

    doc.add_heading(s['labels']['education'], level=1)
    for line in s['education']:
        doc.add_paragraph(line, style='List Bullet')

    doc.add_heading(s['labels']['languages'], level=1)
    for line in s['languages']:
        doc.add_paragraph(line, style='List Bullet')

    doc.add_paragraph(f"{s['labels']['full_resume']}: {s['full_resume']}")
    doc.save(path)


def build_pdf(path, s, profile_id='full'):
    """Same layout as the page: a tinted side column and the main column, one A4 sheet."""
    register_fonts()
    reg, bold = _fonts['regular'], _fonts['bold']
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    side_w = 168
    pad = 20
    top = height - 40

    INK, SOFT, MUTED, SIDE_BG, LINE = (0.05, 0.06, 0.07), (0.12, 0.14, 0.15), (0.32, 0.36, 0.35), (0.93, 0.94, 0.93), (0.75, 0.78, 0.76)

    c.setFillColorRGB(*SIDE_BG)
    c.rect(0, 0, side_w, height, stroke=0, fill=1)

    def wrap(text, font, size, width_limit):
        words, lines, cur = str(text).split(), [], ''
        for w in words:
            probe = (cur + ' ' + w).strip()
            if pdfmetrics.stringWidth(probe, font, size) <= width_limit:
                cur = probe
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines or ['']

    class Column:
        def __init__(self, x, w, y):
            self.x, self.w, self.y = x, w, y

        def block(self, text, font=None, size=8.6, leading=11, indent=0, color=INK, bullet=None):
            font = font or reg
            c.setFillColorRGB(*color)
            c.setFont(font, size)
            lines = wrap(text, font, size, self.w - indent)
            for i, line in enumerate(lines):
                if bullet is not None and i == 0:
                    c.drawString(self.x + indent - bullet[1], self.y, bullet[0])
                c.drawString(self.x + indent, self.y, line)
                self.y -= leading

        def rule(self, label, color=INK, line_color=LINE):
            self.y -= 6
            c.setFillColorRGB(*color)
            c.setFont(bold, 7.4)
            c.drawString(self.x, self.y, label.upper())
            self.y -= 4
            c.setStrokeColorRGB(*line_color)
            c.setLineWidth(0.6)
            c.line(self.x, self.y, self.x + self.w, self.y)
            self.y -= 10

        def gap(self, n):
            self.y -= n

    side = Column(pad, side_w - 2 * pad, top)
    main = Column(side_w + 26, width - side_w - 26 - 30, top)

    # ---- side column
    side.rule(s['labels']['contacts'], color=MUTED)
    for line in s['contacts'] + [s['location']]:
        side.block(line, reg, 8.2, 11, color=SOFT)
    side.gap(6)
    side.rule(s['labels']['stack'], color=MUTED)
    for label, items in s['skills']:
        side.block(label.upper(), bold, 6.8, 9.4, color=MUTED)
        side.block(' · '.join(items), reg, 8.2, 10.8, color=SOFT)
        side.gap(3.5)
    side.gap(4)
    side.rule(s['labels']['languages'], color=MUTED)
    for line in s['languages']:
        side.block(line, reg, 8.2, 10.8, color=SOFT)
    side.gap(8)
    side.rule(s['labels']['education'], color=MUTED)
    for line in s['education']:
        side.block(line, reg, 8.2, 10.8, color=SOFT)
        side.gap(3)

    # ---- main column
    main.block(s['name'], bold, 22, 26)
    main.block(s['title'], reg, 10.6, 14.5, color=MUTED)
    main.gap(5)
    main.block(s['summary'], reg, 9.2, 12.4, color=SOFT)
    main.gap(4)
    c.setStrokeColorRGB(*LINE)
    c.line(main.x, main.y, main.x + main.w, main.y)
    main.gap(12)
    for m in s['metrics']:
        main.block(m, reg, 8.4, 11.2, color=MUTED)

    main.rule(s['labels']['details'], color=MUTED)
    for e in s['jobs']:
        main.block(e['period'], reg, 7.8, 10.6, color=MUTED)
        main.block(f"{e['title']}, {e['company']}, {e['city']}", bold, 9.6, 12.8)
        main.gap(2)
        for line in e['bullets']:
            main.block(line, reg, 8.9, 11.6, indent=9, color=SOFT, bullet=('–', 9))
        main.gap(7)
    if s['earlier']:
        c.setStrokeColorRGB(*LINE)
        c.setDash(1, 2)
        c.line(main.x, main.y + 3, main.x + main.w, main.y + 3)
        c.setDash()
        main.gap(8)
        main.block(f"{s['labels']['earlier']}: {s['earlier']}", reg, 8.2, 11, color=MUTED)

    c.setFillColorRGB(*MUTED)
    c.setFont(reg, 7.4)
    c.drawString(main.x, 30, f"{s['labels']['full_resume']}: {s['full_resume']}")
    if main.y < 44:
        print(f'warning: [{profile_id}] PDF main column overflows by {44 - main.y:.0f}pt')
    if side.y < 44:
        print(f'warning: [{profile_id}] PDF side column overflows by {44 - side.y:.0f}pt')
    c.save()


# ---------------------------------------------------------------- build

def build(skip_fetch=False):
    if not skip_fetch:
        print('fetching data from resume2:')
        fetch_source.fetch()

    cfg = load_yaml(ROOT / 'onepager.yaml')

    site = OUTPUT / 'site'
    if site.exists():
        shutil.rmtree(site)
    ensure_dir(site)
    shutil.copytree(ASSETS, site / 'assets', dirs_exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    profiles = [{'id': x['id'], 'route': x['route']} for x in cfg['profiles']]
    for prof in cfg['profiles']:
        build_profile(prof, cfg['full_resume'], profiles, env, site)

    (site / '.nojekyll').write_text('', encoding='utf-8')
    print(f'built {site}')


def build_profile(cfg, full_resume, profiles, env, site):
    b = collect(cfg, full_resume)
    p = b['profile']
    out = site / cfg['route'] if cfg['route'] else site
    ensure_dir(out)
    prefix = '../' if cfg['route'] else ''

    js_data = {
        'profile': p,
        'sections': p['sections'],
        'ui': p['ui'],
        'titleTextObj': b['title_obj'],
        'summaryTextObj': b['summary_obj'],
    }
    en = doc_model(b, 'en')
    uk = doc_model(b, 'uk')

    html = env.get_template('onepager.html.j2').render(
        profile_id=cfg['id'],
        profiles=profiles,
        prefix=prefix,
        page_title=f"{en['name']} — {en['title']}",
        name_text=en['name'],
        title_text=en['title'],
        summary_text=en['summary'],
        location=norm(p['location']),
        contacts=p['contacts'],
        metrics=[dict(m, unit=norm(m['unit']), label=norm(m['label'])) for m in b['metrics']],
        skill_groups=b['skill_groups'],
        jobs=[{
            'company': norm(e['company']),
            'title': norm(e['title']),
            'city': norm(e['city']),
            'start': e['start'],
            'end': e['end'],
            'bullets_en': e['bullets']['en'],
            'bullets_uk': e['bullets'].get('uk') or e['bullets']['en'],
        } for e in b['jobs']],
        earlier=norm({'en': en['earlier'], 'uk': uk['earlier']}),
        education=[{
            'specialty': norm(e['specialty']),
            'institution': norm(e['institution']),
            'period': e['period'],
        } for e in b['education']],
        languages=[{'uk': u, 'en': e} for u, e in zip(uk['languages'], en['languages'])],
        full_resume=b['full_resume'],
        build_date=date.today().isoformat(),
        js_data=json.dumps(js_data, ensure_ascii=False),
    )
    (out / 'index.html').write_text(html, encoding='utf-8')

    for lang, model in (('en', en), ('uk', uk)):
        suffix = '' if lang == 'en' else f'.{lang}'
        md = env.get_template('resume.md.j2').render(s=model)
        (out / f'resume{suffix}.md').write_text(md, encoding='utf-8')
        build_docx(out / f'resume{suffix}.docx', model)
        build_pdf(out / f'resume{suffix}.pdf', model, cfg['id'])
    print(f"  {cfg['id']}: {out.relative_to(site) if out != site else '.'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-fetch', action='store_true', help='build from the local data copy')
    build(**vars(ap.parse_args()))


if __name__ == '__main__':
    main()
