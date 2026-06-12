import asyncio

async def order_pizza():
    print("   🍕 Step 1: Called pizza shop (10 sec delivery)")
    for i in range(1, 11):
        await asyncio.sleep(1)
        if i == 5:
            print(f"   🍕 Step {i}: Pizza is being baked...")
        elif i == 8:
            print(f"   🍕 Step {i}: Delivery driver on the way!")
    print("   🍕 Step 10: PIZZA ARRIVES! 🎉")
    return "Hot & Fresh Pizza"

async def do_homework():
    print("   📚 Step 1: Open math book")
    await asyncio.sleep(2)
    print("   📚 Step 2: Solving problem 1...")
    await asyncio.sleep(2)
    print("   📚 Step 3: Solving problem 2...")
    await asyncio.sleep(2)
    print("   📚 Step 4: Solving problem 3...")
    await asyncio.sleep(2)
    print("   📚 Step 5: HOMEWORK DONE! ✅")
    return "Completed Homework"

async def perfect_example():
    print("\n🎯 Other Senario:")
    print("=" * 50)
    
    # Order pizza first (starts delivery timer)
    pizza_task = asyncio.create_task(order_pizza())
    
    print("🟢 Pizza ordered! Now starting homework...\n")
    
    # While pizza is being delivered, do homework
    homework_result = await do_homework()
    
    # Pizza should be here by now (or very close)
    print("\n🔔 Doorbell rings!")
    pizza_result = await pizza_task
    
    print("\n" + "=" * 50)
    print(f"✅ Result: {pizza_result} AND {homework_result}")
    print("🎉 Both tasks completed at nearly the same time!")

async def what_students_think():
    """Wait for pizza to arrive before starting homework"""
    print("\n😢 Wait for pizza to arrive before starting homework:")
    print("=" * 50)
    
    # They think they must wait for pizza first
    print("Waiting for pizza to arrive...")
    pizza_result = await order_pizza()
    print("\nNow pizza is here, can start homework...")
    homework_result = await do_homework()
    
    print(f"\nTotal time: 20 seconds (10 sec pizza + 10 sec homework)")

asyncio.run(what_students_think())
print("\n" + "=" * 50)

asyncio.run(perfect_example())