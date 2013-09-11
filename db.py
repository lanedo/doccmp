import config

def listing(**k):
    return config.DB.query("SELECT * FROM items JOIN scores WHERE scores.id = items.id")