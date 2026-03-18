from pathlib import Path

EXCLUDE_NAMES = {".venv", "__pycache__", ".git", "tree.py"}
EXCLUDE_CONTENTS = {"input"}  # on affiche le dossier, mais pas son contenu


def print_tree(root, prefix=""):
    root = Path(root)

    entries = [p for p in root.iterdir() if p.name not in EXCLUDE_NAMES]
    entries.sort(key=lambda p: (p.is_file(), p.name.lower()))

    for i, path in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        print(prefix + connector + path.name)

        if path.is_dir():
            if path.name in EXCLUDE_CONTENTS:
                # on affiche juste "..."
                extension = "    " if i == len(entries) - 1 else "│   "
                print(prefix + extension + "...")
                continue

            extension = "    " if i == len(entries) - 1 else "│   "
            print_tree(path, prefix + extension)


if __name__ == "__main__":
    print_tree(".")