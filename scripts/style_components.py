#!/usr/bin/env python3
"""Build DM Sans headings and add script-free SVG motion. Safe to run repeatedly."""
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import uharfbuzz as hb
from update_stats import font_instance, text

ROOT = Path(__file__).resolve().parents[1]
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

def element(name, **attributes):
    return ET.Element(f'{{{SVG}}}{name}', attributes)


def reset_motion(root):
    for parent in list(root.iter()):
        for child in list(parent):
            if child.get('data-profile-motion') == 'overlay':
                parent.remove(child)
            elif child.get('data-profile-motion') == 'wrapper':
                position = list(parent).index(child)
                parent.remove(child)
                for nested in list(child):
                    parent.insert(position, nested)
                    position += 1


def border_motion(path, index, social=False):
    root = ET.parse(path).getroot()
    reset_motion(root)
    width, height = int(root.get('width')), int(root.get('height'))
    style = element('style', **{'data-profile-motion':'overlay'})
    style.text = '''.motion-edge{animation:edge-travel 12s linear infinite;opacity:.62}
@keyframes edge-travel{from{stroke-dashoffset:0}to{stroke-dashoffset:-1000}}
@media(prefers-reduced-motion:reduce){.motion-edge{animation:none!important;opacity:.18}}'''
    root.append(style)
    rect = element('rect', x='1.5', y='1.5', width=str(width-3), height=str(height-3),
                   rx='13' if social else '11', fill='none', stroke='#5eead4' if index%2==0 else '#b99aff',
                   **{'stroke-width':'1.5','pathLength':'1000','stroke-dasharray':'90 910',
                      'stroke-dashoffset':str(-index*73),'class':'motion-edge',
                      'style':f'animation-delay:-{index*0.7:.1f}s','data-profile-motion':'overlay'})
    root.append(rect)
    path.write_text(ET.tostring(root, encoding='unicode')+'\n')


def banner_motion(path):
    root = ET.parse(path).getroot()
    reset_motion(root)
    style = element('style', **{'data-profile-motion':'overlay'})
    style.text = '''.motion-photo{animation:photo-drift 7s ease-in-out infinite}
.motion-spark{animation:spark-glow 5s ease-in-out infinite}
@keyframes photo-drift{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
@keyframes spark-glow{0%,100%{opacity:.2}50%{opacity:.8}}
@media(prefers-reduced-motion:reduce){.motion-photo,.motion-spark{animation:none!important;transform:none!important}}'''
    root.append(style)
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag == f'{{{SVG}}}g' and child.get('transform','').startswith('rotate(-2'):
                index = list(parent).index(child)
                wrapper = element('g', **{'class':'motion-photo','data-profile-motion':'wrapper'})
                parent.remove(child)
                wrapper.append(child)
                parent.insert(index,wrapper)
    for i,(x,y) in enumerate([(378,104),(405,344),(959,35)]):
        root.append(element('circle',cx=str(x),cy=str(y),r='2',fill='#5eead4',
                    **{'class':'motion-spark','opacity':'.4','style':f'animation-delay:-{i*1.5}s',
                       'data-profile-motion':'overlay'}))
    path.write_text(ET.tostring(root, encoding='unicode')+'\n')


def heading(label, slug, level):
    size = 24 if level == 2 else 19
    _, font, upem = font_instance(700,size)
    buffer=hb.Buffer();buffer.add_str(label);buffer.guess_segment_properties();hb.shape(font,buffer)
    width=math.ceil(sum(p.x_advance for p in buffer.glyph_positions)*size/upem)+20
    height=38 if level==2 else 32
    root=element('svg',width=str(width),height=str(height),viewBox=f'0 0 {width} {height}',
                 role='img',**{'aria-labelledby':'title','data-font':'DM Sans'})
    title=element('title',id='title');title.text=label;root.append(title)
    style=element('style')
    style.text='''.heading-text{fill:#1f2328}.heading-accent{animation:heading-glow 6s ease-in-out infinite}
@media(prefers-color-scheme:dark){.heading-text{fill:#e6edf3}}
@keyframes heading-glow{0%,100%{opacity:.45}50%{opacity:1}}
@media(prefers-reduced-motion:reduce){.heading-accent{animation:none!important;opacity:1}}'''
    root.append(style)
    root.append(element('rect',x='0',y='7',width='4',height=str(size),rx='2',fill='#8b5cf6',**{'class':'heading-accent'}))
    group=element('g',**{'class':'heading-text'});group.append(ET.fromstring(text(label,16,size+5,size,'inherit',700)));root.append(group)
    path=ROOT/'assets/headings'/f'{slug}.svg';path.parent.mkdir(exist_ok=True)
    path.write_text(ET.tostring(root,encoding='unicode')+'\n')
    return f'<h{level}><img src="./assets/headings/{slug}.svg" width="{width}" height="{height}" alt="{label.replace("&", "&amp;")}" /></h{level}>'


def main():
    headings=[('Let’s connect','connect',3),('GitHub stats','github-stats',2),('My toolkit','my-toolkit',2),
              ('Languages','languages',3),('Web & mobile','web-mobile',3),('Databases','databases',3),
              ('Cloud & infrastructure','cloud-infrastructure',3),('Tools','tools',3),
              ('Badges & community','badges-community',2)]
    readme=(ROOT/'README.md').read_text()
    for label,slug,level in headings:
        replacement=heading(label,slug,level)
        pattern=rf'(?m)^#{{{level}}} {re.escape(label)}$|^<h{level}><img src="\./assets/headings/{slug}\.svg"[^\n]*</h{level}>$'
        readme,count=re.subn(pattern,lambda _:replacement,readme)
        if count!=1:raise ValueError(f'Expected one heading: {label}; found {count}')
    (ROOT/'README.md').write_text(readme)
    banner_motion(ROOT/'assets/header.svg')
    for i,path in enumerate(sorted((ROOT/'assets/toolkit').glob('*.svg'))):border_motion(path,i)
    for i,path in enumerate(sorted((ROOT/'assets/social').glob('*.svg'))):border_motion(path,i,social=True)
    print('Updated 9 DM Sans headings, banner, 23 toolkit tiles and 4 social cards.')

if __name__=='__main__':main()
