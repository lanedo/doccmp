import web
import view, config
import shutil
from view import render
import document_compare
import os
urls = (
    '/', 'index',
    '/upload', 'Upload',
    '/details', 'details'
)

class index:
    def GET(self):
        return render.base(view.listing())

class details:
	def GET(self):
		i = web.input(uid=None)
		if i.uid == None:
			return render.base(view.listing())
		else:
			results = config.DB.select('items', dict(n=str(i.uid)), where="id=$n")
			rows = results.list()
			print ("Row count: " + str(len(rows)))
			if len(rows) == 0:
				return render.base(view.listing())
			row = rows[0]
			return render.details(row)

class Upload:
    def GET(self):
        return """<html><head></head><body>
<form method="POST" enctype="multipart/form-data" action="">
<input type="file" name="doc" />
<br/>
<input type="submit" />
</form>
</body></html>"""

    def POST(self):
    	form = web.input(doc={})
    	tempfile = '/tmp/' + form['doc'].filename
    	with open(tempfile, 'wb') as saved:
        	shutil.copyfileobj(form['doc'].file, saved)
        uid, score, pagecount = document_compare.compare_document(tempfile, '/home/pierre-eric/Projects/webpy/static/')
        basename, ext = os.path.splitext(form['doc'].filename)

        config.DB.insert('items', id=uid, name=basename, pagecount=pagecount, extension=ext,olscore=score[0],ollscore=score[1], olwscore=score[2])

        return render.base(view.listing())

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.internalerror = web.debugerror
    app.run()