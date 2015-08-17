from glob import glob
import codecs
import os
import threading
from subprocess import call

from flask import Flask, request, redirect, url_for, render_template, flash

# create our little application :)
from search import Search

class UpdateIndexTask(object):
    def __init__(self):
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def run(self):
        search = Search(app.config["INDEX_DIR"])
        search.add_all_files(app.config["MARKDOWN_FILES_DIR"], tags_prefix=app.config["TAGS_PREFIX"], create_new_index=True, tags_regex=app.config["TAGS_REGEX"])

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.from_pyfile("config.py")

@app.route('/')
def index():
    return redirect(url_for("search", query="", fields=""))

@app.route('/search')
def search():
    query = request.args['query']
    fields = request.args.get('fields')
    if fields == 'None':
        fields = None

    directories = []
    search = Search(app.config["INDEX_DIR"])
    if not query:
        tag_cloud = search.get_tags()
        parsed_query = ""
        result = []
        directories=get_directories()

    else:
        parsed_query, result, tag_cloud = search.search(query.split(), fields=[fields])
        store_search(query, fields)

    return render_template('search.html', entries=result, query=query, parsed_query=parsed_query, fields=fields, tag_cloud=tag_cloud, last_searches=get_last_searches(), directories=directories)

@app.route('/open')
def open_file():
    path = request.args['path']
    fields = request.args.get('fields')
    query = request.args['query']
    call([app.config["EDIT_COMMAND"], path])

    return redirect(url_for("search", query=query, fields=fields))

@app.route('/update_index')
def update_index():
    UpdateIndexTask()
    flash("Updating index, check console output")
    store_directories()
    return render_template("search.html", query="", fields="")


def get_last_searches():
    if os.path.exists("last_searches.txt"):
        f = open("last_searches.txt", "r")
        contents = f.readlines()
        f.close()
    else:
        contents = []
    return contents

def get_directories():
    if os.path.exists("directories.txt"):
        f = open("directories.txt", "r")
        directories = f.readlines()
        f.close()
    else:
        directories = []
    return directories

def store_search(query, fields):
    if os.path.exists("last_searches.txt"):
        with codecs.open("last_searches.txt", 'r', encoding='utf8') as f:
            contents = f.readlines()
    else:
        contents = []

    search = "query=%s&fields=%s\n" % (query, fields)
    if not search in contents:
        contents.insert(0, search)

    with codecs.open("last_searches.txt", 'w', encoding='utf8') as f:
        f.writelines(contents[:30])

def store_directories():
    directories = []
    for root, dirnames, files in os.walk(app.config["MARKDOWN_FILES_DIR"]):
        if dirnames:
            for d in dirnames:
                if os.path.isdir(os.path.join(root, d)):
                    directories.append("%s\n" % unicode(d.lower()))
    directories = sorted(set(directories))
    with codecs.open("directories.txt", 'w', encoding='utf8') as f:
        f.writelines(directories)

if __name__ == '__main__':
    app.run()
