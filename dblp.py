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

if 'request' in urllib.__dict__:
    urlopen = urllib.request.urlopen
else:
    urlopen = urllib.urlopen

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
    elif field is None:
        return entityDecode(default)
    else:
        return entityDecode(field.get("text", default))

class SearchDBLPThread(threading.Thread):

    def __init__(self, query, max_hits, on_search_results=None, on_error=None):
        threading.Thread.__init__(self)
        self.query = query
        self.max_hits = max_hits
        self.on_search_results = on_search_results
        self.on_error = on_error

    def stop(self):
        if self.isAlive():
            self._Thread__stop()

    def run(self):
        try:
            self.query = self.query.replace("'", " ").replace(",", " ")
            url = "http://dblp.dagstuhl.de/search/publ/api?format=json&q=%s&h=%s"
            url = url % (urlquote(self.query), self.max_hits)
            LOG(url)
            data = urlopen(url).read().decode()
            data = json.loads(data)
            data = data['result']
            sublime.status_message(
                "DBLP Search done in %s%s" % (data['time']['text'], data['time']['@unit']))

            hits = data['hits'].get('hit', [])
            result = []
            for hit in hits:
                info = hit.get('info')
                LOG(hit.get("@id", "") + " - " + str(info))
                # entry_url = hit.get('url') # OLD API
                entry_url = info.get('url') if info else None
                authors = info.get('authors', {}).get('author', ["No Author"])
                if isinstance(authors, str):
                    authors = [authors]
                authors = [entityDecode(a) for a in authors]
                title = info.get('title', {})
                if info and entry_url:
                    key = entry_url.replace('http://dblp.org/rec/', '')
                    result.append({
                            'key': key,
                            'cite_key': u"DBLP:" + key,
                            'title': getFieldText(title, "No Title"),
                            'year': info['year'],
                            'venue': getFieldText(info.get('venue', {})),
                            'authors': ', '.join(authors),
                            'url': entry_url
                        })

            if self.on_search_results:
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
            self._queryThread = SearchDBLPThread(q, m, self.on_search_results, self.on_error)
            self._queryThread.start()
        else:
            sublime.status_message('DBLP query is too short!')

    def on_search_results(self, results):
        if len(results) == 0:
            sublime.status_message('DBLP returned no results for your search!')
            return
        self.results = results
        menu = [[x['title'], '%s (%s)' % (x['authors'], x['year']), x['cite_key']] for x in results]
        self.window.show_quick_panel(menu, self.on_entry_selected, 0, 0, self.on_entry_highlighted)

    def on_entry_highlighted(self, i):
        if i >= 0:
            entry = self.results[i]
            txt = MARKDOWN_TEMPLATE.safe_substitute(entry)
            self.window.run_command("show_panel", {"panel": "output.DBLP"})
            panel = self.window.get_output_panel('DBLP')
            syntax = sublime.find_resources("Markdown.tmLanguage")
            if syntax:
                panel.set_syntax_file(syntax[0])
            panel.run_command('dblp_insert', {'characters': txt})
            panel.sel().clear()
            panel.settings().set('draw_centered', False)
        
        
    def on_entry_selected(self, i):
        self.on_entry_highlighted(i)

    def on_error(self, err):
        sublime.error_message("DBLP Search error: "+err)

    def run(self, edit, query_snippet=None, query=None, **kwargs):
        self.args = kwargs
        self.window = self.view.window()
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
                    self.view.run_command(
                        "dblp_insert",
                        {'characters': data.decode(enc)})
                except Exception as e:
                    sublime.status_message("DBLP Error: %s" % e)


class DblpInsertCommand(sublime_plugin.TextCommand):

    def run(self, edit, characters=""):
        if len(self.view.sel()) > 0:
            region = self.view.sel()[0]
        else:
            region = sublime.Region(0, 0)
        self.view.replace(edit, region, characters)
