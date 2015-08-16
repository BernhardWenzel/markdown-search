# Search engine for local markdown files with tagging

This is a local search engine that is optimized for markdown files. It takes advantage of markdown syntax by giving boost to words in headlines, emphasis and other markup. One special feature is that it treats the first line of a markdown file as a list of **tags** (this behaviour is configurable, this line can be prefixed with a term or switched off).
  
Implemented in **Python** using **Flask**, **Whoosh** and **Mistune**.

## Installation

Clone/fork project. Rename `config.py.sample` to `config.py` and adjust the properties. It's only necessary to change the path to your markdown files directory.

    # Path to markdown files
    MARKDOWN_FILES_DIR = "/home/user/wiki"

The search engine will index all files in this folder and it's subdirectories. 

Install the Python requirements. Preferably in a virtualenv, run `pip install -r requirements.

## Run search engine

Just run `python search-app.py` and open <http://127.0.0.1:5000> in a browser.

## Usage

### Build/update index

Click on the `[Update index]` link to re-build the search index. The location of the index can be configured in `config.py` by setting `INDEX_DIR`.

## Tags

The first line of a markdown file is treated as a list of tags. How this is done can be configured by changing the regex in `config.py`

    # Regular expression to select tags, eg tag has to start with alphanumeric followed by at least two alphanumeric or "-" or "."
    TAGS_REGEX = r"\b([A-Za-z0-9][A-Za-z0-9-.]{2,})\b"

Tags can be switched of or can be prefixed (e.g. "tags:"). If prefixed, the tags can be defined in any location of a file.

### Show all tags

At the beginning or when clicking on `[Clear]` or the link `Seach Directory: ...` all tags that are indexed are shown.

![Show all tags](http://bernhardwenzel.com/assets/images/markdown-search/search-cleared.jpg)


### Searching

Type in the query as you would in any other search engine. The syntax is defined by the Whoosh library. To debug the actual query, it is displayed under the search input field (this can also be switched off). 

![Search](http://bernhardwenzel.com/assets/images/markdown-search/search.jpg)

### Searching for tags only

Every search result displays the tags of a file and related tags to the query. Clicking on one tags search for this tag only. Alternatively, check the `only tags` checkbox.

![Search](http://bernhardwenzel.com/assets/images/markdown-search/search.jpg)

It is also possible to just search in the path name of a file, select `only file names` checkbox.

## Open a file in your local editor

Under the tags of a search result is the path of that file. By clicking on the link it can be opened in your default editor. The command to run the path with is defined in the configuration with `EDIT_COMMAND`. This has been tested on MacOS (Windows at least probably requires to specify the path to an executable).With the default setting, if clicking on the path the following command is executed: `edit <PATH>`

## Last searches

On the bottom of the search result page is a list of the last searches. They are stored in a plain text file named `last_searches.txt`

## Schema

The search schema is defined in `search.py`. Adjust it if you want to give a different boost to fields.

```python search.py
class Search:
    def open_index(self, index_folder, create_new=False):
        schema = Schema(
            path=ID(stored=True, unique=True)
            , filename=TEXT(stored=True, field_boost=100.0)
            , tags=KEYWORD(stored=True, scorable=True, field_boost=80.0)
            , headlines=KEYWORD(stored=True, field_boost=60.0)
            , doubleemphasiswords=KEYWORD(stored=True, field_boost=40.0)
            , emphasiswords=KEYWORD(stored=True, field_boost=20.0)
            , content=TEXT(stored=True)
        )
```
  
If you want to learn more about the project, have a look at the related post: <http://bernhardwenzel.com/2015-08-17-searching-local-markdown-files>


