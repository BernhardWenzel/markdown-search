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

    search = Search(app.config["INDEX_DIR"])
    if not query:
        tag_cloud = search.get_tags()
        parsed_query = ""
        result = []
    else:
        parsed_query, result, tag_cloud = search.search(query.split(), fields=[fields])

    return render_template('search.html', entries=result, query=query, parsed_query=parsed_query, fields=fields, tag_cloud=tag_cloud)


@app.route('/open')
def open():
    path = request.args['path']
    fields = request.args.get('fields')
    query = request.args['query']
    call([app.config["EDIT_COMMAND"], path])

    return redirect(url_for("search", query=query, fields=fields))

@app.route('/update_index')
def update_index():
    UpdateIndexTask()
    flash("Updating index, check console output")
    return redirect(url_for("search", query="", fields=""))

if __name__ == '__main__':
    app.run()
