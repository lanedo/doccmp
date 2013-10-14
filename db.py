import config

def listing(**k):
    return config.DB.query("SELECT * FROM items ")

def results_for_doc(uid):
	return config.DB.query("SELECT * FROM scores WHERE scores.id = '" + str(uid) + "' ORDER BY version DESC")
