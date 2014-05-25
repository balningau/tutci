# SETUP
#  - pip install lxml rtyaml beautifulsoup4
#
# USAGE
#  $ python -u extract.py
#  This downloads the jbovlaste export page, uses that list to
#  download the XML export in every language, and then extracts
#  the gismu into formatted YAML files.
#  To get around the captcha, first log into jbovlaste in your
#  web browser. Then, get the cookie for jbovlaste.lojban.org and
#  put it in a file called `jvs_cookie.secret`. (It should look
#  something like `jbovlastessionid=ADSFASFADSF`.)

# <config>

# base for the export list page, and the export links
JVS = 'http://jbovlaste.lojban.org/export/'

# the page with the list of exports
XML_URL = 'xml.html'

# see above: you need to put your jvs session cookie here
# a separate file is used so that this one can be committed
JVS_COOKIE = open('jvs_cookie.secret', 'r').read().strip()

# pattern for saving the jbovlaste exports
# %s will be filled with the language code (en, es, jbo)
XML_FILE = 'xml/%s-xml-export.html'

# folder where the gismu YAML files will be stored
EXPORT_PATH = 'gismu'

# the gismu YAML files will have definitions, notes and gloss
# words in all available languages. the languages in this list
# will be pulled to the top of the file (if present). the rest
# will be sorted alphabetically
FAVORED_LANGUAGES = ['en', 'jbo', 'de', 'es', 'fr', 'ru']

# </config>

import os, codecs, re, urllib2
import rtyaml as yaml
from lxml import etree
from collections import OrderedDict
from bs4 import BeautifulSoup
from pprint import pprint


langs = {}

try:
    opener = urllib2.build_opener()
    opener.addheaders.append(('Cookie', JVS_COOKIE))
    soup = BeautifulSoup(opener.open(JVS + XML_URL).read())
    for link in [li.a.get('href') for li in soup.find_all('li')]:
        lang = link.split('=')[-1]
        if lang != 'test':
            langs[lang] = None
            if not os.path.isfile(XML_FILE % lang):
                print 'downloading', JVS + link
                with codecs.open(XML_FILE % lang, 'w', 'utf-8') as fobj:
                    fobj.write(opener.open(JVS + link).read().decode('utf-8'))
            else:
                print 'file exists', JVS + link
except Exception as e:
    print e
    print "Failed to download XML exports."
    raise

print langs

try:
    for lang in langs.keys():
        print 'importing', XML_FILE % lang
        langs[lang] = codecs.open(XML_FILE % lang, 'r', 'utf-8')
except IOError as e:
    print e
    print "Failed to open import file"
    raise

try:
    for lang in langs.keys():
        print 'parsing', lang
        langs[lang] = etree.parse(langs[lang])
except Exception as e:
    print e
    print "Failed to parse import file."
    raise


all_gismu = {}
stats = {}

#langs = {'en': langs['en']}
for lang, tree in langs.iteritems():
    print '\n'
    print lang
    print '\t',
    stats[lang] = 0
    gismu = tree.xpath("//valsi[@type='gismu']")
    expgismu = tree.xpath("//valsi[@type='experimental gismu']")
    letter = ''

    #gismu = gismu[:10]
    for valsi in gismu:
        # extract info
        word = valsi.get('word')

        this_letter = word[0]
        if this_letter != letter:
            letter = this_letter
            print letter,

        rafsi = [rafsi.text for rafsi in valsi.xpath("rafsi")]
        if len(rafsi) == 0:
            rafsi = ['No rafsi.']

        glosses = tree.xpath("//nlword[@valsi='%s']" % word)
        if len(glosses) > 0:
            gloss = []
            place = []
            for g in glosses:
                s = g.get('word')
                if g.get('sense') is not None:
                    s = '%s (%s)' % (s, g.get('sense'))
                if g.get('place') is not None:
                    s = 'x%s=%s' % (g.get('place'), s)
                    place.append(s)
                else:
                    gloss.append(s)
            gloss = sorted(gloss) + sorted(place)
        else:
            gloss = ['No glosses.']

        definition = valsi.xpath('definition')
        if definition:
            definition = definition[0].text
        else:
            definition = 'No definition.'
        definition = re.sub(r'\$[a-z]_?\{?(\d+)\}?\$', r'x\1', definition)

        notes = valsi.xpath('notes')
        if notes:
            notes = re.sub(r'\$[a-z]_?\{?(\d+)\}?\$', r'x\1', notes[0].text)
            notes = map(lambda s: s.strip(), notes.split('\n'))
        else:
            notes = ['No notes.']

        # add to data structure
        if word not in all_gismu.keys():
            all_gismu[word] = OrderedDict()
            all_gismu[word]['word'] = word
            all_gismu[word]['rafsi'] = rafsi
            all_gismu[word]['examples'] = 'No examples.'
            all_gismu[word]['definitions'] = OrderedDict()

        all_gismu[word]['definitions'][lang] = OrderedDict()
        all_gismu[word]['definitions'][lang]['place structure'] = definition
        all_gismu[word]['definitions'][lang]['notes'] = notes
        all_gismu[word]['definitions'][lang]['glosses'] = gloss

        stats[lang] += 1

pprint(stats)

for valsi, data in all_gismu.iteritems():

    parent_path = os.path.join(EXPORT_PATH, data['word'][0])

    if not os.path.isdir(parent_path):
        os.makedirs(parent_path)

    with codecs.open(os.path.join(parent_path, "{}.yaml".format(valsi)), 'w', 'utf-8') as fobj:
        d = OrderedDict()
        for lang in FAVORED_LANGUAGES:
            if lang in data['definitions'].keys():
                d[lang] = data['definitions'][lang]
        for lang in sorted(list(set(data['definitions'].keys()) - set(FAVORED_LANGUAGES))):
            d[lang] = data['definitions'][lang]
        data['definitions'] = d
        yaml.dump(data, fobj)

