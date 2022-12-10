import threading
from subprocess import call

import codecs
import os
from flask import Flask, request, redirect, url_for, render_template, flash


# create our little application :)
from search import Search

class UpdateIndexTask(object):
    def __init__(self, rebuild_index=False):
        self.rebuild_index = rebuild_index
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def run(self, rebuild_index=False):
        search = Search(app.config["INDEX_DIR"])
        search.update_index_incremental(app.config, create_new_index=self.rebuild_index)

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.from_pyfile("config.py")

last_searches_file = app.config["INDEX_DIR"] + "/last_searches.txt"
directories_file = app.config["INDEX_DIR"] + "/directories.txt"

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

    total = search.get_document_total_count()

    return render_template('search.html', entries=result, query=query, parsed_query=parsed_query, fields=fields, tag_cloud=tag_cloud, last_searches=get_last_searches(), directories=directories, total=total)

@app.route('/open')
def open_file():
    path = request.args['path']
    fields = request.args.get('fields')
    query = request.args['query']
    call([app.config["EDIT_COMMAND"], path])

    return redirect(url_for("search", query=query, fields=fields))

@app.route('/update_index')
def update_index():
    rebuild = request.args.get('rebuild')
    if rebuild:
        UpdateIndexTask(rebuild_index=True)
        flash("Rebuilding index, check console output")
    else:
        UpdateIndexTask()
        flash("Updating index, check console output")
    store_directories()
    return render_template("search.html", query="", fields="", last_searches=get_last_searches())


def get_last_searches():
    if os.path.exists(last_searches_file):
        with codecs.open(last_searches_file, 'r', encoding='utf-8') as f:
            contents = f.readlines()
    else:
        contents = []
    return contents

def get_directories():
    if os.path.exists(directories_file):
        with codecs.open(directories_file, 'r', encoding='utf-8') as f:
            directories = f.readlines()
            f.close()
    else:
        directories = []
    return directories

def store_search(query, fields):
    if os.path.exists(last_searches_file):
        with codecs.open(last_searches_file, 'r', encoding='utf-8') as f:
            contents = f.readlines()
    else:
        contents = []

    search = "query=%s&fields=%s\n" % (query, fields)
    if not search in contents:
        contents.insert(0, search)

    with codecs.open(last_searches_file, 'w', encoding='utf-8') as f:
        f.writelines(contents[:30])

def store_directories():
    directories = []
    for root, dirnames, files in os.walk(app.config["MARKDOWN_FILES_DIR"]):
        if dirnames:
            for d in dirnames:
                if os.path.isdir(os.path.join(root, d)):
                    directories.append(f"{d.lower()}\n")
    directories = sorted(set(directories))
    with codecs.open(app.config["INDEX_DIR"] + "/directories.txt", 'w', encoding='utf-8') as f:
        f.writelines(directories)

if __name__ == '__main__':
    app.run()
