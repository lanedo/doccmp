#SQL table creations commands:

CREATE TABLE items(pagecount NUMERIC,id TEXT,name TEXT,extension TEXT,PRIMARY KEY(id));
CREATE TABLE scores(commitsha TEXT,id TEXT,olscore REAL,ollscore REAL,olwscore REAL,details TEXT,version TEXT,path2LO TEXT,PRIMARY KEY(commitsha, id),FOREIGN KEY(id) REFERENCES items(id));
