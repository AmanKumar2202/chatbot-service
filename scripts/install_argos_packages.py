import argparse
import os
from pathlib import Path


def install_pairs(pairs: list[str]) -> None:
    root = Path(os.getenv("ARGOS_DATA_DIRECTORY", "./argos_data")).resolve()
    os.environ.setdefault("XDG_DATA_HOME", str(root / "data"))
    os.environ.setdefault("XDG_CONFIG_HOME", str(root / "config"))
    os.environ.setdefault("XDG_CACHE_HOME", str(root / "cache"))
    import argostranslate.package

    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    for pair in pairs:
        try:
            source, target = pair.split("-", 1)
        except ValueError as exc:
            raise ValueError(f"Invalid language pair '{pair}'; expected source-target") from exc
        package = next(
            (
                candidate
                for candidate in available
                if candidate.from_code == source and candidate.to_code == target
            ),
            None,
        )
        if package is None:
            raise ValueError(f"No Argos package is available for {pair}")
        argostranslate.package.install_from_path(package.download())
        print(f"Installed Argos language pair: {pair}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pairs",
        nargs="*",
        help="Language pairs such as en-es en-fr",
    )
    args = parser.parse_args()
    pairs = args.pairs or [
        pair.strip()
        for pair in os.getenv("ARGOS_LANGUAGE_PAIRS", "").split(",")
        if pair.strip()
    ]
    if not pairs:
        print("No Argos language pairs requested")
        return
    install_pairs(pairs)


if __name__ == "__main__":
    main()
