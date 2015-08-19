import shutil
import HTMLParser

from markdown_parser import MarkdownParser
import mistune
from whoosh.fields import *
import whoosh.index as index
import os
import os.path
import codecs
from whoosh.qparser import MultifieldParser, QueryParser
from whoosh.analysis import StemmingAnalyzer

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
        stemming_analyzer = StemmingAnalyzer()

        schema = Schema(
            path=ID(stored=True, unique=True)
            , filename=TEXT(stored=True, field_boost=100.0)
            , tags=KEYWORD(stored=True, scorable=True, field_boost=80.0)
            , headlines=KEYWORD(stored=True, scorable=True, field_boost=60.0)
            , doubleemphasiswords=KEYWORD(stored=True, scorable=True, field_boost=40.0)
            , emphasiswords=KEYWORD(stored=True, scorable=True, field_boost=20.0)
            , content=TEXT(stored=True, analyzer=stemming_analyzer)
            , time=STORED
        )
        if not exists:
            self.ix = index.create_in(index_folder, schema)
        else:
            self.ix = index.open_dir(index_folder)

    def add_document(self, writer, file_path, config):
        file_name = unicode(file_path.replace(".", " ").replace("/", " ").replace("\\", " ").replace("_", " ").replace("-", " "), encoding="utf-8")
        # read file content
        with codecs.open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            path = unicode(file_path, "utf-8")

        # parse markdown fields
        parser = MarkdownParser()
        parser.parse(content, config)

        modtime = os.path.getmtime(path)
        print "adding to index: path: %s size:%d tags:'%s' headlines:'%s' modtime=%d" % (
            path, len(content), parser.tags, parser.headlines, modtime)
        writer.add_document(
            path=path
            , filename=file_name
            , headlines=parser.headlines
            , tags=parser.tags
            , content=content
            , doubleemphasiswords=parser.doubleemphasiswords
            , emphasiswords=parser.emphasiswords
            , time = modtime
        )


    def add_all_files(self, file_dir, config, create_new_index=False):
        if create_new_index:
            self.open_index(self.index_folder, create_new=True)

        count = 0
        writer = self.ix.writer()
        for root, dirs, files in os.walk(file_dir, followlinks=True):
            for file in files:
                if file.endswith(".md") or file.endswith("markdown"):
                    path = os.path.join(root, file)
                    self.add_document(writer, path, config)
                    count += 1
        writer.commit()
        print "Done, added %d documents to the index" % count

    def update_index_incremental(self, config, create_new_index=False):
        file_dir = config["MARKDOWN_FILES_DIR"]
        if create_new_index:
            self.open_index(self.index_folder, create_new=True)

        all_files = []
        for root, dirs, files in os.walk(file_dir, followlinks=True):
            for file in files:
                if file.endswith(".md") or file.endswith("markdown"):
                    path = os.path.join(root, file)
                    all_files.append(path)

        # see: https://pythonhosted.org/Whoosh/indexing.html#incremental-indexing
        # The set of all paths in the index
        indexed_paths = set()
        # The set of all paths we need to re-index
        to_index = set()

        count = 0
        with self.ix.searcher() as searcher:
            writer = self.ix.writer()

            # Loop over the stored fields in the index
            for fields in searcher.all_stored_fields():
                indexed_path = fields['path']
                indexed_paths.add(indexed_path)

                if not os.path.exists(indexed_path):
                    # This file was deleted since it was indexed
                    writer.delete_by_term('path', indexed_path)
                    print "removed from index: %s" % indexed_path

                else:
                    # Check if this file was changed since it
                    # was indexed
                    indexed_time = fields['time']
                    mtime = os.path.getmtime(indexed_path)
                    if mtime > indexed_time:
                        # The file has changed, delete it and add it to the list of
                        # files to reindex
                        writer.delete_by_term('path', indexed_path)
                        to_index.add(indexed_path)

            # Loop over the files in the filesystem
            for path in all_files:
                if path in to_index or path not in indexed_paths:
                    # This is either a file that's changed, or a new file
                    # that wasn't indexed before. So index it!
                    self.add_document(writer, path, config)
                    count += 1

            writer.commit()

            print "Done, updated %d documents in the index" % count

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
            query = None
            if "\"" in query_string or ":" in query_string:
                query = QueryParser("content", self.schema).parse(query_string)
            elif len(fields) == 1 and fields[0] == "filename":
                pass
            elif len(fields) == 1 and fields[0] == "tags":
                pass
            elif len(fields) == 2:
                pass
            else:
                fields = ["tags", "headlines", "content", "filename", "doubleemphasiswords", "emphasiswords"]
            if not query:
                query = MultifieldParser(fields, schema=self.ix.schema).parse(query_string)
            parsed_query = "%s" % query
            print "query: %s" % parsed_query
            results = searcher.search(query, terms=False, scored=True, groupedby="path")
            key_terms = results.key_terms("tags", docs=100, numterms=100)
            tag_cloud = [keyword for keyword, score in key_terms]
            search_result = self.create_search_result(results)

        return parsed_query, search_result, tag_cloud

    def get_document_total_count(self):
        return self.ix.searcher().doc_count_all()

if __name__ == "__main__":
    search = Search("search_index")
    search.add_all_files("/Volumes/data/doc/wiki/dev")
