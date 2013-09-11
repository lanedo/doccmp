CREATE TABLE scores(
	commitsha TEXT,
	id TEXT,
	olscore REAL,
	ollscore REAL,
	olwscore REAL,
	details TEXT,
	PRIMARY KEY(commitsha, id),
	FOREIGN KEY(id) REFERENCES items(id)
);