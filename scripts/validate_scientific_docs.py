"""Check RedScribe's tracked Markdown, numbered evidence and immutable public samples."""
import ast
import hashlib
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def read(path):
    return Path(path).read_text(encoding="utf-8")


files = subprocess.check_output(["git", "ls-files", "*.md"], text=True).splitlines()
links = 0
for name in files:
    fenced = False
    for number, line in enumerate(read(name).splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in re.finditer(r"\]\((?:<([^>]+)>|([^\s()]+))\)", line):
            url = urlsplit(match[1] or match[2])
            if url.scheme or url.netloc:
                continue
            target = Path(name).parent / unquote(url.path) if url.path else Path(name)
            require(target.exists(), f"{name}:{number}: missing {target}")
            if url.fragment and target.suffix == ".md":
                headings = re.findall(r"^#+ (.+)$", read(target), re.M)
                anchors = {re.sub(r"[^\w -]", "", h.lower()).replace(" ", "-") for h in headings}
                require(unquote(url.fragment) in anchors, f"{name}:{number}: missing heading {url.fragment}")
            links += 1

base = Path("docs/scientific")
figures = base / "figures"
guide = read(figures / "README.md")
for i in range(1, 12):
    stem = f"{i:02d}"
    require(f"## Figure {i}. " in guide and f"({stem}.svg)" in guide
            and f"({stem}.dot)" in guide, f"Missing figure {i} caption or asset link")
    require(ET.parse(figures / f"{stem}.svg").getroot().tag.endswith("}svg"), stem)

labels = next(ast.literal_eval(n.value) for n in ast.parse(read("model_options.py")).body
              if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "ASR_MODEL_LABELS")
inventory = read(base / "MODELS.md")
for key, label in labels.items():
    require(f"| {key} | {label} |" in inventory, f"Model inventory differs for {key}")
for filename, pattern, count in [("REFERENCES.md", r"^\| \[(\d+)\]", 19),
                                 ("CLAIMS.md", r"^\| C(\d+) ", 21)]:
    numbers = list(map(int, re.findall(pattern, read(base / filename), re.M)))
    require(numbers == list(range(1, count + 1)), f"Check numbering in {filename}")

samples = Path("docs/user-guide/sample-outputs")
hashes = re.findall(r"^- `([^`]+)`: `([0-9a-f]{64})`", read(samples / "README.md"), re.M)
require(len(hashes) == 2, "Expected two checksummed public samples")
for name, expected in hashes:
    require(hashlib.sha256((samples / name).read_bytes()).hexdigest() == expected, name)
print(f"{len(files)} Markdown documents, {links} internal links, 11 figures, "
      f"{len(labels)} model labels, 19 references, 21 claims, 2 sample digests checked")
