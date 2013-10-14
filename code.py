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

###############################################################################
# MAIN
###############################################################################
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


###############################################################################
# DETAILS
###############################################################################
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


###############################################################################
# UPDATE
###############################################################################
class update:
	def GET(self):
		i = web.input(uid=None, path2LO=None, full=0)
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
						print ("Updating: " + r['path2LO'])
						outdir = os.getcwd() + '/static/' + r['commitsha'] + '/'
						score, pagecount, all_scores = document_compare.compare_pdf_using_images(row['id'], outdir)
						config.DB.update('scores', where='id="' + str(i.uid) + '" AND path2LO="' + str(r['path2LO']) + '"', olscore=score[0],ollscore=score[1], olwscore=score[2], details=str(all_scores).strip('[]'))
				else:
					shutil.copy(os.getcwd() + '/static/originals/' + str(i.uid) + row['extension'], '/tmp/')
					
					if len(results.list()) == len(lo):
						# Update everyone
						if i.path2LO == None:
							config.DB.delete('scores', where='id = "' + str(i.uid) + '"')
							a = threading.Thread(target=worker, args=('/tmp/' + str(i.uid) + row['extension'], lo, False, ))
							a.start()
						# Update one row
						else:
							config.DB.delete('scores', where='id = "' + str(i.uid) + '" AND path2LO="' + str(i.path2LO) + '"')
							a = threading.Thread(target=worker, args=('/tmp/' + str(i.uid) + row['extension'], [str(i.path2LO)], False, ))
							a.start()
					else:
						a = threading.Thread(target=worker, args=('/tmp/' + str(i.uid) + row['extension'], lo, True, ))
						a.start()
			
			return render.base(view.listing())


###############################################################################
# Function performing document comparaison
###############################################################################
def worker(tempfile, libreoffice_versions_to_use, only_add_missing):
	baseoutdir = os.getcwd() + '/static/'
	uid = document_compare.init_document_compare (tempfile, baseoutdir)

	for libreoffice in libreoffice_versions_to_use:
		sha = document_compare.get_libreoffice_sha(libreoffice)
		version = document_compare.get_libreoffice_version(libreoffice)
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
		config.DB.insert('scores', id=str(uid), commitsha=sha, olscore=score[0],ollscore=score[1], olwscore=score[2], details=str(all_scores).strip('[]'), version=version, path2LO=libreoffice)

	os.remove(tempfile)

if __name__ == "__main__":
	app = web.application(urls, globals())
	app.internalerror = web.debugerror

	app.run()