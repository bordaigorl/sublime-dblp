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

if "urlencode" in urllib.__dict__:
    urlencode = urllib.urlencode
else:
    urlencode = urllib.parse.urlencode


POST_PARAMS = {
    "accc": ":",
    "bnm": "A",
    "deb": "0",
    "dm": "3",
    "eph": "1",
    "er": "20",
    "fh": "1",
    "fhs": "1",
    "hppwt": "20",
    "hppoc": "100",
    "hrd": "1a",
    "hrw": "1d",
    "language": "en",
    "ll": "2",
    "log": "/var/log/dblp/error_log",
    "mcc": "0",
    "mcl": "80",
    "mcs": "1000",
    "mcsr": "40",
    "mo": "100",
    "name": "dblpmirror",
    "navigation_mode": "user",
    "page": "index.php",
    "path": "/search/",
    "qi": "3",
    "qid": "3",
    "qt": "H",
    "rid": "6",
    "syn": "0"
}

KEY_PARSER = re.compile(r"""
    <tr>
      <td.*?>
        <a\ href=\"http://www\.dblp\.org/rec/bibtex/(.*?)\">
        .*?
      </td>
      <td.*?>(.*?)</td><td.*?>(.*?)</td>
    </tr>
    """, re.VERBOSE)


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
            conn = httplib.HTTPConnection("dblp.org")
            POST_PARAMS['query'] = self.query
            params = urlencode(POST_PARAMS)
            headers = {"Content-type": "application/x-www-form-urlencoded"}
            conn.request("POST", "/autocomplete-php/autocomplete/ajax.php", params, headers)
            response = conn.getresponse()
            if response.status == 200:
                data = response.read().decode("utf-8")
                LOG(data)
                parsed_data = (data.split("\n")[30].split("=", 1)[1])
                # mangle ill formed json
                parsed_data = parsed_data.replace("'", "\"")[:-1]
                parsed_data = json.loads(parsed_data)

                LOG(parsed_data)

                body = parsed_data["body"]

                result = []
                # Filter the relevant information:
                for match in KEY_PARSER.finditer(body):
                    LOG(match.group(1))
                    title = strip_tags(match.group(3))
                    authors, title = title.split(":", 1)
                    result.append({
                        'key': match.group(1),
                        'title': title,
                        'authors': authors,
                        'cite_key': u"DBLP:" + match.group(1)
                        })

                if self.on_search_results:
                    self.on_search_results(result)

            elif self.on_error:
                LOG('Error %s' % response.reason())
                self.on_error(response.reason())
        except Exception as e:
            raise
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
        menu = [[x['title'], x['authors'], x['cite_key']] for x in results]
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
            citation = self.args.get('template', '{cite_key}')
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
