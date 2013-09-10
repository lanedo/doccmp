import web
import view, config
import shutil
from view import render
import document_compare
import threading
import os
import Queue

urls = (
    '/', 'index',
    '/details', 'details',
    '/update', 'update'
)

class index:
    def GET(self):
        return render.base(view.listing())

    def POST(self):
        form = web.input(doc={})

        basename = form['doc'].filename.replace(' ', '_')
        tempfile = '/tmp/' + basename
        with open(tempfile, 'wb') as saved:
            shutil.copyfileobj(form['doc'].file, saved)

        # Do document comparison
        outdir = os.getcwd() + '/static/'
        uid = document_compare.init_document_compare (tempfile, outdir)
        b, ext = os.path.splitext(form['doc'].filename)
        filename = uid + ext

        config.DB.delete('items', where='id = "' + uid + '"')
        config.DB.insert('items', id=uid, name=b, pagecount=-1, extension=ext,olscore=-1,ollscore=-1, olwscore=-1)
        
        a = threading.Thread(target=worker, args=(filename, uid, outdir))
        a.start()
        #document_compare.generate_pdf_for_doc(filename, uid, outdir)
        #document_compare.generate_fullres_images_from_pdf(filename, uid, outdir)
        #score, pagecount = document_compare.compare_pdf_using_images(uid, outdir)


        # Insert into base
        #config.DB.insert('items', id=uid, name=b, pagecount=pagecount, extension=ext,olscore=score[0],ollscore=score[1], olwscore=score[2])

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

class update:
    def GET(self):
        i = web.input(uid=None, full=0)
        if i.uid == None:
            return render.base(view.listing())
        else:
            results = config.DB.select('items', dict(n=str(i.uid)), where="id=$n")
            rows = results.list()
            print ("Row count: " + str(len(rows)))
            if len(rows) > 0:
                outdir = os.getcwd() + '/static/'
                row = rows[0]
                if i.full == 0:
                    score, pagecount, all_scores = document_compare.compare_pdf_using_images(row['id'], outdir)
                    config.DB.update('items', where='id="' + str(i.uid) + '"', pagecount=pagecount, olscore=score[0],ollscore=score[1], olwscore=score[2], details=str(all_scores).strip('[]'))        
                else:
                    a = threading.Thread(target=worker, args=(row['id'] + row['extension'], i.uid, outdir))
                    a.start()
            
            return render.base(view.listing())

def worker(filename, uid, outdir):
    document_compare.generate_pdf_for_doc(filename, uid, outdir)
    document_compare.generate_fullres_images_from_pdf(filename, uid, outdir)
    score, pagecount, all_scores = document_compare.compare_pdf_using_images(uid, outdir)
    # Insert into base
    config.DB.update('items', where='id="' + str(uid) + '"', pagecount=pagecount, olscore=score[0],ollscore=score[1], olwscore=score[2], details=str(all_scores).strip('[]'))        

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.internalerror = web.debugerror

    app.run()