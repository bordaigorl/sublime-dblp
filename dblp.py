import sublime
import sublime_plugin

# Sublime Text 3 Python 3 compatibility
try:
    import httplib
except ImportError:
    import http.client as httplib

import urllib
import json
import re

import threading

DEBUG = True


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


class SearchDBLPThread(threading.Thread):

    def __init__(self, query, on_search_results=None, on_error=None):
        threading.Thread.__init__(self)
        self.query = query
        self.on_search_results = on_search_results
        self.on_error = on_error

    def stop(self):
        if self.isAlive():
            self._Thread__stop()

    def run(self):
        try:
            url = "http://dblp.org/search/api/?format=json&q=" + urlquote(self.query)
            data = urlopen(url).read().decode()
            data = json.loads(data)
            data = data['result']
            sublime.status_message("DBLP Search done in %s%s" % (data['time']['text'], data['time']['@unit']))

            hits = data['hits'].get('hit', [])
            result = []
            for hit in hits:
                info = hit.get('info')
                entry_url = hit.get('url')
                authors = info['authors']['author']
                if info and entry_url:
                    key = entry_url.replace('http://www.dblp.org/rec/bibtex/', '')
                    result.append({
                            'key': key,
                            'cite_key': u"DBLP:" + key,
                            'title': info['title']['text'],
                            'year': info['year'],
                            'venue': info['venue']['text'],
                            'authors': entityDecode(', '.join(authors))
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


class DblpSearch(sublime_plugin.TextCommand):

    _queryThread = None

    def on_query(self, q):
        if len(q) > 3:
            if self._queryThread is not None:
                LOG("Starting Thread...")
                self._queryThread.stop()
            self._queryThread = SearchDBLPThread(q, self.on_search_results, self.on_error)
            self._queryThread.start()

    def on_search_results(self, results):
        if len(results) == 0:
            sublime.status_message('DBLP returned no results for your search!')
            return
        self.results = results
        menu = [[x['title'], '%s (%s)' % (x['authors'], x['year']), x['cite_key']] for x in results]
        self.window.show_quick_panel(menu, self.on_entry_selected)

    def on_entry_selected(self, i):
        pass

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
        if len(self.view.sel()) > 0 and 'selector' in kwargs:
            return self.view.score_selector(self.view.sel()[0].a, kwargs['selector']) > 0
        return True


class DblpInsertKey(DblpSearch):

    def on_entry_selected(self, i):
        if i >= 0:
            citation = self.args.get('snippet', '{cite_key}')
            self.view.run_command("insert", {"characters": citation.format(**self.results[i])})


FORMAT_MAP = {
    'bibtex': 'bib1',
    'bibtex_crossref': 'bib2'
}


class DblpInsertCitation(DblpSearch):

    def on_entry_selected(self, i):
        if i >= 0:
            entry = self.results[i]
            format = self.args.get('format', 'bibtex')
            format = FORMAT_MAP.get(format, format)
            url = "http://www.dblp.org/rec/%s/%s" % (format, entry['key'])
            LOG(url)
            try:
                data = urlopen(url).read()
                self.view.run_command("dblp_insert", {'characters': data.decode(self.view.encoding())})
            except Exception as e:
                sublime.status_message("DBLP Error: %s" % e)


class DblpInsertCommand(sublime_plugin.TextCommand):

    def run(self, edit, characters=""):
        if len(self.view.sel()) > 0:
            region = self.view.sel()[0]
        else:
            region = sublime.Region(0,0)
        self.view.replace(edit, region, characters)
