# DBLP Search for Sublime

This plugin for SublimeText 2 is a small extension for working with  LaTeX
documents. It allows you to define a query to DBLP and will present  you with a
list of matching papers. Selecting a paper will insert the necessary DBLP
citation key.

This can be used in conjunction with [rDBLP][dblp] to automatically maintain
your bib files for your current publication.

You can install a keyboard shortcut by adding

    {
        "keys": ["ctrl+.", "ctrl+d"],
        "command": "dblp_search",
        "context": [
            {"key": "selector", "operand": "text.tex.latex", "operator": "equal"}
        ]
    }

to your user key bindings.

DBLP Search for Sublime can now be installed directly using the [Package Control][pc].

[dblp]: https://github.com/grundprinzip/dblp
[pc]: http://wbond.net/sublime_packages/package_control
