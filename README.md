# SAVE CHATGPT TO EBOOK
Save chatGPT Conversation into EPUB


## DOWNLOAD CHAT GPT CONVERSATION TO HTML & EPUB (PART 1 - BASIC CONVERSION)

### Depedencies Installation
```
pip install ebooklib beautifulsoup4 lxml
```

### Usage: 
1. Open the chatGPT file you want to download in Avast Browser or Google Chrome

2. Right click > Inspect element > Find (Ctrl+F) > ```flex flex-col text-sm......```

3. Copy all content of the DIV that showed under ```flex flex-col text-sm......```

4. Make a new FILENAME.HTML file in TEXT EDITOR :
```
<html>
<head>
    <style>
        .whitespace-pre-wrap {
            white-space: pre-wrap;
            white-space-collapse: preserve;
            text-wrap-mode: wrap;
            background-color: #F4F4F4;
        }
    </style>
</head>
<body>
    COPY THE DIV FOUND FROM THE ```flex flex-col text-sm...``` TO THIS PART
<\body>
<\html>
```

5. Clean the HTML (optional for decrease the HTML size, not mandatory can be skipped to 6):
```
python HTML_ATTRIBUTE_STRIPPER.py [FILENAME.HTML]
```
This step will turn `[FILENAME.HTML]` into `[FILENAME_CLEANED.HTML]`

6. Convert to EPUB:
```
python HTML_TO_EPUB_GPT.py [FILENAME.HTML or FILENAME_CLEANED.HTML] [TITLE] [AUTHOR] [SYNOPSIS (optional - in quotes)] [SERIES_ID (optional)]
```

Example : `python HTML_TO_EPUB_GPT.py "myfile.html" "The Epic Tale" "John Smith" "A thrilling journey through time and space lorem ipsum dolor sit amet consitutum tetum lorem ipsum dolor sit amet domenicus tecum ave lorom lorem ipsum dolor sit amet amet tecum" "Series123"`


## DOWNLOAD CHAT GPT CONVERSATION TO HTML & EPUB (PART 2 - Cosmetic fix - Optional to fix the ToC - using Calibre EBook Management)

7. Open the exported EPUB with Calibre EBook Management (Edit E-Book) [https://calibre-ebook.com/download]

8. For changing the chapter title find the first `<h1>` after `<body>`, then:
```
Edit ➜ Table of Content ➜ Edit Table of Contents ➜ Generate ToC from XPath ➜ Fill Level 1 ToC, with:
```

```
.//*[local-name()='body']/*[local-name()='h1'][1][starts-with(normalize-space(.), 'Chapter')]
```

or

```
.//*[local-name()='h1'][starts-with(normalize-space(.), 'Chapter')][1]
```

9. If you need to re-arrange the chapter title, just rearrange using the Calibre EBook Management (Edit E-Book) in the left navbar (FILE BROWSER -> TEXT)

10. To fix the chapter title into sequence again after did step 8:

For example now the sequence become : `chapter 1.xhtml | chapter 3.xhtml | chapter 4.xhtml`.

Save and close the Calibre EBook Management (Edit E-Book), and then run :

```
python AUTO_RENUMBERING_EPUB_CHAPTER.py book_title.epub [keep_title optional (YES/NO)]
```

Explanation: keep_title optional (YES/NO) whether keeping filename annotation Chapter_NUMBER_annotation.xhtml; if unsure just empty and it will generate only Chapter_number

After you run the python script for rename the sequence of .xhtml, reopen Calibre EBook Management (Edit E-Book). Then re-run steps (7)




## STRIP ATTRIBUTE FROM CHATGPT COPIED HTML (COSMETIC FIX - OPTIONAL to decrease the saved HTML size without re-run whole page using `HTML_ATTRIBUTE_STRIPPER.py`)

This is a simple browser-based tool that removes unwanted HTML attributes based on predefined rules.

It runs entirely in your browser.  
No installation.  
No server.  
No uploads.  
No data stored.
Everything is processed locally in memory.

### What This Tool Does

When you click **Process**, the tool will:

-   Strip all attributes from these tags: ```h1–h6, p, em, b, strong, hr, br, ol, ul, li, blockquote, table, thead, tbody, tr, th, td```
        
-   Preserve only this class if present: ```whitespace-pre-wrap```
        
-   Force all ```<table>``` elements to have: border="1"
    

All other attributes are removed.

The structure and content of the HTML remain unchanged.



### How to Use

1. Open `index.html` in browser. No internet connection required after download.

2. Provide HTML. You have two options:
    1.  Copy your HTML. Paste it into the large text box.
    2.  Click the file selector at the top. Choose an `.html` or `.htm` file. The file content will automatically appear in the text box.

3. Click the **Process** button.

4. The cleaned HTML will immediately replace the content inside the text box.

5. Select all text in the box. Copy it. Paste it wherever you need.
    
6. If you want to save it as a file, simply paste it into a new `.html` file and save.



