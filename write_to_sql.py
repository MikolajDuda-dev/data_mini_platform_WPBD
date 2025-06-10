# write_to_sql.py
import pandas as pd
from sqlalchemy import create_engine, text
import time

DATABASE_URL = "postgresql://user:passwd@postgres:5432/testdb"

# Wait for PostgreSQL to be ready
for i in range(10):
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("PostgreSQL is ready!")
        break
    except Exception as e:
        print(f"Waiting for PostgreSQL... ({i+1}/10): {e}")
        time.sleep(5)
else:
    raise Exception("Could not connect to PostgreSQL")

# Define table schemas and corresponding CSV files
tables_config = [
    {"name": "customers", "csv_file": "data1.csv", "dtype": {"id": "int", "name": "str", "email": "str"}},
    {"name": "products", "csv_file": "data2.csv", "dtype": {"id": "int", "product_name": "str", "price": "float"}},
    {"name": "orders", "csv_file": "data3.csv", "dtype": {"order_id": "int", "customer_id": "int", "product_id": "int", "quantity": "int", "order_date": "str"}},
]

for table_info in tables_config:
    table_name = table_info["name"]
    csv_file = table_info["csv_file"]
    df = pd.read_csv(f"/{csv_file}") # Path in the container

    print(f"Creating table '{table_name}' and inserting data from '{csv_file}'...")
    # Write DataFrame to SQL table, creating it if it doesn't exist
    # if_exists='replace' will drop and recreate table, 'append' will just add rows
    df.to_sql(table_name, engine, if_exists='replace', index=False)
    print(f"Table '{table_name}' created and data inserted successfully.")

print("All data loaded into PostgreSQL.")