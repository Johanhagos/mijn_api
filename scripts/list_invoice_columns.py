import os
import psycopg2

def main():
    url = os.environ.get('DATABASE_URL')
    if not url:
        print('DATABASE_URL not set')
        return
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    try:
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='invoices'")
        for row in cur.fetchall():
            print(row)
    except Exception as e:
        print('error:', e)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
