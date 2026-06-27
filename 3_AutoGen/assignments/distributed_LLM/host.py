"""
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Stopping host...")


host.py

Starts the gRPC Host.

The host does NOT execute any AI logic.
It simply routes messages between workers.

Run this FIRST.

    python host.py
"""

import asyncio

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost

from config import HOST_ADDRESS, TOPIC_NAME


async def main():

    print("=" * 60)
    print("Starting AutoGen Distributed Host")
    print("=" * 60)

    host = GrpcWorkerAgentRuntimeHost(
        address=HOST_ADDRESS
    )

    host.start()

    print()
    print(f"Host Address : {HOST_ADDRESS}")
    print(f"Topic        : {TOPIC_NAME}")
    print()
    print("Workers expected:")
    print("  • Reviewer Agent")
    print("  • Researcher Agent")
    print("  • Monitor Agent")
    print()
    print("Waiting for workers...")
    print()
    print("Press Ctrl+C to stop.")
    print()

    # Windows doesn't support add_signal_handler()
    # so we simply keep the event loop alive.
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())