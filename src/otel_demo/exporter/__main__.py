import asyncio

from otel_demo.exporter import serve


def main():
    asyncio.run(serve())


if __name__ == "__main__":
    main()
