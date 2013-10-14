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

lo =['/media/pierre-eric/309451c6-b1c2-4554-99a1-30452150b211/libreoffice-master-ro/', '/media/pierre-eric/309451c6-b1c2-4554-99a1-30452150b211/libreoffice-4.1/', '/media/pierre-eric/309451c6-b1c2-4554-99a1-30452150b211/libreoffice-3.6/']

def sha_to_libreoffice(sha):
	if sha == 'f5248b4':
		return lo[0]
	elif sha == '9c2b278':
		return lo[1]
	elif sha == 'b059b03':
		return lo[2]
	else:
		raise

class index:
	def GET(self):
		return render.base(view.listing())

	def POST(self):
		form = web.input(doc={})

		basename = form['doc'].filename.replace(' ', '_')
		tempfile = '/tmp/' + basename
		with open(tempfile, 'wb') as saved:
			shutil.copyfileobj(form['doc'].file, saved)

		uid = document_compare.compute_uid (tempfile)

		# Remove old entries
		config.DB.delete('scores', where='id = "' + uid + '"')
		config.DB.delete('items', where='id = "' + uid + '"')

		b, ext = os.path.splitext(form['doc'].filename)
		# Insert 
		config.DB.insert('items', id=uid, name=b, pagecount=-1, extension=ext)

		# Start bg thread		
		a = threading.Thread(target=worker, args=(tempfile, False, ))
		a.start()

		return render.base(view.listing())

class details:
	def GET(self):
		i = web.input(uid=None, sha=None)
		if i.uid == None or i.sha == None:
			return render.base(view.listing())
		else:
			results = config.DB.query("SELECT * FROM items JOIN scores WHERE scores.id = items.id AND scores.id = '" + str(i.uid) + "' AND scores.commitsha='" + i.sha + "'")
			rows = results.list()
			print ("Row count: " + str(len(rows)))
			if len(rows) == 0:
				return render.base(view.listing())
			row = rows[0]
			return render.details(row)

class update:
	def GET(self):
		i = web.input(uid=None, sha=None, full=0)
		if i.uid == None:
			return render.base(view.listing())
		else:
			results = config.DB.select('items', dict(n=str(i.uid)), where="id=$n")
			rows = results.list()
			print ("Row count: " + str(len(rows)))
			if len(rows) > 0:
				row = rows[0]

				results = config.DB.query("SELECT * FROM scores WHERE id='"  + str(i.uid) + "'")
				if i.full == 0:
					for r in results.list():
						print ("Updating: " + r['commitsha'])
						outdir = os.getcwd() + '/static/' + r['commitsha'] + '/'
						score, pagecount, all_scores = document_compare.compare_pdf_using_images(row['id'], outdir)
						config.DB.update('scores', where='id="' + str(i.uid) + '" AND commitsha="' + str(r['commitsha']) + '"', olscore=score[0],ollscore=score[1], olwscore=score[2], details=str(all_scores).strip('[]'))
				else:
					shutil.copy(os.getcwd() + '/static/originals/' + str(i.uid) + row['extension'], '/tmp/')
					
					if len(results.list()) == len(lo):
						# Update everyone
						if i.sha == None:
							config.DB.delete('scores', where='id = "' + str(i.uid) + '"')
							a = threading.Thread(target=worker, args=('/tmp/' + str(i.uid) + row['extension'], False, ))
							a.start()
						# Update one row
						else:
							print ("TODO")
					else:
						a = threading.Thread(target=worker, args=('/tmp/' + str(i.uid) + row['extension'], True, ))
						a.start()
			
			return render.base(view.listing())

def worker(tempfile, only_add_missing):
	baseoutdir = os.getcwd() + '/static/'
	uid = document_compare.init_document_compare (tempfile, baseoutdir)

	for libreoffice in lo:
		sha = document_compare.get_libreoffice_sha(libreoffice)
		outdir = baseoutdir + sha + '/'

		if only_add_missing:
			results = config.DB.select('scores', dict(n=str(uid)), where="id=$n AND commitsha='" + str(sha) + "'")
			if len(results.list()) > 0:
				continue

		b, ext = os.path.splitext(tempfile)
		filename = uid + ext

		document_compare.generate_pdf_for_doc(baseoutdir + 'originals/' + filename, uid, libreoffice, outdir)
		document_compare.generate_fullres_images_from_pdf(filename, uid, outdir)
		score, pagecount, all_scores = document_compare.compare_pdf_using_images(uid, outdir)
		# Update page count
		config.DB.update('items', where='id="' + str(uid) + '"', pagecount=pagecount)
		# Update score
		config.DB.insert('scores', id=str(uid), commitsha=sha, olscore=score[0],ollscore=score[1], olwscore=score[2], details=str(all_scores).strip('[]'))

	os.remove(tempfile)

if __name__ == "__main__":
	app = web.application(urls, globals())
	app.internalerror = web.debugerror

	app.run()