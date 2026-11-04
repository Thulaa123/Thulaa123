#!/usr/bin/env python3
"""Generate self-contained README cards from public GitHub data (requires gh)."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import escape
from functools import lru_cache
import io
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import uharfbuzz as hb
import json
from pathlib import Path
import subprocess

PALETTE = ['#a78bfa', '#5eead4', '#60a5fa', '#fbbf24', '#f472b6', '#fb923c', '#94a3b8']


def api(endpoint, paginate=False):
    command = ['gh', 'api', endpoint]
    if paginate:
        command += ['--paginate', '--slurp']
    response = subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    return json.loads(response.stdout)


def public_owned(repos, username, exclude_forks=False):
    return [repo for repo in repos
            if not repo.get('private', True)
            and repo['owner']['login'].lower() == username.lower()
            and not (exclude_forks and repo.get('fork', False))]


def aggregate_languages(language_maps):
    totals = Counter()
    for languages in language_maps:
        for language, size in languages.items():
            if not isinstance(size, int) or size < 0:
                raise ValueError('Invalid language byte count')
            if size:
                totals[language] += size
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    shown = ranked[:5]
    if len(ranked) > 5:
        shown.append(('Other', sum(size for _, size in ranked[5:])))
    return shown


def collect(username):
    profile = api(f'users/{username}')
    pages = api(f'users/{username}/repos?per_page=100&type=owner', paginate=True)
    repos = public_owned([repo for page in pages for repo in page], username)
    originals = public_owned(repos, username, exclude_forks=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        languages = list(pool.map(lambda repo: api(f"repos/{repo['full_name']}/languages"), originals))
    prs = api(f'search/issues?q=author%3A{username}+type%3Apr+is%3Apublic&per_page=1')
    issues = api(f'search/issues?q=author%3A{username}+type%3Aissue+is%3Apublic&per_page=1')
    if prs.get('incomplete_results') or issues.get('incomplete_results'):
        raise RuntimeError('GitHub search results were incomplete; retaining existing cards')
    return {
        'repositories': len(repos),
        'stars': sum(repo['stargazers_count'] for repo in originals),
        'forks': sum(repo['forks_count'] for repo in originals),
        'followers': profile['followers'],
        'pull_requests': prs['total_count'],
        'issues': issues['total_count'],
        'languages': aggregate_languages(languages),
    }


@lru_cache(maxsize=32)
def font_instance(weight, size):
    path = Path(__file__).resolve().parents[1] / 'assets/fonts/DM-Sans.ttf'
    font = instantiateVariableFont(TTFont(path), {'wght': weight, 'opsz': max(9, min(40, size))}, inplace=True)
    buffer = io.BytesIO()
    font.save(buffer)
    face = hb.Face(buffer.getvalue())
    shaped_font = hb.Font(face)
    shaped_font.scale = (face.upem, face.upem)
    return font, shaped_font, face.upem


def text(value, x, y, size=13, color='#c5cee0', weight=400):
    # Paths keep the real DM Sans letterforms when GitHub renders the SVG as an image.
    font, shaped_font, upem = font_instance(weight, size)
    glyphs = font.getGlyphSet()
    names = font.getGlyphOrder()
    buffer = hb.Buffer()
    buffer.add_str(str(value))
    buffer.guess_segment_properties()
    hb.shape(shaped_font, buffer)
    pen = SVGPathPen(glyphs)
    scale = size / upem
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions):
        transform = TransformPen(pen, (scale, 0, 0, -scale,
                                       x + position.x_offset * scale,
                                       y - position.y_offset * scale))
        glyphs[names[info.codepoint]].draw(transform)
        x += position.x_advance * scale
    return f'<path aria-label="{escape(str(value), quote=True)}" fill="{color}" d="{pen.getCommands()}"/>'


def card(title, description, body, date):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="260" viewBox="0 0 480 260" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs><linearGradient id="background" x2="1" y2="1"><stop stop-color="#101c2e"/><stop offset="1" stop-color="#1b1830"/></linearGradient></defs>
<rect x=".5" y=".5" width="479" height="259" rx="18" fill="url(#background)" stroke="#303c53"/>
<g data-font="DM Sans">{text(title,24,36,20,'#e9e6ff',700)}
{body}
<path d="M24 222H456" stroke="#303c53"/>{text('Updated '+date+' · public GitHub data',24,243,10,'#94a3b8')}
</g></svg>\n'''


def render_stats(data, date):
    metrics = [('Public repos', data['repositories']), ('Stars earned', data['stars']),
               ('Followers', data['followers']), ('Public pull requests', data['pull_requests']),
               ('Public issues', data['issues']), ('Forks received', data['forks'])]
    body = text('A snapshot of my open-source activity',24,58,12,'#94a3b8')
    for i, (label, value) in enumerate(metrics):
        x = 24 + i % 3 * 151
        y = 104 + i // 3 * 78
        body += text(f'{value:,}',x,y,29, '#5eead4' if i % 2 else '#bda4ff',700)
        body += text(label,x,y+22,11)
    description = '; '.join(f'{label}: {value}' for label,value in metrics)
    return card('GitHub overview',description,body,date)


def render_languages(data, date):
    languages=data['languages'];total=sum(size for _,size in languages)
    body=text('Share of code bytes in public, non-fork repositories',24,58,11,'#94a3b8')
    if not total:
        body += text('No public language data yet',24,120,16)
    else:
        x=24
        for i,(name,size) in enumerate(languages):
            width=432*size/total
            body+=f'<rect x="{x:.3f}" y="78" width="{width:.3f}" height="13" fill="{PALETTE[i]}"/>'
            x+=width
        for i,(name,size) in enumerate(languages):
            x=24+(i%2)*222;y=123+(i//2)*32
            body+=f'<circle cx="{x+4}" cy="{y-4}" r="4" fill="{PALETTE[i]}"/>'
            body+=text(name,x+16,y,12)+text(f'{100*size/total:.1f}%',x+162,y,12,'#e9e6ff',700)
    desc='Public, non-fork repository language bytes. '+', '.join(f'{n}: {s} bytes' for n,s in languages)
    return card('Most used languages',desc,body,date)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',default='Thulaa123')
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'assets/stats')
    args=parser.parse_args()
    if not args.username or any(not(c.isalnum() or c=='-') for c in args.username):
        parser.error('Invalid GitHub username')
    data=collect(args.username)
    date=datetime.now(timezone.utc).strftime('%d %b %Y')
    # Complete all fetching and rendering before replacing any published image.
    cards={'overview.svg':render_stats(data,date),'languages.svg':render_languages(data,date)}
    args.output.mkdir(parents=True,exist_ok=True)
    for name,content in cards.items():
        temporary=args.output/(name+'.tmp')
        temporary.write_text(content,encoding='utf-8')
        temporary.replace(args.output/name)
    print(f"Generated cards: {data['repositories']} public repos, {data['stars']} stars, {len(data['languages'])} language groups")

if __name__=='__main__':
    main()
