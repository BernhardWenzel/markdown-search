import mistune
import re

# http://mistune.readthedocs.org/en/latest/

class ParsingRenderer(mistune.Renderer):
    def __init__(self, **kwargs):
        super(ParsingRenderer, self).__init__(**kwargs)
        self.blocks = []
        self.headlines = u''
        self.doubleemphasiswords=u''
        self.emphasiswords=u''

    def block_code(self, code, lang):
        self.blocks.append(code)
        return super(ParsingRenderer, self).block_code(code, lang)

    def header(self, text, level, raw=None):
        self.headlines += "%s " % raw.lower()
        return super(ParsingRenderer, self).header(text, level, raw)

    def double_emphasis(self, text):
        self.doubleemphasiswords += "%s " % text.lower()
        return super(ParsingRenderer, self).double_emphasis(text)

    def emphasis(self, text):
        self.emphasiswords += "%s " % text.lower()
        return super(ParsingRenderer, self).emphasis(text)

class MarkdownParser:
    def __init__(self):
        self.blocks = []
        self.headlines = u''
        self.tags = u''
        self.doubleemphasiswords=u''
        self.emphasiswords=u''

    def parse(self, markdown_text, tags_prefix='', tags_regex='[^a-zA-Z\d\s]+'):
        renderer = ParsingRenderer()
        markdown = mistune.Markdown(renderer=renderer)
        markdown(markdown_text)
        self.blocks = renderer.blocks
        self.headlines = renderer.headlines if renderer.headlines.strip() else u''
        self.tags = self.get_tags_line(markdown_text, tags_prefix, tags_regex)

    def get_tags_line(self, markdown_text, tags_prefix, tags_regex):
        if len(markdown_text):
            tags_line = u''
            if tags_prefix:
                # find tags line
                for l in markdown_text.split("\n"):
                    if l.startswith(tags_prefix):
                        tags_line = l.replace(tags_prefix, "")
            else:
                # first line of content
                tags_line = markdown_text.split("\n", 1)[0]

            # only lower case
            tags_line = tags_line.lower()
            # apply regex
            pattern = re.compile(tags_regex, re.UNICODE)
            tags = pattern.findall(tags_line)
            if tags:
                return " ".join([t for t in tags])

        return u''