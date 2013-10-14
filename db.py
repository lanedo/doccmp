import config

def listing(**k):
    return config.DB.query("SELECT * FROM items ")

def results_for_doc(uid):
	return config.DB.query("SELECT * FROM scores WHERE scores.id = '" + str(uid) + "'")

def sha_2_version(sha):
	l = config.DB.query("SELECT name FROM versions WHERE versions.sha='" + str(sha) + "'").list();
	if len(l) > 0:
		return l[0]['name']
	else:
		return 'master'