import click
from signature import PySignature
from pprint import pprint


@click.command()
@click.argument('file', type=click.Path(exists=True))
def main(file: str):
    signature = PySignature(file)
    pprint("Imports:")
    pprint(signature.signature.imports)
    pprint("---")
    pprint("Functions:")
    pprint(signature.signature.functions)
    pprint("---")
    pprint("Classes:")
    pprint(signature.signature.classes)


if __name__ == "__main__":
    main()
