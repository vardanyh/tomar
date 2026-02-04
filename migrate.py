import sqlite3
import os
from dbfread import DBF

# 1. CONFIGURATION
# List your specific Clipper files here
SOURCE_FILES = ['~/projects/papa/SHZATIK.DBF', '~/projects/papa/MONTARM.DBF', '~/projects/papa/SHARAIC.DBF']
SOURCE_FOLDER = '~/projects/papa/'  # Path where your DBFs are located
TARGET_DB = '~/projects/papa/migration_output.db'

# Encoding Note: Clipper apps in your region often used specific Code Pages.
# If the text looks like gibberish, try changing 'cp437' to:
# 'cp1256' (Windows Arabic/Farsi), 'cp864' (DOS Arabic), or 'armscii-8' (Armenian)
ENCODING = 'cp437' 

def get_sql_type(type_char):
    """Maps Clipper DBF field types to SQLite types."""
    mapping = {
        'C': 'TEXT',    # Character
        'N': 'REAL',    # Number
        'D': 'TEXT',    # Date (stored as YYYYMMDD string in SQLite)
        'L': 'INTEGER', # Logical (True/False)
        'M': 'TEXT'     # Memo (Text Blob)
    }
    return mapping.get(type_char, 'TEXT')

def migrate_file(filename):
    file_path = os.path.join(SOURCE_FOLDER, filename)
    table_name = filename.split('.')[0].lower() # e.g., shzatik
    
    if not os.path.exists(file_path):
        print(f"Skipping {filename} (File not found)")
        return

    print(f"Migrating {filename} to table '{table_name}'...")

    try:
        # Load the DBF file
        table = DBF(file_path, load=True, encoding=ENCODING)
        
        if len(table) == 0:
            print(f" -> {filename} is empty.")
            return

        # Connect to SQL
        conn = sqlite3.connect(TARGET_DB)
        cursor = conn.cursor()

        # 1. Drop old table if exists (start fresh)
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        # 2. Create Table Dynamically
        # We assume an 'id' column is needed for modern SQL logic
        field_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        field_names = []
        
        for field in table.fields:
            sql_type = get_sql_type(field.type)
            # Sanitize field names (replace spaces/illegal chars)
            clean_name = field.name.replace(' ', '_')
            field_defs.append(f"{clean_name} {sql_type}")
            field_names.append(clean_name)

        create_query = f"CREATE TABLE {table_name} ({', '.join(field_defs)})"
        cursor.execute(create_query)

        # 3. Insert Records
        insert_sql = f"INSERT INTO {table_name} ({', '.join(field_names)}) VALUES ({','.join(['?']*len(field_names))})"
        
        count = 0
        for record in table:
            if record.deleted:
                continue # Skip deleted records
            
            # Extract values in the order of fields
            values = [record[fn] for fn in table.field_names]
            cursor.execute(insert_sql, values)
            count += 1

        conn.commit()
        conn.close()
        print(f" -> Success! Migrated {count} records.")

    except Exception as e:
        print(f" -> Error processing {filename}: {e}")

# MAIN EXECUTION
if __name__ == "__main__":
    print("Starting Migration...")
    for f in SOURCE_FILES:
        migrate_file(f)
    print("\nMigration Finished. Open 'migration_output.db' to view data.")
