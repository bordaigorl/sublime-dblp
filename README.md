# DBLP for Sublime Text

A plugin for SublimeText 3 for working with [DBLP][dblp], the Computer Science Bibliography.

DBLP for Sublime Text can be installed directly using [Package Control][pc].


## Features

The plugin offers the following commands (available from the Command Palette).

### DBLP: Lookup

It asks the user for a query and searches DBLP for papers matching it.
Then a quick panel is displayed with the results.
When a result is selected, a panel at the bottom shows the corresponding entry (in Markdown syntax).


### DBLP: Insert Citation Key

After doing a lookup, the citation key of the selected entry is inserted in the current view.


### DBLP: Insert `\cite` Command

After doing a lookup, the citation key of the selected entry is inserted in the current view, wrapped in a `\cite` macro.
For use with LaTeX documents.


### DBLP: Insert Citation Entry (BibTeX)

After doing a lookup, the full citation *entry* of the selected record is inserted in the current view, in BibTeX format.


### DBLP: Insert Citation Entry (Markdown)

After doing a lookup, the full citation *entry* of the selected record is inserted in the current view, in Markdown format.


### DBLP: Insert Citation Entry (XML)

After doing a lookup, the full citation *entry* of the selected record is inserted in the current view, in XML format.


## Shortcuts

You can install a keyboard shortcut by adding variations of the following

    {
        "keys": ["ctrl+d", "ctrl+k"],
        "command": "dblp_search",
        "context": [
            {"key": "selector", "operand": "text.tex.latex", "operator": "equal"}
        ]
    },
    {
        "keys": ["ctrl+d", "ctrl+c"],
        "command": "dblp_insert_citation",
        "args": {"format": "bibtex"},
        "context": [
            {"key": "selector", "operand": "text.bibtex", "operator": "equal"}
        ]
    },
    {
        "keys": ["ctrl+d", "ctrl+c"],
        "command": "dblp_insert_citation",
        "args": {"format": "xml"},
        "context": [
            {"key": "selector", "operand": "text.xml", "operator": "equal"}
        ]
    }

to your user key bindings.


## Advanced usage

The `dblp_search` offers two additional arguments:

 * `query_snippet`: the snippet initially filling the input panel for the search query (can be a ST snippet);
 * `query`: the query itself. If this argument is specified, no input is asked to the user and the search is performed straight away;
 * `max_hits`: the maximum number of results shown in the quick panel (default 500).


The `dblp_insert_citation` offers advanced arguments:

 * `query_snippet`, `query` and `max_hits` as above;
 * `format`: the format for the citation (default `bibtex`).
   It could be any of:
     - the DBLP provided `bibtex`, `bibtex_std`, `bibtex_crossref`, `bib0`, `bib1`, `bib2`, `xml`, `rdf`
     - `markdown`
     - a custom format for which you have to set the template argument (see below).
 * `template`: a template string using any of the fields `key`, `cite_key`, `title`, `year`, `venue`, `authors` and `url`.
     This is only used if the format is not one of the DBLP supported ones.
     The default template is a Markdown entry:

         # ${title}
           > ${authors}
             ${venue} (${year})
           [${key}](${url})
         

This plugin can be used in conjunction with [rDBLP][rdblp] to automatically maintain
your bib files for your current publication.

## Acknowledgements

This plugin is a fork of the [DBLP Search](https://github.com/grundprinzip/sublime-dblp) plugin for ST2, but it evolved as a complete rewrite.

- - -

> The DBLP service provides open bibliographic information on major computer science journals and proceedings.
DBLP is a joint service of the [University of Trier][trier] and [Schloss Dagstuhl][dagstuhl].
For more information check out their [F.A.Q](http://dblp.dagstuhl.de/faq/).

- - -


[dblp]: http://dblp.org
[rdblp]: https://github.com/grundprinzip/dblp
[pc]: http://wbond.net/sublime_packages/package_control
[trier]: http://www.uni-trier.de/?L=2
[dagstuhl]: http://www.dagstuhl.de/en
