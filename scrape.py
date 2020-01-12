# scrape latin texts from http://penelope.uchicago.edu/Thayer/E/Roman/home.html

import bs4
import re
import requests

def load(url):
    r = requests.get(url)
    return bs4.BeautifulSoup(r.content, 'lxml')

def extract(soup):
    root = soup.new_tag('div')

    header = soup.find('table', class_=('headerbox', 'header'))
    for tag in list(header.next_siblings):
        if hasattr(tag, 'attrs') and 'endnotes' in tag.attrs.get('class', ()):
            break
        root.append(tag.extract())

    bad = ('pagenum', 'linenum', 'translation_flag', 'verse_speaker',
           'ref', 'sec', 'chapter')
    for p in root.find_all('p'):
        for x in p.find_all(class_=bad):
            x.decompose()
        for s in p.strings:
            yield str(s).strip()



def gather_texts(soup):
    for a in soup.find_all('a', href=re.compile('E/Roman/Texts')):
        if a.find_next_siblings('img', src=re.compile('Vatican')):
            yield a.attrs['href'].strip()

def gather_parts(s):
    for a in s.find_all('a', href=re.compile('L/Roman/Texts')):
        x = a.attrs['href'].strip()
        i = x.find('#')
        if i != -1:
            x = x[:i]
        yield x


BASE = 'http://penelope.uchicago.edu/Thayer/'

#part_clean = re.compile()
PARTS = set()
for t in gather_texts(load(BASE + 'E/HELP/Indexes/books.html')):
    for part in gather_parts(load(BASE + t)):
        PARTS.add(part)

for p in PARTS:
    try:
        name = '.'.join(p[14:-6].split('/'))
        print(name)
        with open(name, 'w+') as out:
            for s in extract(load(BASE + p)):
                out.write(s)
                out.write('\n')
    except Exception as err:
        print(err)
