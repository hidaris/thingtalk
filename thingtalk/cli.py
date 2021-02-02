import click
import uvicorn

from .app import app


@click.command()
@click.option("--host", default="127.0.0.1", type=str, help="Host of service.")
@click.option("--port", default=5000, type=int, help="Port of service.")
@click.option("--mode", type=str, prompt="Service mode", help="Mode of service.")
def thingtalk(host: str, port: int, mode: str):
    """Simple program that greets NAME for a total of COUNT times."""
    app.state.mode = mode
    uvicorn.run("thingtalk:app", host=host, port=port, log_level="info")


if __name__ == '__main__':
    thingtalk()
