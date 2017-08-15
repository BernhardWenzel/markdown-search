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

index_dir = app.config["INDEX_DIR"]
settings_dir = app.config["SETTINGS_DIR"]
if not os.path.exists(settings_dir):
    os.makedirs(settings_dir)
last_searches_file = index_dir + "/last_searches.txt"
directories_file = index_dir + "/directories.txt"
favourite_searches_file = settings_dir + "/favourite_searches.txt"
favourite_directories_file = settings_dir + "/favourite_directories.txt"

@app.route('/')
def index():
    return redirect(url_for("search", query="", fields=""))

@app.route('/search')
def search():
    query = request.args['query']
    fields = request.args.get('fields')
    if fields == 'None' or not fields:
        fields = []

    directories = []
    search = Search(index_dir)
    favourite_searches = read_storage(favourite_searches_file)
    favourite_directories = read_storage(favourite_directories_file)
    last_searches=read_storage(last_searches_file)
    if not query:
        tag_cloud = search.get_tags()
        parsed_query = ""
        result = []
        directories=read_storage(directories_file)

    else:
        parsed_query, result, tag_cloud = search.search(query.split(), fields=[fields])
        store_search(query, fields)

    total = search.get_document_total_count()

    return render_template('search.html', entries=result, query=query, parsed_query=parsed_query, fields=fields, tag_cloud=tag_cloud, last_searches=last_searches, directories=directories, total=total, favourite_searches=favourite_searches, favourite_directories=favourite_directories)

@app.route('/open')
def open_file():
    path = request.args['path']
    fields = request.args.get('fields')
    query = request.args['query']
    edit_command = app.config["EDIT_COMMAND"]
    args = ["open", "-a", edit_command, path]
    call(args)

    return redirect(url_for("search", query=query, fields=fields))


@app.route('/view')
def view_file():
    path = request.args['path']
    fields = request.args.get('fields')
    query = request.args['query']
    # List parameter in config not possible?
    view_command = app.config["VIEW_COMMAND"]
    args = ["open", "-a", view_command, path]
    call(args)

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
    return render_template("search.html", query="", fields="")


def read_storage(file):
    if os.path.exists(file):
        with codecs.open(file, 'r', encoding='utf-8') as f:
            contents = f.readlines()
    else:
        contents = []
        open(file, 'a').close()
        
    return contents

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
                    directories.append("%s\n" % unicode(d.lower(), "utf-8"))
    directories = sorted(set(directories))
    with codecs.open(directories_file, 'w', encoding='utf-8') as f:
        f.writelines(directories)

if __name__ == '__main__':
    app.run()
