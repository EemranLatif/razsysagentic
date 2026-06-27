import asyncio

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost


async def main():
    host = GrpcWorkerAgentRuntimeHost(
        address="localhost:50051"
    )

    host.start()

    print("Host is running on localhost:50051")
    print("Press Ctrl+C to stop")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Stopping host...")


if __name__ == "__main__":
    asyncio.run(main())