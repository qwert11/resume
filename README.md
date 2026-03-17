# Resume Engine

Готовый проект для GitHub Pages:

- единая YAML-база
- несколько target-резюме
- генерация HTML / Markdown / DOCX / PDF
- страницы:
  - `/resume` → полная карьера
  - `/resume/dotnet`
  - `/resume/delphi`
  - `/resume/web`
- GitHub Actions автоматически пересобирает сайт после изменений в YAML

## Как использовать

### 1. Установить зависимости локально
```bash
pip install -r requirements.txt
```

### 2. Собрать всё
```bash
python scripts/build.py --all
```

### 3. Собрать только одну цель
```bash
python scripts/build.py --target dotnet
python scripts/build.py --target delphi
python scripts/build.py --target full
python scripts/build.py --target web
```

### 4. Что редактировать
Обычно только:

- `data/master.yaml`
- `data/experience.yaml`
- `data/projects.yaml`
- `data/skills.yaml`
- `data/education.yaml`
- `data/achievements.yaml`

## GitHub Pages

В настройках репозитория:

`Settings -> Pages -> Source -> GitHub Actions`

После этого каждый commit в `main` будет:
1. собирать HTML/PDF/DOCX/MD
2. публиковать сайт в GitHub Pages

## Структура

```text
resume/
├── .github/workflows/build-pages.yml
├── assets/
│   ├── css/site.css
│   └── js/theme.js
├── data/
│   ├── master.yaml
│   ├── experience.yaml
│   ├── projects.yaml
│   ├── skills.yaml
│   ├── education.yaml
│   └── achievements.yaml
├── output/
├── scripts/
│   ├── build.py
│   └── utils.py
├── targets/
│   ├── full.yaml
│   ├── dotnet.yaml
│   ├── delphi.yaml
│   └── web.yaml
├── templates/
│   ├── site.html.j2
│   └── resume.md.j2
└── requirements.txt
```
