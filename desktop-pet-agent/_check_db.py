import sqlite3
db = sqlite3.connect('data/sessions.db')
rows = db.execute("SELECT role, content FROM messages WHERE content LIKE '%__TEXT__%' LIMIT 5").fetchall()
for r in rows:
    print('[{}] {}'.format(r[0], r[1][:80]))
if not rows:
    print('No __TEXT__ in DB')
    rows2 = db.execute('SELECT role, content FROM messages WHERE role="status" LIMIT 5').fetchall()
    for r in rows2:
        print('[{}] {}'.format(r[0], r[1][:80]))
db.close()
