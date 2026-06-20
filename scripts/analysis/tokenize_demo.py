import argparse
import re

WORD_RE = re.compile(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+|\d+|[^\w\s]", re.UNICODE)

TEXTOS = [
    "El Dr. Gómez es una sola frase aunque tenga dos puntos.",
    "¿Final de interrogación? ¿Nueva frase??",
    "¡Y las admiraciones! ¿Qué pasa con ellas?",
    "Símbolos en otros alfabetos: 千と千尋の神隠し (viaje de Chihiro)",
    "Estados Unidos se abrevia EE. UU. en español",
    "También tenemos siglas: O.N.U., O.T.A.N. y otras",
]


def tokenize_regex(texto: str) -> list[str]:
    return WORD_RE.findall(texto)


def tokenize_spacy(texto: str) -> list[str]:
    return [t.text for t in _nlp(texto)]


def mostrar(nombre: str, texto: str, tokens: list[str]) -> None:
    print(f"  [{nombre}] Tokens ({len(tokens)}): {tokens}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tokenizador: regex vs spaCy")
    parser.add_argument(
        "modo",
        nargs="?",
        default="both",
        choices=["regex", "spacy", "both"],
        help="Qué tokenizador usar (default: both)",
    )
    args = parser.parse_args()

    usar_regex = args.modo in ("regex", "both")
    usar_spacy = args.modo in ("spacy", "both")

    if usar_spacy:
        import spacy

        global _nlp
        _nlp = spacy.load("es_core_news_sm")

    for texto in TEXTOS:
        print(f"Texto: {texto}")
        if usar_regex:
            mostrar("regex", texto, tokenize_regex(texto))
        if usar_spacy:
            mostrar("spacy", texto, tokenize_spacy(texto))
        print()


if __name__ == "__main__":
    main()
