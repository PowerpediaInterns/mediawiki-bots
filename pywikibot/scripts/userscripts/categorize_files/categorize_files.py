#!/usr/bin/env python
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

import pywikibot
from pywikibot import pagegenerators, textlib
from pywikibot.bot import SingleSiteBot, ExistingPageBot, NoRedirectPageBot
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
            "audio/x-flac",
            "application/flac",
            "audio/flac",
            "application/x-flac",
            "audio/wav",
            "application/x-wave",
            "audio/wave",
            "application/wave",
            "application/wav",
            "application/x-wav",
            "audio/x-wave",
            "audio/x-wav",
            "audio/x-pn-wav",
            "audio/mp3",
            "application/mp3",
            "application/x-mp3",
            "audio/mpg",
            "audio/mpeg3",
            "audio/x-mp3",
            "audio/x-mpegaudio",
            "audio/mpeg",
            "audio/x-mpeg3",
            "audio/x-mpg",
            "audio/x-mpeg",
            "audio/mp1",
            "application/mp1",
            "application/aiff",
            "audio/aiff",
            "application/x-aif",
            "application/aif",
            "application/x-aiff",
            "audio/x-aifc",
            "audio/x-aiff",
            "audio/aif",
            "audio/aifc",
            "audio/x-aif",
            "audio/m4a",
            "audio/mp4",
            "application/x-m4a",
            "application/x-m4p",
            "audio/mpeg4",
            "audio/x-m4b",
            "audio/x-m4a",
            "audio/x-m4p",
            "audio/x-mp4",
            "audio/x-ms-wma",
            "application/x-ms-wma",
            "application/wma",
            "audio/wma",
            "audio/x-scpls",
            "audio/x-mpegurl",
            "audio/x-ms-asf",
            "audio/x-ms-wax",
            "audio/x-ms-wvx",
            "audio/aacp",
            "audio/aac",
            "audio/3gpp",
            "audio/3gpp2",
            "audio/x-aac",
            "audio/x-ogg",
            "audio/vorbis",
            "audio/ogg",
            "audio/opus",
            "audio/webm",
            "audio/midi",
            "audio/x-midi",
            "audio/x-matroska",
            "audio/speex"
        ]
    },
    "Videos": {
        "patterns": [
            r"video/.*"
        ],
        "literals": [
            "video/3gpp",
            "video/3gpp2",
            "video/avi",
            "video/mkv",
            "video/mp4",
            "video/mp4v-es",
            "video/mpeg",
            "video/mp2t",
            "video/quicktime",
            "video/x-quicktime",
            "video/webm",
            "video/ogg",
            "video/theora",
            "video/x-m4v",
            "video/x-matroska",
            "video/x-matroska-3d",
            "video/x-mkv",
            "video/x-ms-asf",
            "video/x-ms-avi",
            "video/x-ms-video",
            "video/x-ms-wax",
            "video/x-ms-wmv",
            "video/x-ms-wvx",
            "video/x-msvideo"
        ]
    },
    "Audios or videos": [
        "application/ogg",
        "application/x-ogg",
        "application/mpeg",
        "application/mpeg3",
        "application/mpeg4",
        "application/mp4"
        "application/x-m4b",
        "application/x-mp4"
    ],
    "PDFs": "application/pdf",
    "Text files": "text/plain",

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
    Flatten the `category_mimes` dictionary to allow hashtable lookups by MIME type.
    :return:
    """

    mime_categories = {}
    pattern_category_regexes = []

    for category, mimes in category_mimes.items():
        c = category
        if category.endswith(" documents"):
            c = ["Office documents"]
            if category.startswith("Microsoft "):
                c.append("Microsoft Office documents")
            elif category.startswith("OpenDocument "):
                c.append("OpenDocument documents")
            c.append(category)

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


def build_categories(mime_category):
    categories = [
        # "Files"
    ]

    if isinstance(mime_category, list):
        categories += mime_category
    else:
        categories.append(mime_category)

    return categories


def categorize_file_page(site, page, p=0):
    status = {
        "f": 0,
        "p": 1,
        "w": 0,
        "e": 0
    }

    pywikibot.output(f"Page {p + 1}:")

    if not page.is_filepage():
        pywikibot.error("Page \"" + page.title(as_link=True) + "\" is not a file page. Skipping page...")
        pywikibot.output("")
        status["e"] += 1
        return status

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
        pywikibot.warning(f"Unrecognized MIME type \"{mime}\". Attempting to search by regex...")
        status["w"] += 1

        for pattern_category_regex in pattern_category_regexes:
            regex = pattern_category_regex["regex"]
            if regex.search(mime) is not None:
                category = pattern_category_regex["category"]
                pywikibot.warning(f"Found category \"{category}\" for unrecognized MIME type \"{mime}\".")
                status["w"] += 1
                mime_category = category
                break

    if mime_category is None:
        pywikibot.error(f"No category found for MIME type \"{mime}\". Skipping file page...")
        pywikibot.output("")
        status["e"] += 1
        return status

    # Build categories, and add them to the file page.
    categories = build_categories(mime_category)
    pywikibot.output("    Add categories: " + ", ".join(categories))

    page_categories = []
    category_wikilinks = []
    for category in categories:
        page_category = pywikibot.Page(site, "Category:" + category)
        page_categories.append(page_category)

        category_wikilink = "[[Category:{0}|{0}]]".format(category)
        category_wikilinks.append(category_wikilink)

    file_page.text = textlib.replaceCategoryLinks(file_page.text, page_categories, site=file_page.site, addOnly=True)

    summary = "Add the {0} {1}.".format(
        "categor" + ("y" if len(category_wikilinks) <= 1 else "ies"),
        ", ".join(category_wikilinks)
    )

    file_page.save(
        summary=summary,
        minor=False
    )

    status["f"] += 1

    return status


def create_report(f, p, w, e):
    return ("Categorized {0} {1} out of {2} {3} ({4:.2%}) with {5} {6} and {7} {8}.".format(
        f,
        "file page" + ("s" if f != 1 else ""),
        p,
        "page" + ("s" if p != 1 else ""),
        ((f / p) if p != 0 else 1),
        w,
        "warning" + ("s" if w != 1 else ""),
        e,
        "error" + ("s" if e != 1 else "")
    ))


class CategorizerBot(SingleSiteBot, ExistingPageBot, NoRedirectPageBot):
    """Categorizer bot."""

    def __init__(self, site, generator, **kwargs):
        """
        Initializer.
        :param generator: The page generator that determines on which pages to work.
        :param kwargs:
        """

        self.availableOptions.update({
            'example': False,
        })

        super(CategorizerBot, self).__init__(site=site, generator=generator, **kwargs)

        self.status = {
            "f": 0,
            "p": 0,
            "w": 0,
            "e": 0
        }

    def update_status(self, status):
        combined_status = self.status
        for key in status:
            if key in combined_status:
                combined_status[key] += status[key]
            else:
                combined_status[key] = status[key]
        self.status = combined_status
        return combined_status

    def output_report(self):
        status = self.status
        report = create_report(**status)

        pywikibot.output("")
        pywikibot.output(report)

    def run(self):
        super(CategorizerBot, self).run()
        pywikibot.output("")

    def exit(self):
        self.output_report()
        super(CategorizerBot, self).exit()

    def treat_page(self):
        site = self.site
        page = self.current_page
        status = categorize_file_page(site, page, p=self.status["p"])
        self.update_status(status)


def remove_categories():
    site = pywikibot.Site()
    category = pywikibot.Category(site, "Category:Files")
    generator = pagegenerators.PreloadingGenerator(pagegenerators.CategorizedPageGenerator(category=category))
    for page in generator:
        pywikibot.output("")

        pywikibot.output(vars(page))
        pywikibot.output(page.text)

        page.text = textlib.replaceCategoryLinks(page.text, [], site=page.site)

        page.save(
            summary="Remove categories.",
            # asynchronous=True,
        )


def main(*args):
    option = {}

    local_args = pywikibot.handle_args(args)
    generator_factory = pagegenerators.GeneratorFactory()

    for arg in local_args:
        if arg == "-example":
            option["example"] = True
        else:
            generator_factory.handleArg(arg)

    site = pywikibot.Site()
    generator = generator_factory.getCombinedGenerator(
        pagegenerators.UnCategorizedImageGenerator(site=site),
        preload=True
    )
    if generator is None:
        pywikibot.bot.suggest_help(missing_generator=True)
        return

    bot = CategorizerBot(site, generator, **option)
    bot.run()

    # remove_categories()
    # pywikibot.output("")


if __name__ == "__main__":
    main()