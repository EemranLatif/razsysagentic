import threading
import time

def fetch_from_db(table_name, delay):
    print(f"Started fetching from {table_name}")
    time.sleep(delay)  # simulates waiting for DB response (blocking)
    print(f"Done fetching from {table_name}")

# Create one thread per table
t1 = threading.Thread(target=fetch_from_db, args=("Orders", 3))
t2 = threading.Thread(target=fetch_from_db, args=("Customers", 1))
t3 = threading.Thread(target=fetch_from_db, args=("Products", 2))

# Start all threads
t1.start()
t2.start()
t3.start()

# Wait for all threads to finish
t1.join()
t2.join()
t3.join()

print("All done")