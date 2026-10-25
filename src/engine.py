import sqlite3
import os

DB_PATH = os.environ.get("DIGIFARM_DB_PATH", "data/digimon.db")
MAX_TRAINING_AMOUNT = 25
MAX_STAT_VALUE = 10_000

def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), mode=0o700, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS digimon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            stage TEXT,
            age INTEGER,
            hunger INTEGER,
            energy INTEGER,
            happiness INTEGER,
            strength INTEGER,
            iq INTEGER,
            care_mistakes INTEGER,
            is_alive BOOLEAN
        )
    ''')
    cursor.execute('SELECT COUNT(*) FROM digimon')
    if cursor.fetchone()[0] == 0:
        # Initialize default Digimon
        cursor.execute('''
            INSERT INTO digimon (name, stage, age, hunger, energy, happiness, strength, iq, care_mistakes, is_alive)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("Botamon", "Baby", 0, 100, 100, 100, 10, 10, 0, True))
    conn.commit()
    conn.close()
    os.chmod(DB_PATH, 0o600)

def get_digimon_status():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, stage, age, hunger, energy, happiness, strength, iq,
               care_mistakes, is_alive
        FROM digimon WHERE id = 1
    ''')
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def tick_active_session():
    """Advances time by exactly one tick. Called periodically only while the app is open."""
    digimon = get_digimon_status()
    if not digimon or not digimon['is_alive']:
        return

    hunger = max(0, digimon['hunger'] - 5)
    energy = max(0, digimon['energy'] - 3)
    happiness = max(0, digimon['happiness'] - 2)
    age = digimon['age'] + 1
    
    care_mistakes = digimon['care_mistakes']
    if hunger == 0:
        care_mistakes += 1

    is_alive = True
    if age >= 50 or care_mistakes >= 10:
        is_alive = False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE digimon 
        SET hunger = ?, energy = ?, happiness = ?, age = ?, care_mistakes = ?, is_alive = ?
        WHERE id = 1
    ''', (hunger, energy, happiness, age, care_mistakes, is_alive))
    conn.commit()
    conn.close()

def feed_digimon():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE digimon SET hunger = MIN(100, hunger + 20), happiness = MIN(100, happiness + 5) WHERE id = 1')
    conn.commit()
    conn.close()

def train_strength(amount: int = 10) -> str:
    """Increases Digimon's strength through physical training and reduces energy."""
    if type(amount) is not int or not 1 <= amount <= MAX_TRAINING_AMOUNT:
        raise ValueError(f"amount must be an integer from 1 to {MAX_TRAINING_AMOUNT}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE digimon SET strength = MIN(?, strength + ?), energy = MAX(0, energy - 15) WHERE id = 1',
        (MAX_STAT_VALUE, amount),
    )
    if cursor.rowcount != 1:
        conn.close()
        raise RuntimeError("Digimon state has not been initialized")
    conn.commit()
    conn.close()
    return f"Successfully trained! Strength increased by up to {amount}."

def study_iq(amount: int = 10) -> str:
    """Increases Digimon's IQ through studying tasks and reduces energy."""
    if type(amount) is not int or not 1 <= amount <= MAX_TRAINING_AMOUNT:
        raise ValueError(f"amount must be an integer from 1 to {MAX_TRAINING_AMOUNT}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE digimon SET iq = MIN(?, iq + ?), energy = MAX(0, energy - 15) WHERE id = 1',
        (MAX_STAT_VALUE, amount),
    )
    if cursor.rowcount != 1:
        conn.close()
        raise RuntimeError("Digimon state has not been initialized")
    conn.commit()
    conn.close()
    return f"Successfully studied! IQ increased by up to {amount}."