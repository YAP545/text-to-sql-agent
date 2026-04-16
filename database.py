import sqlite3

def setup_mock_database(db_name="company.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS employees (
                        id INTEGER PRIMARY KEY, name TEXT, department TEXT, salary REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales (
                        id INTEGER PRIMARY KEY, employee_id INTEGER, amount REAL, date TEXT)''')
    
    # Insert sample data
    cursor.executemany('INSERT OR IGNORE INTO employees VALUES (?,?,?,?)', [
        (1, 'Alice', 'Engineering', 120000),
        (2, 'Bob', 'Sales', 85000),
        (3, 'Charlie', 'Sales', 90000)
    ])
    cursor.executemany('INSERT OR IGNORE INTO sales VALUES (?,?,?,?)', [
        (1, 2, 5000, '2026-04-01'),
        (2, 2, 7500, '2026-04-05'),
        (3, 3, 12000, '2026-04-10')
    ])
    conn.commit()
    conn.close()
    return db_name

def get_database_schema(db_name="company.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    schema = "\n".join([row[0] for row in cursor.fetchall() if row[0]])
    conn.close()
    return schema
