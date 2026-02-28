#!/usr/bin/env python3

import sys
from pathlib import Path
from bs4 import BeautifulSoup

TARGET_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "em", "b", "strong",
    "hr", "br",
    "ol", "ul", "li",
    "blockquote",
    "table", "thead", "tbody", "tr", "th", "td"
}

SKIP_CLASS_ID = {"whitespace-pre-wrap"}


def clean_html_attributes(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "lxml")

    for tag in soup.find_all(TARGET_TAGS):
        preserved_class = None

        # Check class preservation rule
        if tag.has_attr("class"):
            matched = SKIP_CLASS_ID.intersection(tag["class"])
            if matched:
                preserved_class = sorted(matched)

        # Remove all attributes
        tag.attrs.clear()

        # Restore preserved class if any
        if preserved_class:
            tag["class"] = preserved_class

        # Force table border
        if tag.name == "table":
            tag["border"] = "1"

    return str(soup)


def main():
    if len(sys.argv) not in (2, 3):
        print("Usage: python clean_html_attributes.py INPUT.html [REPLACE_FILE]")
        sys.exit(1)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    replace_file = False
    if len(sys.argv) == 3:
        replace_file = sys.argv[2].strip().upper() == "TRUE"

    html_text = input_path.read_text(encoding="utf-8")
    cleaned_html = clean_html_attributes(html_text)

    if replace_file:
        # overwrite original
        output_path = input_path
    else:
        # default behavior
        output_path = input_path.with_name(
            f"{input_path.stem}_cleaned{input_path.suffix}"
        )

    output_path.write_text(cleaned_html, encoding="utf-8")

    print(f"Cleaned file written to: {output_path}")


if __name__ == "__main__":
    main()
