import click

click.command()
click.argument("path", type=click.Path(exists=True))
def formast(path):
    print(path)


if __name__ == "__main__":
    formast()