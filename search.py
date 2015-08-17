from markdown_parser import MarkdownParser
import mistune
from whoosh.fields import *
import whoosh.index as index
import os
import os.path
import codecs
from whoosh.qparser import MultifieldParser, QueryParser
import shutil
import HTMLParser
from whoosh.query import Phrase


class SearchResult:
    score = 1.0
    path = None
    content = ""
    content_highlight = ""
    headlines = None
    tags = ""


class DontEscapeHtmlInCodeRenderer(mistune.Renderer):
    def __init__(self, **kwargs):
        super(DontEscapeHtmlInCodeRenderer, self).__init__(**kwargs)

    def block_code(self, code, lang):
        if not lang:
            return '<pre><code>%s\n</code></pre>\n' % code
        return '<pre><code class="lang-%s">%s\n</code></pre>\n' % (lang, code)

    def codespan(self, text):
        return '<code>%s</code>' % text.rstrip()


class Search:
    ix = None
    index_folder = None
    markdown = mistune.Markdown(renderer=DontEscapeHtmlInCodeRenderer(), escape=False)
    html_parser = HTMLParser.HTMLParser()
    schema = None

    def __init__(self, index_folder):
        self.open_index(index_folder)

    def open_index(self, index_folder, create_new=False):
        self.index_folder = index_folder
        if create_new:
            if os.path.exists(index_folder):
                shutil.rmtree(index_folder)
                print "deleted index folder: " + index_folder

        if not os.path.exists(index_folder):
            os.mkdir(index_folder)

        exists = index.exists_in(index_folder)
        schema = Schema(
            path=ID(stored=True, unique=True)
            , filename=TEXT(stored=True, field_boost=100.0)
            , tags=KEYWORD(stored=True, scorable=True, field_boost=80.0)
            , headlines=KEYWORD(stored=True, field_boost=60.0)
            , doubleemphasiswords=KEYWORD(stored=True, field_boost=40.0)
            , emphasiswords=KEYWORD(stored=True, field_boost=20.0)
            , content=TEXT(stored=True)
        )
        if not exists:
            self.ix = index.create_in(index_folder, schema)
        else:
            self.ix = index.open_dir(index_folder)

    def add_document(self, file_path, tags_prefix='', tags_regex='\b[A-Za-z0-9][A-Za-z0-9-.]+\b'):
        base = os.path.basename(file_path)
        file_name = unicode(file_path.replace(".", " ").replace("/", " ").replace("\\", " "), encoding="utf-8")
        writer = self.ix.writer()
        # read file content
        with codecs.open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            path = unicode(file_path, "utf-8")

        # parse markdown fields
        parser = MarkdownParser()
        parser.parse(content, tags_prefix=tags_prefix, tags_regex=tags_regex)

        writer.add_document(
            path=path
            , filename=file_name
            , headlines=parser.headlines
            , tags=parser.tags
            , content=content
            , doubleemphasiswords=parser.doubleemphasiswords
            , emphasiswords=parser.emphasiswords
        )
        print "adding to index: path: %s size:%d tags:'%s' headlines:'%s'" % (
            path, len(content), parser.tags, parser.headlines)
        writer.commit()

    def add_all_files(self, file_dir, tags_prefix='', create_new_index=False, tags_regex=None):
        if create_new_index:
            self.open_index(self.index_folder, create_new=True)

        count = 0
        for root, dirs, files in os.walk(file_dir, followlinks=True):
            for file in files:
                if file.endswith(".md") or file.endswith("markdown"):
                    path = os.path.join(root, file)
                    self.add_document(path, tags_prefix=tags_prefix, tags_regex=tags_regex)
                    count += 1
        print "Done, added/updated %d documents to the index" % count

    def create_search_result(self, results):
        # Allow larger fragments
        results.fragmenter.maxchars = 300

        # Show more context before and after
        results.fragmenter.surround = 50

        search_results = []
        for r in results:
            sr = SearchResult()
            sr.score = r.score
            sr.tags = r["tags"]
            sr.path = r["path"]
            sr.content = r["content"]
            highlights = r.highlights("content")
            if not highlights:
                highlights = self.cap(r["content"], 1000)
            # unescape
            highlights = self.html_parser.unescape(highlights)
            html = self.markdown(highlights)
            sr.content_highlight = html
            if "headlines" in r:
                sr.headlines = r["headlines"]
            search_results.append(sr)

        return search_results

    def cap(self, s, l):
        return s if len(s) <= l else s[0:l - 3] + '...'

    def get_tags(self):
        with self.ix.searcher() as searcher:
            return list(searcher.lexicon("tags"))

    def search(self, query_list, fields=None):
        with self.ix.searcher() as searcher:
            query_string = " ".join(query_list)
            qp = QueryParser("content", self.schema)
            query = qp.parse(query_string)
            is_phrase_query = isinstance(query, Phrase)
            if len(fields) == 1 and fields[0] == "filename":
                pass
            if len(fields) == 1 and fields[0] == "tags":
                if is_phrase_query:
                    query_string = query_string.replace("\"", "")
            elif is_phrase_query:
                fields = ["content", "filename"]
            else:
                fields = ["tags", "headlines", "content", "filename", "doubleemphasiswords", "emphasiswords"]
            query = MultifieldParser(fields, schema=self.ix.schema).parse(query_string)
            parsed_query = "%s" % query
            print "query: %s" % parsed_query
            results = searcher.search(query, terms=False, scored=True, groupedby="path")
            key_terms = results.key_terms("tags", docs=100, numterms=100)
            tag_cloud = [keyword for keyword, score in key_terms]
            search_result = self.create_search_result(results)

        return parsed_query, search_result, tag_cloud

if __name__ == "__main__":
    search = Search("search_index")
    search.add_all_files("/Volumes/data/doc/wiki/dev")
