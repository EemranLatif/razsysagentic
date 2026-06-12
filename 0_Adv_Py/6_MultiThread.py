import threading
import time

def fetch_from_db(table_name, delay):
    print(f"Started fetching from {table_name}")
    time.sleep(delay)
    print(f"Done fetching from {table_name}")

# All your task data in one place
tables = [
    ("Orders",    3),
    ("Customers", 1),
    ("Products",  2),
]

# Create and start all threads in one loop
threads = []
for table_name, delay in tables:
    t = threading.Thread(target=fetch_from_db, args=(table_name, delay))
    threads.append(t)
    t.start()

# Wait for all threads to finish
for t in threads:
    t.join()

print("All done")