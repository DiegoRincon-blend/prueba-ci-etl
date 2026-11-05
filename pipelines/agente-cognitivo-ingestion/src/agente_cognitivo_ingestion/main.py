"""Punto de entrada para la futura ingestión del agente cognitivo."""

import argparse


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline de ingestión del agente cognitivo (pendiente de implementación)."
    )
    parser.parse_args()
    parser.exit(2, "Error: la ingestión aún no está implementada; define fuentes y destino.\n")


if __name__ == "__main__":
    cli()
