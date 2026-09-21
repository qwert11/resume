"""Build the one-page resume.

Data comes from github.com/qwert11/resume2 (see fetch_source.py); `onepager.yaml`
decides what fits on the single page. Output: output/site/index.html plus
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


def pick(items, ids, key='id'):
    """Select items by id, in the order the ids are listed."""
    index = {x[key]: x for x in items}
    return [index[i] for i in ids if i in index]


def rest(items, ids, key='id'):
    return [x for x in items if x[key] not in ids]


def collect(cfg):
    master = load_yaml(DATA / 'master.yaml')['profile']
    experience = load_yaml(DATA / 'experience.yaml')
    projects = load_yaml(DATA / 'projects.yaml')
    groups = load_yaml(DATA / 'skills.yaml')['groups']
    education = load_yaml(DATA / 'education.yaml')['education']
    languages = load_yaml(DATA / 'languages.yaml')['languages']

    metrics = [m for m in master['metrics'] if m['value'] in cfg['metrics']][:cfg['max_metrics']]
    skill_groups = [
        {'id': g['id'], 'label': norm(g['label']),
         'items': [norm(s['name']) for s in g['items'][:cfg['max_skills']]]}
        for g in pick(groups, cfg['skill_groups'])
    ]
    jobs = pick(experience, cfg['jobs'])
    earlier = rest(experience, cfg['jobs'])

    return {
        'profile': master,
        'title_obj': master['titles'][cfg['title_key']],
        'summary_obj': master['summary'][cfg['summary_key']],
        'metrics': metrics,
        'skill_groups': skill_groups,
        'jobs': jobs,
        'earlier': earlier,
        'projects': pick(projects, cfg['projects']),
        'project_sentences': cfg.get('project_sentences', 0),
        'education': education,
        'languages': languages,
        'max_bullets': cfg['max_bullets'],
        'full_resume': cfg['full_resume'],
    }


def first_sentences(text, count):
    """Keep only the first N sentences — the page has room for one line per project."""
    if not count:
        return text
    out, taken = [], 0
    for chunk in text.replace('! ', '. ').split('. '):
        out.append(chunk)
        taken += 1
        if taken >= count:
            break
    joined = '. '.join(out).strip()
    if not joined.endswith('.'):
        joined += '.'
    return joined


def period(item, lang, present_word):
    end = present_word if item['end'] == 'present' else item['end']
    return f"{item['start']} — {end}"


def earlier_line(items, lang, present_word):
    """Older positions compressed into one line: company (years)."""
    parts = []
    for e in items:
        years = f"{e['start'][:4]}–{(present_word if e['end'] == 'present' else e['end'][:4])}"
        parts.append(f"{t(e['company'], lang)} ({years})")
    return ' · '.join(parts)


def doc_model(b, lang):
    p = b['profile']
    present = t(p['ui']['present'], lang)
    sec = {k: t(v, lang) for k, v in p['sections'].items()}
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
            'period': period(e, lang, present),
            'city': t(e['city'], lang),
            'bullets': e['bullets'][lang if lang in e['bullets'] else 'en'][:b['max_bullets']],
        } for e in b['jobs']],
        'earlier': earlier_line(b['earlier'], lang, present),
        'projects': [{
            'name': t(pr['name'], lang),
            'period': pr['period'],
            'description': first_sentences(t(pr['description'], lang), b['project_sentences']),
            'stack': pr.get('stack') or [],
        } for pr in b['projects']],
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
        par.add_run(f"{e['title']} — {e['company']}").bold = True
        doc.add_paragraph(f"{e['period']} · {e['city']}")
        for line in e['bullets']:
            doc.add_paragraph(line, style='List Bullet')
    if s['earlier']:
        doc.add_paragraph(s['earlier'])

    doc.add_heading(s['labels']['projects'], level=1)
    for pr in s['projects']:
        par = doc.add_paragraph()
        par.add_run(f"{pr['name']} ({pr['period']}). ").bold = True
        par.add_run(pr['description'])

    doc.add_heading(s['labels']['education'], level=1)
    for line in s['education']:
        doc.add_paragraph(line, style='List Bullet')

    doc.add_heading(s['labels']['languages'], level=1)
    for line in s['languages']:
        doc.add_paragraph(line, style='List Bullet')

    doc.add_paragraph(s['full_resume'])
    doc.save(path)


def build_pdf(path, s):
    register_fonts()
    reg, bold = _fonts['regular'], _fonts['bold']
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    left, right = 44, 44
    avail = width - left - right
    y = height - 46

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

    def block(text, font=None, size=9.2, leading=12, indent=0, color=(0.09, 0.11, 0.12)):
        nonlocal y
        font = font or reg
        c.setFillColorRGB(*color)
        c.setFont(font, size)
        for line in wrap(text, font, size, avail - indent):
            if y < 48:
                c.showPage()
                y = height - 46
                c.setFont(font, size)
                c.setFillColorRGB(*color)
            c.drawString(left + indent, y, line)
            y -= leading

    def rule(label):
        nonlocal y
        y -= 7
        c.setFillColorRGB(0.09, 0.11, 0.12)
        c.setFont(bold, 9.5)
        c.drawString(left, y, label.upper())
        y -= 4
        c.setStrokeColorRGB(0.72, 0.75, 0.73)
        c.setLineWidth(0.6)
        c.line(left, y, width - right, y)
        y -= 11

    block(s['name'], bold, 20, 24)
    block(s['title'], reg, 11.5, 15, color=(0.25, 0.29, 0.28))
    block(' · '.join(s['contacts'] + [s['location']]), reg, 9, 12, color=(0.32, 0.36, 0.35))
    y -= 3
    block(s['summary'], reg, 9.4, 12.4, color=(0.15, 0.17, 0.18))
    block(' · '.join(s['metrics']), reg, 8.6, 11.5, color=(0.32, 0.36, 0.35))

    rule(s['labels']['stack'])
    for label, items in s['skills']:
        block(f"{label}: {', '.join(items)}", reg, 9, 11.6)

    rule(s['labels']['details'])
    for e in s['jobs']:
        block(f"{e['title']} — {e['company']}", bold, 9.6, 12.4)
        block(f"{e['period']} · {e['city']}", reg, 8.6, 11.4, color=(0.36, 0.4, 0.39))
        for line in e['bullets']:
            block('• ' + line, reg, 9, 11.6, indent=9, color=(0.18, 0.2, 0.21))
        y -= 2
    if s['earlier']:
        block(s['earlier'], reg, 8.6, 11.4, color=(0.36, 0.4, 0.39))

    rule(s['labels']['projects'])
    for pr in s['projects']:
        block(f"{pr['name']} ({pr['period']}). {pr['description']}", reg, 9, 11.6)
        if pr['stack']:
            block(', '.join(pr['stack']), reg, 8.4, 11, indent=9, color=(0.4, 0.44, 0.43))

    rule(s['labels']['education'])
    for line in s['education']:
        block('• ' + line, reg, 9, 11.6)

    rule(s['labels']['languages'])
    for line in s['languages']:
        block('• ' + line, reg, 9, 11.6)

    y -= 4
    block(s['full_resume'], reg, 8.4, 11, color=(0.4, 0.44, 0.43))
    c.save()


# ---------------------------------------------------------------- build

def build(skip_fetch=False):
    if not skip_fetch:
        print('fetching data from resume2:')
        fetch_source.fetch()

    cfg = load_yaml(ROOT / 'onepager.yaml')
    b = collect(cfg)
    p = b['profile']

    site = OUTPUT / 'site'
    if site.exists():
        shutil.rmtree(site)
    ensure_dir(site)
    shutil.copytree(ASSETS, site / 'assets', dirs_exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
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
            'bullets_en': e['bullets']['en'][:b['max_bullets']],
            'bullets_uk': e['bullets']['uk'][:b['max_bullets']],
        } for e in b['jobs']],
        earlier=norm({'en': en['earlier'], 'uk': uk['earlier']}),
        projects=[{
            'name': norm(pr['name']),
            'period': pr['period'],
            'description': norm({'uk': first_sentences(t(pr['description'], 'uk'), b['project_sentences']),
                                 'en': first_sentences(t(pr['description'], 'en'), b['project_sentences'])}),
            'stack': pr.get('stack') or [],
        } for pr in b['projects']],
        education=[{'uk': u, 'en': e} for u, e in zip(uk['education'], en['education'])],
        languages=[{'uk': u, 'en': e} for u, e in zip(uk['languages'], en['languages'])],
        full_resume=b['full_resume'],
        build_date=date.today().isoformat(),
        js_data=json.dumps(js_data, ensure_ascii=False),
    )
    (site / 'index.html').write_text(html, encoding='utf-8')

    for lang, model in (('en', en), ('uk', uk)):
        suffix = '' if lang == 'en' else f'.{lang}'
        md = env.get_template('resume.md.j2').render(s=model)
        (site / f'resume{suffix}.md').write_text(md, encoding='utf-8')
        build_docx(site / f'resume{suffix}.docx', model)
        build_pdf(site / f'resume{suffix}.pdf', model)

    (site / '.nojekyll').write_text('', encoding='utf-8')
    print(f'built {site}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-fetch', action='store_true', help='build from the local data copy')
    build(**vars(ap.parse_args()))


if __name__ == '__main__':
    main()
