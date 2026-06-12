import time

def fetch_from_db(table_name, delay):
    print(f"Started fetching from {table_name}")
    time.sleep(delay)  # This BLOCKS the entire thread
    print(f"Done fetching from {table_name}")
    return f"{table_name} data"

def do_other_work():
    print("Doing other useful work while waiting for DB...")
    time.sleep(2)
    print("Finished other work")
    return "other result"

def main():
    # This blocks for 10 seconds - NOTHING else can run
    db_result = fetch_from_db("Orders", 10)
    
    # This only starts AFTER the 10 second DB call completes
    other_result = do_other_work()
    
    print(f"\nDB Result: {db_result}")
    print(f"Other Result: {other_result}")

if __name__ == "__main__":
    main()