#!/usr/bin/python3
"""
Copyright 2019 David Wong

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import re
from warnings import warn
import pywikibot
from pywikibot import pagegenerators, textlib
from pywikibot.comms.http import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

category_mimes = {
    "Images": {
        "patterns": [
            r"image/.*"
        ],
        "literals": [
            "image/apng",
            "image/bmp",
            "image/gif",
            "image/x-icon",
            "image/jpeg",
            "image/png",
            "image/svg+xml",
            "image/tiff",
            "image/webp",
            "image/vnd.microsoft.icon"
        ]
    },
    "Audios": {
        "patterns": [
            r"audio/.*"
        ],
        "literals": [
            "audio/aac",
            "audio/wave",
            "audio/wav",
            "audio/x-wav",
            "audio/x-pn-wav",
            "audio/webm",
            "audio/ogg",
            "audio/opus",
            "audio/midi",
            "audio/x-midi",
            "audio/mpeg",
            "audio/3gpp",
            "audio/3gpp2"
        ]
    },
    "Videos": {
        "patterns": [
            r"video/.*"
        ],
        "literals": [
            "video/x-msvideo",
            "video/webm",
            "video/ogg",
            "video/mpeg",
            "video/mp2t",
            "video/3gpp",
            "video/3gpp2"
        ]
    },
    "Audios or videos": [
        "application/ogg"
    ],
    "PDFs": "application/pdf",

    "Microsoft Word documents": {
        "patterns": [
            r"application/msword.*",
            r"application/vnd\.openxmlformats-officedocument\.wordprocessingml.*"
            r"application/vnd\.ms-word.*"
        ],
        "literals": [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
            "application/vnd.ms-word.document.macroEnabled.12",
            "application/vnd.ms-word.template.macroEnabled.12"
        ]
    },
    "Microsoft PowerPoint documents": {
        "patterns": [
            r"application/vnd\.ms-powerpoint.*",
            r"application/vnd\.openxmlformats-officedocument\.presentationml.*"
        ],
        "literals": [
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.presentationml.template",
            "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
            "application/vnd.ms-powerpoint.addin.macroEnabled.12",
            "application/vnd.ms-powerpoint.presentation.macroEnabled.12",
            "application/vnd.ms-powerpoint.template.macroEnabled.12",
            "application/vnd.ms-powerpoint.slideshow.macroEnabled.12"
        ]
    },
    "Microsoft Excel documents": {
        "patterns": [
            r"application/vnd\.ms-excel.*",
            r"application/vnd\.openxmlformats-officedocument\.spreadsheetml.*"
        ],
        "literals": [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.template",
            "application/vnd.ms-excel.sheet.macroEnabled.12",
            "application/vnd.ms-excel.template.macroEnabled.12",
            "application/vnd.ms-excel.addin.macroEnabled.12",
            "application/vnd.ms-excel.sheet.binary.macroEnabled.12"
        ]
    },
    "Microsoft Visio documents": {
        "patterns": [
            r"application/vnd\.ms-visio.*"
        ],
        "literals": [
            "application/visio",
            "application/x-visio",
            "application/vnd.visio",
            "application/visio.drawing",
            "application/vsd",
            "application/x-vsd",
            "image/x-vsd",
            "application/vnd.ms-visio.drawing",
            "application/vnd.ms-visio.viewer",
            "application/vnd.ms-visio.drawing.main+xml",
            "application/vnd.ms-visio.template.main+xml",
            "application/vnd.ms-visio.stencil.main+xml",
            "application/vnd.ms-visio.drawing.macroEnabled.main+xml",
            "application/vnd.ms-visio.template.macroEnabled.main+xml",
            "application/vnd.ms-visio.stencil.macroEnabled.main+xml"
        ]
    },

    "OpenDocument text documents": "application/vnd.oasis.opendocument.text",
    "OpenDocument presentation documents": "application/vnd.oasis.opendocument.presentation",
    "OpenDocument spreadsheet documents": "application/vnd.oasis.opendocument.spreadsheet",
    "OpenDocument graphics documents": "application/vnd.oasis.opendocument.graphics"
}


def flatten_category_mimes():
    """
    Flatten the `category_mimes` dictionary to allow hashtable lookup by MIME type.
    :return:
    """

    mime_categories = {}
    pattern_category_regexes = []

    for category, mimes in category_mimes.items():
        c = category
        if category.startswith("Microsoft ") and category.endswith(" documents"):
            c = ["Office documents", "Microsoft Office documents", category]
        elif category.startswith("OpenDocument ") and category.endswith(" documents"):
            c = ["Office documents", "OpenDocument documents", category]

        if isinstance(mimes, str):
            mime_categories[mimes.lower()] = c
        else:
            literals = mimes

            if isinstance(mimes, dict):
                if "literals" in mimes:
                    literals = mimes["literals"]

                if "patterns" in mimes:
                    patterns = mimes["patterns"]
                    if isinstance(patterns, str):
                        patterns = [patterns]

                    for p in patterns:
                        regex = re.compile(p, flags=re.IGNORECASE)
                        pattern_category_regexes.append({
                            "pattern": p,
                            "category": c,
                            "regex": regex
                        })

            for m in literals:
                mime_categories[m.lower()] = c

    return mime_categories, pattern_category_regexes


mime_categories, pattern_category_regexes = flatten_category_mimes()


def remove_categories():
    site = pywikibot.Site()
    category = pywikibot.Category(site, "Category:Files")
    generator = pagegenerators.PreloadingGenerator(pagegenerators.CategorizedPageGenerator(category=category))
    for page in generator:
        pywikibot.output(vars(page))
        pywikibot.output(page.text)

        page.put(
            textlib.replaceCategoryLinks(page.get(), [], site=page.site),
            asynchronous=True,
            summary="Remove categories."
        )


def build_categories(mime_category):
    categories = ["Files"]

    if isinstance(mime_category, list):
        categories += mime_category
    else:
        categories.append(mime_category)

    return categories


def categorize_files():
    site = pywikibot.Site()
    generator = pagegenerators.PreloadingGenerator(pagegenerators.UnCategorizedImageGenerator(site=site))
    i = 0
    for page in generator:
        i += 1

        pywikibot.output("")

        pywikibot.output("Page " + str(i) + ":")

        if not page.is_filepage():
            pywikibot.error("Page \"" + page.title(as_link=True) + "\" is not a file. Skipping page...")
            pywikibot.output("")
            continue

        file_page = pywikibot.FilePage(page)
        file_info = file_page.latest_file_info
        mime = file_info.mime.lower()

        pywikibot.output("    Title: " + file_page.title(as_link=True))
        pywikibot.output("    URI: " + file_page.full_url())
        pywikibot.output("    MIME type: " + mime)

        # Find a matching category for the MIME type.
        mime_category = None
        if mime in mime_categories:
            mime_category = mime_categories[mime]
        else:
            warn("Unrecognized MIME type \"" + mime + "\". Attempting to search by regex...")

            for pattern_category_regex in pattern_category_regexes:
                regex = pattern_category_regex["regex"]
                if regex.search(mime) is not None:
                    category = pattern_category_regex["category"]
                    warn("Found category \"" + category + "\" for unrecognized MIME type \"" + mime + "\".")
                    mime_category = category
                    break

        if mime_category is None:
            pywikibot.error("No category found for MIME type \"" + mime + "\". Skipping file...")
            pywikibot.output("")
            continue

        # Build categories, and add them to the file page.
        categories = build_categories(mime_category)
        pywikibot.output("    Add categories: " + ", ".join(categories))

        page_categories = list(map(lambda c: pywikibot.Page(site, "Category:" + c), categories))
        category_wikilinks = list(map(lambda c: "[[Category:" + c + "|" + c + "]]", categories))
        summary = "Add the categor" + ("y" if len(category_wikilinks) <= 1 else "ies") + " " + ", ".join(category_wikilinks) + "."

        file_page.put(
            textlib.replaceCategoryLinks(file_page.get(), page_categories, site=file_page.site, addOnly=True),
            asynchronous=True,
            summary=summary
        )


def main(*args):
    # remove_categories()
    # pywikibot.output("")
    # pywikibot.output("")
    categorize_files()
    pywikibot.output("")


if __name__ == "__main__":
    main()