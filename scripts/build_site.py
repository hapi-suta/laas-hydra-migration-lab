#!/usr/bin/env python3
"""Build a portable GitHub Pages site and an allowlisted, secret-free lab bundle."""
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import zipfile
import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
OUT = ROOT / 'site'


def lesson_source(page):
    """Expand maintained reference lessons into the six-task reading path."""
    def include(match):
        source = (page.parent / match[1]).resolve()
        if not source.is_relative_to(DOCS.resolve()) or source.suffix != '.md':
            raise ValueError('Invalid lesson include: ' + str(source))
        text = source.read_text().split('\n', 1)[1]
        def link(m):
            destination = m[2]
            if re.match(r'^[a-z]+:', destination):
                return m[0]
            address, marker, anchor = destination.partition('#')
            resolved = source.parent / address if address else source
            relative = os.path.relpath(resolved, page.parent)
            return m[1] + relative + (marker + anchor if marker else '') + ')'
        text = re.sub(r'(\[[^\]\n]*\]\()([^\s)]+)\)', link, text)
        return text
    return re.sub(r'\{\{lesson:([^}]+)\}\}', include, page.read_text())


def main():
    pages = sorted(DOCS.rglob('*.md'))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(exist_ok=True)
    titles = {p: next((line[2:].strip() for line in p.read_text().splitlines() if line.startswith('# ')), p.stem) for p in pages}
    manifest = json.loads((DOCS / 'navigation.json').read_text())
    for p in pages:
        relative = p.relative_to(DOCS).with_suffix('.html')
        prefix = '../' * (len(relative.parts) - 1)
        nav = f'<a class="home" href="{prefix}index.html">The project</a><a class="home" href="{prefix}start.html">Start here: laptop setup</a>'
        for step in json.loads((DOCS / 'journey.json').read_text()):
            selected = ' aria-current="page"' if p == DOCS / step['page'] else ''
            href = step['page'].replace('.md', '.html')
            nav += f'<a class="home"{selected} href="{prefix}{href}">{html.escape(step["title"])}</a>'
        reference_active = relative.parts[0] in [m['folder'] for m in manifest]
        nav += f'<details class="references" {"open" if reference_active else ""}><summary>Detailed reference lessons</summary>'
        for module in manifest:
            folder = module['folder']
            is_active = relative.parts[0] == folder
            nav += f'<details {"open" if is_active else ""}><summary>{html.escape(module["title"])}</summary>'
            console = DOCS / folder / 'console.md'
            if console.exists():
                selected = ' class="active" aria-current="page"' if p == console else ''
                nav += f'<a{selected} href="{prefix}{folder}/console.html"><span>CONSOLE</span>{html.escape(titles[console])}</a>'
            for phase in ('concepts', 'build', 'use', 'survive'):
                page = DOCS / folder / (phase + '.md')
                if not page.exists():
                    raise ValueError('Missing phase: ' + str(page))
                selected = ' aria-current="page"' if page == p else ''
                nav += f'<a{selected} href="{prefix}{folder}/{phase}.html"><span>{phase.upper()}</span>{html.escape(titles[page])}</a>'
            for extra in module.get('extra', []):
                page = DOCS / folder / (extra + '.md')
                selected = ' aria-current="page"' if page == p else ''
                nav += f'<a{selected} href="{prefix}{folder}/{extra}.html"><span>STEPS</span>{html.escape(titles[page])}</a>'
            nav += '</details>'
        nav += '</details>'
        nav += f'<a class="home" href="{prefix}workstation.html">Install workstation tools</a><a class="home" href="{prefix}worksheet.html">Your lab worksheet</a><a class="home" href="{prefix}validation.html">What has been tested</a><a class="home" href="{prefix}sources.html">Sources & assumptions</a>'
        body = markdown.markdown(lesson_source(p), extensions=['fenced_code', 'tables', 'toc', 'md_in_html'])
        body = re.sub(r'href="([^"#]+)\.md(#[^"]*)?"', lambda m: f'href="{m[1]}.html{m[2] or ""}"', body)
        key = str(relative)
        footer = '' if p.name in ('index.md', 'start.md', 'sources.md', 'validation.md') else f'<section class="checkpoint"><strong>Record your checkpoint</strong><p>Mark complete after you have saved the evidence requested in this lesson. Progress stays in this browser; it is not a server verification.</p><button id="complete" data-key="{key}">Mark lesson complete</button><span id="saved" aria-live="polite"></span></section>'
        result = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(titles[p])} · Hydra Migration Lab</title><link rel="stylesheet" href="{prefix}assets/site.css"><script src="{prefix}assets/site.js" defer></script></head><body><a class="skip" href="#main">Skip to lesson</a><header><a class="brand" href="{prefix}index.html">StepUp Tech Academy<small>Customer migration practice</small></a><div class="header-right"><span>HYDRA / MYSQL TO POSTGRESQL</span><a href="{prefix}downloads/hydra-practice.zip">Download lab</a><button id="menu" aria-label="Toggle lessons" aria-expanded="false">Lessons ☰</button></div></header><div class="layout"><aside aria-label="Lessons"><label class="search">Find a lesson<input id="search" type="search" placeholder="Search lesson titles…"></label>{nav}</aside><main id="main"><div class="eyebrow">BUILD · MIGRATE · CUT OVER</div>{body}{footer}<footer>StepUp Tech Academy · Hydra MySQL to PostgreSQL Migration Practice Lab<br>Build it yourself. Save the result of each check.</footer></main></div></body></html>'''
        dest = OUT / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(result)
    shutil.copytree(DOCS / 'assets', OUT / 'assets', dirs_exist_ok=True)
    (OUT / '.nojekyll').touch()
    downloads = OUT / 'downloads'
    downloads.mkdir(exist_ok=True)
    allowed = []
    for directory in ('app', 'scripts', 'migration', 'infra', 'docs', 'tests'):
        for file in (ROOT / directory).rglob('*'):
            if not file.is_file() or any(part in ('.terraform', '__pycache__') for part in file.parts):
                continue
            if file.suffix in ('.py', '.sh', '.json', '.md', '.tf', '.yaml', '.yml', '.css', '.js', '.svg', '.hcl') or file.name in ('Dockerfile', 'terraform.tfvars.example', 'nginx.conf'):
                allowed.append(file)
    allowed += list((DOCS / 'assets').glob('*.png'))
    allowed += [ROOT / n for n in ('README.md', 'VALIDATION.md', 'requirements.txt', 'compose.yaml', 'compose.cloud.yaml', '.gitignore')]
    # Explicit allowlist: never recursively package the repository root or runtime.
    with zipfile.ZipFile(downloads / 'hydra-practice.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(set(allowed)):
            if file.exists():
                archive.write(file, 'hydra-practice/' + str(file.relative_to(ROOT)))
    digest = hashlib.sha256((downloads / 'hydra-practice.zip').read_bytes()).hexdigest()
    (downloads / 'SHA256SUMS').write_text(digest + '  hydra-practice.zip\n')
    print(f'Built {len(pages)} pages and a secret-free downloadable lab bundle in {OUT}')


if __name__ == '__main__':
    main()
