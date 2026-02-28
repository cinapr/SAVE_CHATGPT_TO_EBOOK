import sys
import os
import re
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET

# CONFIG START
NS = {"opf": "http://www.idpf.org/2007/opf"}
SKIP_FILES = {"nav.xhtml", "summary.xhtml"}
# CONFIG END


def extract_epub(epub_path, extract_dir):
    with zipfile.ZipFile(epub_path, "r") as z:
        z.extractall(extract_dir)


def find_opf(root):
    for dp, _, files in os.walk(root):
        for f in files:
            if f.endswith(".opf"):
                return os.path.join(dp, f)
    raise RuntimeError("OPF not found")


def sync_chapter_header(xhtml_path, chapter_number):
    with open(xhtml_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Update <title>
    content = re.sub(
        r"(<title>\s*Chapter\s+)\d+(\s*(?:[-–—].*?)?</title>)",
        rf"\g<1>{chapter_number}\g<2>",
        content,
        flags=re.IGNORECASE
    )

    # Update first <h1> after <body>
    def replace_first_h1(match):
        h1 = match.group(1)
        h1 = re.sub(
            r"(Chapter\s+)\d+",
            rf"\g<1>{chapter_number}",
            h1,
            flags=re.IGNORECASE
        )
        return "<body>" + h1

    content = re.sub(
        r"<body>\s*(<h1>.*?</h1>)",
        replace_first_h1,
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL
    )

    with open(xhtml_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    if len(sys.argv) < 2:
        print("Usage: python Auto-Renumber.py book.epub [keeptitle YES|NO] [addold YES|NO] [prefix]")
        sys.exit(1)

    epub_path = sys.argv[1]
    keeptitle = "NO"
    addold = False
    privateprefix = ""

    if len(sys.argv) >= 3:
        keeptitle = sys.argv[2].upper()
    if len(sys.argv) >= 4:
        addold = sys.argv[3].upper() == "YES"
    if len(sys.argv) >= 5:
        privateprefix = sys.argv[4].upper()

    keep_suffix = keeptitle == "YES"

    out_epub = epub_path.replace(".epub", "_RENUMBERED_" + keeptitle + ".epub")
    temp_dir = tempfile.mkdtemp()

    try:
        extract_epub(epub_path, temp_dir)
        opf_path = find_opf(temp_dir)

        tree = ET.parse(opf_path)
        root = tree.getroot()
        manifest = root.find("opf:manifest", NS)
        spine = root.find("opf:spine", NS)

        id_to_item = {
            item.attrib["id"]: item
            for item in manifest.findall("opf:item", NS)
        }

        rename_plan = []
        chapter_num = 1

        # -----------------------------
        # BUILD RENAME PLAN ONLY
        # -----------------------------
        for itemref in spine.findall("opf:itemref", NS):
            item_id = itemref.attrib["idref"]
            item = id_to_item[item_id]
            href = item.attrib["href"]
            base = os.path.basename(href)

            if base in SKIP_FILES or not base.endswith(".xhtml"):
                continue

            dirpart = os.path.dirname(href)
            name, ext = os.path.splitext(base)

            if keep_suffix:
                m = re.match(r".*?(\d+)(?:_(.+))?$", name)
                if m and m.group(2):
                    new_name = f"chap_{chapter_num}_{m.group(2)}{ext}"
                else:
                    new_name = f"chap_{chapter_num}{ext}"
            else:
                new_name = f"chap_{chapter_num}{ext}"

            if addold:
                new_name = "old_" + new_name

            if privateprefix != "":
                new_name = privateprefix + "_" + new_name

            new_href = os.path.join(dirpart, new_name) if dirpart else new_name

            old_path = os.path.join(os.path.dirname(opf_path), href)

            temp_name = f"__TEMP__REN__{chapter_num}{ext}"
            temp_href = os.path.join(dirpart, temp_name) if dirpart else temp_name
            temp_path = os.path.join(os.path.dirname(opf_path), temp_href)

            rename_plan.append({
                "old_path": old_path,
                "temp_path": temp_path,
                "final_path": os.path.join(os.path.dirname(opf_path), new_href),
                "final_href": new_href,
                "item": item,
                "chapter_num": chapter_num
            })

            chapter_num += 1

        # -----------------------------
        # PHASE 1: RENAME TO TEMP NAMES
        # -----------------------------
        for entry in rename_plan:
            if entry["old_path"] != entry["temp_path"]:
                os.rename(entry["old_path"], entry["temp_path"])

        # -----------------------------
        # PHASE 2: RENAME TEMP TO FINAL
        # -----------------------------
        for entry in rename_plan:
            if entry["temp_path"] != entry["final_path"]:
                os.rename(entry["temp_path"], entry["final_path"])

            entry["item"].attrib["href"] = entry["final_href"]
            sync_chapter_header(entry["final_path"], entry["chapter_num"])

            print(f"✔ → {entry['final_href']}")

        tree.write(opf_path, encoding="utf-8", xml_declaration=True)

        with zipfile.ZipFile(out_epub, "w", zipfile.ZIP_DEFLATED) as z:
            for dp, _, files in os.walk(temp_dir):
                for f in files:
                    full = os.path.join(dp, f)
                    rel = os.path.relpath(full, temp_dir)
                    z.write(full, rel)

        print(f"\nDone → {out_epub}")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()