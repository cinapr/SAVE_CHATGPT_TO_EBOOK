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

    # ---- Update <title> (only one exists, safe) ----
    content = re.sub(
        r"(<title>\s*Chapter\s+)\d+(\s*(?:[-–—].*?)?</title>)",
        rf"\g<1>{chapter_number}\g<2>",
        content,
        flags=re.IGNORECASE
    )

    # ---- Update ONLY the first <h1> after <body> ----
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
        print("Usage: python Auto-Renumber.py book.epub [keeptitle YES|NO] [addold YES|NO]  [add your own prefix no space]")
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

        chapter_num = 1

        for itemref in spine.findall("opf:itemref", NS):
            item_id = itemref.attrib["idref"]
            item = id_to_item[item_id]
            href = item.attrib["href"]
            base = os.path.basename(href)

            if base in SKIP_FILES or not base.endswith(".xhtml"):
                continue

            dirpart = os.path.dirname(href)

            # START CHANGE SUFFIX & PREFIX OF THE CHAPTER.XHTML FILENAME
            name, ext = os.path.splitext(base)

            new_name = None

            if keep_suffix:
                # Match: anything + number + optional _suffix
                # Examples:
                # chap_592_supersimilarwkikyo
                # Chapter_128_KikyoApartEnd
                # 4567
                m = re.match(r".*?(\d+)(?:_(.+))?$", name)
                if m and m.group(2):
                    # Has suffix → keep it
                    new_name = f"Chapter_{chapter_num}_{m.group(2)}{ext}"
                else:
                    # No suffix
                    new_name = f"Chapter_{chapter_num}{ext}"
            else:
                # keeptitle = NO → always plain
                new_name = f"Chapter_{chapter_num}{ext}"
            # END CHANGE SUFFIX & PREFIX OF THE CHAPTER.XHTML FILENAME

            if(addold):
                new_name = "old_" + new_name

            if(privateprefix != ""):
                new_name = privateprefix + "_" + new_name

            new_href = os.path.join(dirpart, new_name) if dirpart else new_name

            old_path = os.path.join(os.path.dirname(opf_path), href)
            new_path = os.path.join(os.path.dirname(opf_path), new_href)

            # Change Filename
            os.rename(old_path, new_path)
            item.attrib["href"] = new_href

            # Change <h1> and <title>
            sync_chapter_header(new_path, chapter_num)

            print(f"✔ {href} → {new_href}")
            chapter_num += 1

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
