import asyncio

import click

from .client import app_factory
from .producer import main as producer_main
from .propagator import main as propagator_main


@click.group()
def cli():
    pass


@cli.command(help="Run producer")
@click.option("-t", "--target", "target", type=str, help="HTTP address of target", required=False)
def producer(target: str | None = None):
    asyncio.run(producer_main(target))


@cli.command(help="Run propagator")
def propagator():
    propagator_main()


@cli.command(help="Run client")
def client():
    asyncio.run(client_mltp())


async def client_mltp():
    app_a1 = app_factory("a:1")
    app_a2 = app_factory("a:2")
    app_b1 = app_factory("b:1")
    app_b2 = app_factory("b:2")

    await asyncio.gather(app_a1.run(), app_a2.run(), app_b1.run(), app_b2.run())


def main():
    cli()


if __name__ == "__main__":
    cli()
