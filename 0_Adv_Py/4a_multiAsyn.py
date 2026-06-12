import asyncio

async def fetch_from_db(table_name, delay):
    print(f"Started fetching from {table_name}")
    await asyncio.sleep(delay)
    print(f"Done fetching from {table_name}")
    return f"{table_name} data"

async def main():
    results = await asyncio.gather(
        fetch_from_db("Orders", 3),
        fetch_from_db("Customers", 1),
        fetch_from_db("Products", 2),
    )

    print("\nResults:")
    print(results)


if __name__ == "__main__":
    asyncio.run(fetch_from_db("Orders", 10) )
    print("Orders done")

"""
if __name__ == "__main__":
    asyncio.run(main())
    print("All done")
"""