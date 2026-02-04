import os
import psycopg2

def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set")
        return
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    try:
        cur.execute("SELECT version_num FROM alembic_version")
        rows = cur.fetchall()
        print("alembic_version rows:", rows)
    except Exception as e:
        print("error querying alembic_version:", e)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
