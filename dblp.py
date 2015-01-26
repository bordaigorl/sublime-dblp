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
import functools

import threading

DEBUG = True


def LOG(m):
    if DEBUG:
        print(m)


def strip_tags(value):
    """Returns the given HTML with all tags stripped."""
    return re.sub(r'<[^>]*?>', '', value)


class SearchDBLPThread(threading.Thread):

    def __init__(self, v, q):
        threading.Thread.__init__(self)
        self.query = q
        self.view = v

    def stop(self):
        if self.isAlive():
            self._Thread__stop()

    def run(self):
        conn = httplib.HTTPConnection("dblp.org")
        fun = urllib.urlencode if "urlencode" in urllib.__dict__ else urllib.parse.urlencode
        params = fun({
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
            "query": self.query,
            "rid": "6",
            "syn": "0"
        })

        headers = {"Content-type": "application/x-www-form-urlencoded"}
        conn.request("POST", "/autocomplete-php/autocomplete/ajax.php", params, headers)
        response = conn.getresponse()
        if response.status == 200:
            data = response.read().decode("utf-8")
            parsed_data = (data.split("\n")[30].split("=", 1)[1])
            # mangle ill formed json
            parsed_data = parsed_data.replace("'", "\"")[:-1]
            parsed_data = json.loads(parsed_data)

            regexp = r"<tr><td.*?><a href=\"http://www.dblp.org/rec/bibtex/(.*?)\">.*?</td><td.*?>(.*?)</td><td.*?>(.*?)</td></tr>"

            body = parsed_data["body"]

            result = []
            # Filter the relevant information:
            for match in re.finditer(regexp, body):
                LOG(match.group(1))
                cite_key = u"DBLP:" + match.group(1)
                title = strip_tags(match.group(3))

                authors, title = title.split(":", 1)
                result.append([title, authors, cite_key])

            sublime.set_timeout(functools.partial(do_response,
                                                  result), 1)
            return

        LOG(response.reason())


class DblpInsertResultCommand(sublime_plugin.TextCommand):

    def run(self, edit, text):
        sel = self.view.sel()[0]
        self.view.insert(edit, sel.begin(), "\cite{%s}" % text)


def do_response(data):
    """
    Presents the response of the DBLP Query to the user
    """
    def on_done(i):
        if i == -1:
            return

        cite_key = data[i][2]
        view = sublime.active_window().active_view()
        view.run_command("dblp_insert_result", {"text": cite_key})

    sublime.active_window().show_quick_panel(data, on_done)


class DblpSearchCommand(sublime_plugin.TextCommand):

    _queryThread = None

    def run(self, edit):

        def on_done(q):
            if len(q) > 3:
                if self._queryThread != None:
                    LOG("Starting Thread...")
                    self._queryThread.stop()
                self._queryThread = SearchDBLPThread(self.view, q)
                self._queryThread.start()


        self.view.window().show_input_panel("DBLP Search:", "", on_done, None, None)




