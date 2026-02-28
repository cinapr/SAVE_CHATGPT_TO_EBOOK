# pip install ebooklib beautifulsoup4 lxml 

import sys
import os
import re
from ebooklib import epub
from bs4 import BeautifulSoup
from lxml import etree, html

MAX_FILENAME_LENGTH = 200

EPUB_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 1.05em;
    line-height: 1.6;
    color: #222;
    margin: 1.5em;
    background-color: transparent;
}

div:not([class]) {
  background-color: transparent;
}

h1, h2, h3 {
    font-weight: 700;
    color: #111;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.3em;
    margin-top: 1.2em;
}

pre {
    white-space: pre-wrap;
    font-family: inherit;
}

b, strong { font-weight: 700; }

i, em { font-style: italic; }

hr {
    border: none;
    border-top: 1px solid #bbb;
    margin: 1.5em 0;
}

/* For prompt section will color RED */
.you-said {
    color: #C00000; /* red */
    background-color: #F4F4F4;
    white-space: pre-wrap;
    white-space-collapse: preserve;
    text-wrap-mode: wrap;
    font-style: italic;
}

/* For chatGPT return section will color BLACK */
.chatgpt-said {
    color: #000000; /* black */
}

/* For re-paste old chat */
.old-chat-memory{
  color: red; 
  font-style: italic; 
}

/* larger paragraph spacing */
p {
    margin: 1.0em 0; 
    line-height: 1.6; 
}
"""


# START: EXPORT WITH PRETTY INDENTION
from lxml import etree, html

def pretty_xhtml(html_fragment):
    """
    Pretty-print XHTML with stable indentation
    WITHOUT destroying inner <div> structure.
    """

    try:
        wrapper = html.fromstring(f"<wrapper>{html_fragment}</wrapper>")

        output = []
        for child in wrapper:
            output.append(
                etree.tostring(
                    child,
                    pretty_print=True,
                    encoding="unicode"
                )
            )
        return "".join(output)

    except Exception as e:
        print(html_fragment)
        print(f"HTML parsing failed pretty_xhtml: {e}")
# END: EXPORT WITH PRETTY INDENTION


# START: CLEAN THE MASSAGE WE SENT TO GPT INTO HTML
def extract_clean_messages(soup):
    """
    Hybrid extractor:
    - YOU-SAID from <span data-you-said="true">
    - GPT-SAID from data-message-author-role="assistant"
    Preserves order.
    """

    blocks = []

    body = soup.body or soup

    for node in body.descendants:
        if not getattr(node, "name", None):
            continue

        # --- YOU SAID (from reconstructed UI span) ---
        if node.name == "span" and node.get("data-you-said") == "true":
            html = node.decode_contents().strip()
            if html:
                blocks.append(f"You said:\n{html}")

        # --- CHATGPT SAID (official semantic marker) ---
        elif node.get("data-message-author-role") == "assistant":
            content = node.find(class_="markdown") or node

            # strip UI junk
            for tag in content.find_all([
                "button", "svg", "nav", "aside", "article"
            ]):
                tag.decompose()

            html = content.decode_contents().strip()
            if html:
                blocks.append(f"ChatGPT said:\n{html}")

    return "\n\n".join(blocks)





def convert_whitespace_div_to_span(div, soup):
    """
    Replace ChatGPT whitespace-pre-wrap div with:
    <span data-you-said="true"><p>...</p></span>
    """

    raw = div.get_text("\n", strip=False)
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')

    span = soup.new_tag("span", **{"data-you-said": "true"})

    blocks = re.split(r'\n{2,}', raw)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        p = soup.new_tag("p")

        lines = block.split('\n')
        for i, line in enumerate(lines):
            p.append(line)
            if i < len(lines) - 1:
                p.append(soup.new_tag("br"))

        span.append(p)

    return span

def unwrap_chatgpt_ui(node):
    """
    Remove ChatGPT UI wrapper divs but keep inner content.
    """
    while node.parent and node.parent.name == "div":
        cls = " ".join(node.parent.get("class", []))
        if any(x in cls for x in [
            "flex",
            "user-message-bubble-color",
            "corner-superellipse"
        ]):
            node.parent.unwrap()
        else:
            break
# END: CLEAN THE MASSAGE WE SENT TO GPT INTO HTML




# START: STRIP ALL HTML INDENT
def strip_all_attributes_selective(soup):
    """
    Strip ALL attributes from specific tags.
    Force <table> to always have border="1".
    Does NOT alter structure or text.
    """

    TARGET_TAGS = {
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "em", "b", "strong",
        "hr", "br",
        "ol", "ul", "li",
        "blockquote",
        "table", "thead", "tbody", "tr", "th", "td"
    }

    # Replace attributes with mandatory attributes
    for tag in soup.find_all(TARGET_TAGS):
        tag.attrs.clear()
        # Enforce table border
        if tag.name == "table":
            tag["border"] = "1"
# END: STRIP ALL HTML INDENT




# YOU-SAID AREA WILL BE TURN INTO HTML
def normalize_you_said_span(span):
    """
    Convert raw text inside <span data-you-said="true">
    into proper HTML:
    - double newline => <p>
    - single newline => <br/>
    """
    raw = span.get_text("\n", strip=False)

    # Normalize line endings
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')

    parts = re.split(r'\n{2,}', raw)

    new_children = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if '\n' in part:
            # Single newline => <br/>
            frag = BeautifulSoup("", "lxml")
            p = frag.new_tag("p")

            lines = part.split('\n')
            for i, line in enumerate(lines):
                p.append(line)
                if i < len(lines) - 1:
                    p.append(frag.new_tag("br"))

            new_children.append(p)
        else:
            p = BeautifulSoup("", "lxml").new_tag("p")
            p.string = part
            new_children.append(p)

    # Clear span and reinsert clean HTML
    span.clear()
    for node in new_children:
        span.append(node)


def convert_chapter_to_html(block, div_for_you_said=None):
    html_parts = []

    # Split by speaker markers and also handle "data-you-said" placeholder
    segments = re.split(r'(You said:|ChatGPT said:)', block)

    current_speaker = None

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        if seg == "You said:":
            current_speaker = "you"
            continue
        elif seg == "ChatGPT said:":
            current_speaker = "chatgpt"
            continue

        # Wrap text based on speaker
        if current_speaker == "you":
            if (div_for_you_said == 'Y' or div_for_you_said == 'Y'):
                # Preserve inner HTML if any
                html_parts.append(f'<div class="you-said">{seg}</div><hr>')
            else:
                html_parts.append(f'\n\n<em><font color="red">{seg}</font></em><hr>\n\n')
        elif current_speaker == "chatgpt":
            html_parts.append(f'<div class="chatgpt-said">{seg}</div>')
        else:
            # Check for placeholder from whitespace-pre-wrap
            if 'data-you-said="true"' in seg:
                html_parts.append(f'<div class="you-said">{seg}</div><hr>')
            else:
                html_parts.append(f'<div>{seg}</div>')

    #print(html_parts)
    return "\n\n".join(html_parts)


def parse_conversation_to_chapters(text):
    """
    Parse conversation logs into chapters.
    Rule:
    - If pattern 'You said:... ChatGPT said:...' => one chapter
    - If pattern 'You said:... You said:...' => separate chapters
    """

    # Normalize newlines
    text = text.replace('\r', '')
    
    # Split on "You said:" occurrences
    parts = re.split(r'(You said:\s*)', text)
    chapters = []
    current_block = ""

    # Merge back the split markers and text pieces
    for i in range(1, len(parts), 2):  # step by 2 to catch marker + text
        marker = parts[i]
        content = parts[i+1] if i + 1 < len(parts) else ''
        block = marker + content
        block = block.strip()
        if block:
            current_block = block

            # Detect if ChatGPT reply is within the same section
            chatgpt_reply = re.search(r'(ChatGPT said:\s*.*?)(?=(You said:|$))', content, re.DOTALL)
            if chatgpt_reply:
                # One full You/ChatGPT pair = one chapter
                chapters.append(block.strip())
            else:
                # Only "You said:" without ChatGPT = own chapter
                chapters.append(block.strip())

    # Clean empty
    chapters = [c for c in chapters if c.strip()]
    return chapters


def html_to_epub(html_file, title, author, synopsis=None, series_id=None, div_for_you_said=None):
    with open(html_file, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Parse HTML
    soup = BeautifulSoup(html_content, 'lxml')

    # REPLACE THESE BELOW TO ACHIEVE : STRIP UI DIVS + FIX SPAN CONTENT
    '''
    # --- 🔄 Treat <div class="whitespace-pre-wrap"> as "You said:" ---
    for div in soup.find_all("div", class_="whitespace-pre-wrap"):
        # Extract inner HTML (keeps formatting)
        inner_html = div.decode_contents()
        # Replace div with a placeholder marker that includes inner HTML
        new_tag = soup.new_tag("span", **{"data-you-said": "true"})
        new_tag.append(BeautifulSoup(inner_html, 'lxml'))
        div.replace_with(new_tag)
    '''

    # START: STRIP UI DIVS + FIX SPAN CONTENT
    for div in soup.find_all("div", class_="whitespace-pre-wrap"):
        span = convert_whitespace_div_to_span(div, soup)

        parent = div
        while parent and parent.name == "div":
            cls = " ".join(parent.get("class", []))
            if any(x in cls for x in [
                "flex",
                "user-message-bubble-color",
                "corner-superellipse"
            ]):
                parent = parent.parent
            else:
                break

        # 1️⃣ Insert span into DOM
        parent.replace_with(span)

        # 2️⃣ NOW unwrap leftover UI divs (this is the key)
        unwrap_chatgpt_ui(span)
    # END: STRIP UI DIVS + FIX SPAN CONTENT

    # REPLACE ATTRIBUTES
    strip_all_attributes_selective(soup)

    # Extract full HTML content after preprocessing
    #text = soup.decode_contents()  # keeps HTML formatting
    text = extract_clean_messages(soup) #CLEAN THE MASSAGE INPUT SENT TO GPT

    # --- 🔍 Detect and Split into Chapters ---
    chapters_text = parse_conversation_to_chapters(text)
    if not chapters_text:
        print("⚠️ No valid conversation patterns found; using entire file as one chapter.")
        chapters_text = [text]

    # --- 📘 Create EPUB ---
    book = epub.EpubBook()
    book.set_identifier(series_id if series_id else 'id_' + title[:10])
    book.set_title(title)
    book.set_language('en')
    book.add_author(author)

    if synopsis:
        book.add_metadata('DC', 'description', synopsis)
    if series_id:
        book.add_metadata('DC', 'source', series_id)

    style = epub.EpubItem(uid="style_nav", file_name="style/style.css", media_type="text/css", content=EPUB_CSS)
    book.add_item(style)

    epub_chapters = []
    for i, chap_text in enumerate(chapters_text, 1):
        chap = epub.EpubHtml(title=f"Chapter {i}", file_name=f'chap_{i:02d}.xhtml', lang='en')
        html_body = convert_chapter_to_html(chap_text, div_for_you_said)
        #chap.content = f"<h1>Chapter {i}</h1>{html_body}"

        # START: EXPORT INDENTION
        #print(html_body)
        raw_html = f"<h1>Chapter {i}</h1>{html_body}"
        #print(raw_html)
        chap.content = pretty_xhtml(raw_html)
        # END: EXPORT INDENTION

        chap.add_item(style)
        book.add_item(chap)
        epub_chapters.append(chap)

    book.toc = tuple(epub_chapters)
    book.spine = ['nav'] + epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Add synopsis page if provided
    if synopsis:
        summary_page = epub.EpubHtml(title="Summary", file_name="summary.xhtml", lang='en')
        summary_html = f"<h1>Book Summary</h1><p>{synopsis}</p>"
        summary_page.content = summary_html
        book.add_item(summary_page)
        book.toc = (summary_page,) + book.toc
        book.spine = ['nav', summary_page] + epub_chapters

    # --- 💾 Save EPUB ---
    base_name = f"{title}_{author}"
    filename = f"{base_name}.epub"

    if synopsis:
        raw_filename = f"{base_name}_{synopsis}.epub"
        if len(raw_filename) > MAX_FILENAME_LENGTH:
            allowed_len = MAX_FILENAME_LENGTH - len(base_name) - len("_.epub")
            truncated_synopsis = synopsis[:allowed_len]
            filename = f"{base_name}_{truncated_synopsis}.epub"
        else:
            filename = raw_filename

    epub.write_epub(filename, book, {})
    print(f"✅ EPUB created: {filename}")



def main():
    if len(sys.argv) < 3:
        print("Usage: python HTML_TO_EPUB.py [FILENAME.HTML] [TITLE] [AUTHOR] [SYNOPSIS (optional)] [SERIES_ID (optional)] [USE DIV FOR YOU-SAID(optional)]")
        print("For including question div: python.exe .\HTML_TO_EPUB_GPT.py [FILENAME.HTML] [TITLE] [AUTHOR] [SYNOPSIS (optional)] [SERIES_ID (optional)] \"Y\"")
        sys.exit(1)

    html_file = sys.argv[1]
    title = sys.argv[2] 
    author = sys.argv[3] if len(sys.argv) > 3 else "ChatGPT"
    synopsis = sys.argv[4] if len(sys.argv) > 4 else None
    series_id = sys.argv[5] if len(sys.argv) > 5 else None
    div_for_you_said = None if len(sys.argv) <= 6 or (sys.argv[6] != 'Y' and sys.argv[6] != 'y') else sys.argv[6]

    if not os.path.exists(html_file):
        print(f"❌ File not found: {html_file}")
        sys.exit(1)

    html_to_epub(html_file, title, author=author, synopsis=synopsis, series_id=series_id, div_for_you_said=div_for_you_said)


if __name__ == "__main__":
    main()
