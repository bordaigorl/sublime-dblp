import sublime
import sublime_plugin

import urllib
import json
import re
from string import Template

import threading

DEBUG = False


def LOG(m):
    if DEBUG:
        print("DBLP Search: ", m)

if "quote_plus" in urllib.__dict__:
    urlquote = urllib.quote_plus
else:
    urlquote = urllib.parse.quote_plus

try:
    import HTMLParser
    entityDecode = HTMLParser.HTMLParser().unescape
except ImportError:
    import html.parser
    entityDecode = html.parser.HTMLParser().unescape


def strip_tags(value):
    """Returns the given HTML with all tags stripped."""
    return re.sub(r'<[^>]*?>', '', value)

urlopen = None  # could be better

if 'request' in urllib.__dict__:
    urlopen = urllib.request.urlopen
else:
    urlopen = urllib.urlopen


def key_from_url(url):
    mark = "dblp.org/rec/"
    pos = url.find(mark)
    if pos >= 0:
        return url[pos+len(mark):]
    else:
        return url


MARKDOWN_CITATION = '''
# ${title}
  > ${authors}
    ${venue} (${year})
  [${key}](${url})
'''
MARKDOWN_TEMPLATE = Template(MARKDOWN_CITATION)


def getFieldText(field, default=""):
    if isinstance(field, str):
        return entityDecode(field)
    elif isinstance(field, list):
        return ', '.join([entityDecode(x) for x in field])
    elif hasattr(field, "text"):  # Old API
        return entityDecode(field.get("text", default))
    else:
        return entityDecode(default)

def dblp_search_url(query, max_hits):
    query = query.replace("'", " ").replace(",", " ")
    url = "http://dblp.dagstuhl.de/search/publ/api?format=json&q=%s&h=%s"
    return url % (urlquote(query), max_hits)

def dblp_fetch(url):
    data = urlopen(url).read().decode()
    data = json.loads(data)
    LOG(data)
    data = data['result']
    if 'time' in data:
        sublime.status_message(
            "DBLP Search done in %s%s" % (data['time']['text'], data['time']['@unit']))
    return data['hits'].get('hit', [])

def dblp_parse_hit(hit):
    info = hit.get('info')
    LOG(hit.get("@id", "") + " - " + str(info))
    # entry_url = hit.get('url') # OLD API
    entry_url = info.get('url') if info else None
    authors = info.get('authors', {}).get('author', ["No Author"])
    if isinstance(authors, str):
        authors = [authors]
    elif isinstance(authors, dict):
        authors = [authors.get('text', "Unknown")]
    for i, a in enumerate(authors):
        if isinstance(a, dict):
            a = a.get('text', "Unknown")
        authors[i] = entityDecode(a)
    title = info.get('title', {})
    if info and entry_url:
        key = info.get("key", key_from_url(entry_url))
        return {
                    'key': key,
                    'cite_key': u"DBLP:" + key,
                    'title': getFieldText(title, "No Title"),
                    'year': info['year'],
                    'venue': getFieldText(info.get('venue', {})),
                    'authors': ', '.join(authors),
                    'doi': info.get('doi', ""),
                    'url': entry_url,
                    'informal': info.get("type", "").startswith("Informal"),
                }
    return {}


class SearchDBLPThread(threading.Thread):

    def __init__(self, query, max_hits, include_informal=True, on_search_results=None, on_error=None):
        threading.Thread.__init__(self)
        self.query = query
        self.max_hits = max_hits
        self.include_informal = include_informal
        self.on_search_results = on_search_results
        self.on_error = on_error
        self._stopped = False

    def stop(self):
        self._stopped = True
        # if self.isAlive():
        #     self._Thread__stop()

    def run(self):
        try:
            url = dblp_search_url(self.query, self.max_hits)
            LOG(url)
            sublime.status_message("Contacting DBLP to fetch references...")
            hits = dblp_fetch(url)
            result = []
            for hit in hits:
                if self._stopped:
                    return
                entry = dblp_parse_hit(hit)
                if entry:
                    if self.include_informal or not entry.get('informal'):
                        result.append(entry)

            if self.on_search_results and not self._stopped:
                self.on_search_results(result)
            return

        except Exception as e:
            LOG('Error [%s]' % e)
            if self.on_error:
                self.on_error(str(e))
            else:
                raise


class DblpSearchCommand(sublime_plugin.TextCommand):

    _queryThread = None

    def on_query(self, q):
        if len(q) > 3:
            if self._queryThread is not None:
                LOG("Starting Thread...")
                self._queryThread.stop()
            m = self.args.get("max_hits", 500)
            ii = self.args.get("include_informal", True)
            self._queryThread = SearchDBLPThread(q, m, ii, self.on_search_results, self.on_error)
            self._queryThread.start()
        else:
            sublime.status_message('DBLP query is too short!')

    def on_search_results(self, results):
        if len(results) == 0:
            sublime.status_message('DBLP returned no results for your search!')
            return
        self.results = results
        if len(results) == 1 and not self.args.get('always_choose', False):
            self.on_entry_selected(0)
        else:
            menu = [[x['title'], '%s (%s)' % (x['authors'], x['year'])] for x in results]
            self.window.show_quick_panel(menu, self.on_entry_selected, 0, 0, self.on_entry_highlighted)

    def on_entry_highlighted(self, i):
        if i >= 0:
            entry = self.results[i]
            txt = MARKDOWN_TEMPLATE.safe_substitute(entry)
            self.window.run_command("show_panel", {"panel": "output.DBLP"})
            panel = self.window.get_output_panel('DBLP')
            syntax = sublime.find_resources("Markdown.tmLanguage") + sublime.find_resources("Markdown.sublime-syntax")
            if syntax:
                panel.set_syntax_file(syntax[0])
            panel.run_command('dblp_insert', {'characters': txt})
            panel.sel().clear()
            panel.settings().set('draw_centered', False)


    def on_entry_selected(self, i):
        self.on_entry_highlighted(i)

    def on_error(self, err):
        sublime.error_message("DBLP Search error: %s" % err)

    def run(self, edit, query_snippet=None, query=None, slurp=True, **kwargs):
        self.args = kwargs
        self.window = self.view.window()
        if query is None and slurp and len(self.view.sel()) > 0:
            query = self.view.substr(self.view.sel()[0])
        if query:
            self.on_query(query)
        else:
            prompt = self.window.show_input_panel("DBLP Search:", "", self.on_query, None, None)
            if query_snippet:
                prompt.run_command("insert_snippet", {"contents", query_snippet})

    def is_enabled(self, **kwargs):
        if 'selector' in kwargs:
            pt = self.view.sel()[0].a if len(self.view.sel()) > 0 else 0
            return self.view.score_selector(pt, kwargs['selector']) > 0
        return True


class DblpInsertKey(DblpSearchCommand):

    def on_entry_selected(self, i):
        self.window.run_command("hide_panel", {"panel": "output.DBLP"})
        if i >= 0:
            citation = self.args.get('template', '${cite_key}')
            citation = Template(citation)
            if self.args.get("next_line"):
                region = self.view.sel()[0]
                region = sublime.Region(self.view.full_line(region).end())
                self.view.sel().clear()
                self.view.sel().add(region)
            self.view.run_command(
                "insert_snippet",
                {"contents": citation.safe_substitute(self.results[i])})


DBLP_FORMATS = set(['bibtex', 'bibtex_std', 'bibtex_crossref', 'bib0', 'bib1', 'bib2', 'xml', 'rdf'])
FORMAT_MAP = {
    'bibtex': 'bib0',
    'bibtex_std': 'bib1',
    'bibtex_crossref': 'bib2'
}


class DblpInsertCitation(DblpSearchCommand):

    def on_entry_selected(self, i):
        self.window.run_command("hide_panel", {"panel": "output.DBLP"})
        if i >= 0:
            entry = self.results[i]
            format = self.args.get('format', 'bibtex')
            if format not in DBLP_FORMATS:
                citation = self.args.get('template', MARKDOWN_CITATION)
                citation = Template(citation)
                self.view.run_command(
                    "insert_snippet",
                    {'contents': citation.safe_substitute(entry)})
            else:
                format = FORMAT_MAP.get(format, format)
                url = "http://www.dblp.org/rec/%s/%s" % (format, entry['key'])
                LOG(url)
                try:
                    data = urlopen(url).read()
                    enc = self.view.encoding()
                    enc = enc if enc != 'Undefined' else 'utf8'
                    data = data.decode(enc)
                    if self.args.get('simple_key', True):
                        try:
                            simple_key = entry['key'].split('/')[-1]
                            data = data.replace('DBLP:'+entry['key'], simple_key, 1)
                        except Exception:
                            print("DBLP plugin could not simplify key: ", str(e))
                    self.view.run_command(
                        "dblp_insert",
                        {'characters': data})
                except Exception as e:
                    sublime.status_message("DBLP Error: %s" % e)



BIBTEX_DOI_FIELD = "\tdoi = {${doi}},\n"

class DblpQueryInsertCommand(sublime_plugin.TextCommand):

    def run(self, edit, doi_template=BIBTEX_DOI_FIELD, necessary=["doi"], queries=None, max_hits=3, add_all=True, **kwargs):
        if queries is None:
            queries = [self.view.substr(s) for s in self.view.sel() if len(s)]
            # TODO: parse line as bibtex
        doi_template = Template(doi_template)
        lines = [self.view.full_line(s) for s in self.view.sel()]
        LOG(queries)
        while len(queries):
            query = queries.pop()
            line = lines.pop()
            try:
                url = dblp_search_url(query, max_hits)
                hits = dblp_fetch(url)
                if not add_all: hits = [hits[0]]
                for hit in hits:
                    entry = dblp_parse_hit(hit)
                    if all(entry.get(f) for f in necessary):
                        txt = doi_template.safe_substitute(entry)
                        self.view.insert(edit, line.end(), txt)
                        LOG("Query %s succeeded: %s" % (query, txt))
            except Exception as e:
                LOG("Failed query %s: %s" % (query, e))

    def _launch_next_search(self):
        if len(self._queries) > 0:
            q = self._queries.pop()
            self._queryThread = SearchDBLPThread(q, 1, self.on_search_results, self.on_error)
            self._queryThread.start()

    # def on_search_results(self, results):
    #     if len(results) == 0:
    #         sublime.status_message('DBLP returned no results for your search!')
    #         return
    #     line = self._lines.pop()
    #     entry = results[0]
    #     txt = self._doi_template.safe_substitute(entry)
    #     self.
    #     self._launch_next_search()

    def on_error(self, err):
        sublime.error_message("DBLP Search error: "+err)


class DblpInsertCommand(sublime_plugin.TextCommand):

    def run(self, edit, characters="", next_line=False):
        if len(self.view.sel()) > 0:
            region = self.view.sel()[0]
            if next_line:
                region = sublime.Region(self.view.full_line(region).end())
        else:
            region = sublime.Region(0, 0)
        self.view.replace(edit, region, characters)
