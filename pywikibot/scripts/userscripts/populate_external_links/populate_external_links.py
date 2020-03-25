#!/usr/bin/env python
"""populate_external_links.py

This Pywikibot script searches a list of web feeds, finds entries matched by
keywords or regexes, and adds the links to the "External links" section of
specified wiki pages.

SCRIPT OPTIONS
==============
(Script arguments available for this bot)

-config-type:x          Config type of "file" or "wiki".
                        For "file", it retrieves the config file locally using
                        the file path specified by the `-config-path`
                        argument.
                        For "wiki", it retrieves the config file on the wiki
                        using the page title specified by the
                        `-config-page-title` argument.

-config-path:x          File path of the config file. Used with
                        `-config-type:file` argument.

-config-page-title:x    Page title of the config file on the wiki. Used with
                        `-config-type:wiki` argument.

-group:n                How many pages to preload at once.
"""
"""
Copyright 2020 David Wong

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
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from operator import attrgetter
from enum import Enum
from copy import deepcopy
import math
import json
import feedparser

import mwparserfromhell
from mwparserfromhell.nodes.external_link import ExternalLink
import pywikibot
from pywikibot import pagegenerators, textlib
from pywikibot.bot import SingleSiteBot, NoRedirectPageBot
from pywikibot.comms.http import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class ConfigType(Enum):
    FILE = "file"
    WIKI = "wiki"

    def __str__(self):
        return self.value


CONFIG_FILENAME = "config.json"
CONFIG_PAGE_TITLE = f"MediaWiki:Populate external links/{CONFIG_FILENAME}"

COMMAND_OPTION = {
    "config_type": ConfigType.FILE,
    "config_path": f"./{CONFIG_FILENAME}",
    "config_page_title": CONFIG_PAGE_TITLE,

    "group": 50
}


def fetch_config_file(path):
    with open(path, encoding="utf8") as file:
        config = json.load(file)
        return config


def fetch_config_wiki_page(title):
    site = pywikibot.Site()
    page = pywikibot.Page(site, title)

    if not page.exists():
        raise pywikibot.exceptions.NoPage(page)

    page_text = page.text
    config = json.loads(page_text)
    return config


def fetch_config(option):
    config_type = option["config_type"]
    if config_type == ConfigType.WIKI:
        config_page_title = option["config_page_title"]
        try:
            return fetch_config_wiki_page(config_page_title)
        except (pywikibot.exceptions.NoPage, json.decoder.JSONDecodeError) as exception:
            pywikibot.exception(exception, tb=True)
            pywikibot.output("")
            pywikibot.output("")

    config_path = option["config_path"]
    return fetch_config_file(config_path)


def fetch_feeds(sources):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(feedparser.parse, source) for source in sources]
        feeds = [future.result() for future in concurrent.futures.as_completed(futures)]
        return feeds


keyword_compiled_pattern = {}


def execute_queries(text, queries):
    query_results = []
    number_of_keyword_matches = 0
    number_of_regex_matches = 0
    for q, query in enumerate(queries):
        # Search by keywords.
        keyword_matches = []
        if "keywords" in query:
            keywords = query["keywords"]
            for keyword in keywords:
                compiled_pattern = None
                if keyword in keyword_compiled_pattern:
                    compiled_pattern = keyword_compiled_pattern[keyword]
                else:
                    compiled_pattern = re.compile(r"\b({0})\b".format(keyword), flags=re.IGNORECASE)
                    keyword_compiled_pattern[keyword] = compiled_pattern

                result = compiled_pattern.search(text)
                if result is not None:
                    keyword_matches.append(result)
                    number_of_keyword_matches += 1

        # Search by regexes.
        regex_matches = []
        if "regexes" in query:
            regexes = query["regexes"]
            for regex in regexes:
                pattern = None
                flags = 0
                if isinstance(regex, str):
                    pattern = regex
                elif isinstance(regex, dict):
                    if "pattern" in regex:
                        pattern = regex["pattern"]
                    else:
                        pywikibot.error(f"Regex \"{regex}\" must have a pattern.")
                        pywikibot.output("")
                        continue

                    if "flags" in regex:
                        flags = regex["flags"]
                        if isinstance(flags, str) or isinstance(flags, int):
                            flags = [flags]
                        elif not isinstance(flags, list):
                            pywikibot.error(f"Flags \"{flags}\" must be a list, string, or int.")
                            pywikibot.output("")
                            continue

                        f = 0
                        for flag in flags:
                            if isinstance(flag, str):
                                f += getattr(re, flag)
                            elif isinstance(flag, int):
                                f += flag
                            else:
                                pywikibot.error(f"Flag \"{flag}\" must be a string or int.")
                                pywikibot.output("")
                                continue

                        flags = f
                else:
                    pywikibot.error(f"Regex \"{regex}\" must be a string or dict.")
                    pywikibot.output("")
                    continue

                compiled_pattern = re.compile(pattern, flags=flags)

                result = compiled_pattern.search(text)
                if result is not None:
                    regex_matches.append(result)
                    number_of_regex_matches += 1

        query_results.append({
            "q": q,
            "query": query,
            "keyword_matches": keyword_matches,
            "regex_matches": regex_matches
        })

    return query_results
    # return query_results, number_of_keyword_matches


def search_entries(feed, queries, matches):
    entries = feed.entries
    for entry in entries:
        title = entry.title

        query_results = execute_queries(title, queries)
        for query_result in query_results:
            keyword_matches = query_result["keyword_matches"]
            regex_matches = query_result["regex_matches"]
            if len(keyword_matches) > 0 or len(regex_matches) > 0:
                q = query_result["q"]
                matches[q].append(entry)


get_publish_date = attrgetter("published_parsed")


def process_matches(queries, matches):
    title_entries = {}

    # Add all matches to a page in `page_entries`.
    for q, query in enumerate(queries):
        entries = matches[q]
        if len(entries) > 0:
            titles = query["pages"]
            for title in titles:
                if title not in title_entries:
                    title_entries[title] = []

                title_entries[title].extend(entries)

    for title, entries in title_entries.items():
        # Sort entries by date.
        entries.sort(key=get_publish_date)

        # Remove duplicates.
        unique_entries = []
        unique_titles = set()
        unique_links = set()
        for entry in entries:
            entry_link = entry.link
            if entry_link in unique_links:
                pywikibot.warning(f"An entry for page \"{title}\" was discarded because its link \"{entry_link}\" was a duplicate.")
                pywikibot.output("")
                continue

            entry_title = entry.title
            if title in unique_titles:
                pywikibot.warning(f"An entry for page \"{title}\" has the same title \"{entry_title}\" as another entry.")
                pywikibot.output("")

            unique_titles.add(entry_title)
            unique_links.add(entry_link)
            unique_entries.append(entry)

        title_entries[title] = unique_entries

    return title_entries


def get_title_entries(feeds, queries):
    matches = [[] for i in range(len(queries))]

    for feed in feeds:
        if "bozo_exception" in feed:
            pywikibot.exception(feed["bozo_exception"])
            pywikibot.output("")

        search_entries(feed, queries, matches)

    title_entries = process_matches(queries, matches)

    return title_entries


def format_entry_to_link_markup(entry):
    title = entry.title
    link = entry.link
    external_link = ExternalLink(link, title)
    # return f"* [{link} {title}]"
    return f"* {external_link}"


def map_entries_to_list_markup(entries):
    return map(format_entry_to_link_markup, entries)


def format_entries_to_list_markup(entries):
    return "\n".join(map_entries_to_list_markup(entries))


def get_unique_entries(title, previous_external_links, entries):
    """Merge entries by excluding duplicate links that already exist."""

    unique_entries = []
    unique_titles = set()
    unique_links = set()

    # Add titles and links from existing external links.
    for previous_external_link in previous_external_links:
        title = str(previous_external_link.title)
        link = str(previous_external_link.url)
        unique_titles.add(title)
        unique_links.add(link)

    # Check for titles and links that already exist, and remove duplicates.
    for entry in entries:
        link = entry.link
        if link in unique_links:
            pywikibot.warning(f"An entry for page \"{title}\" was discarded because its link \"{link}\" was a duplicate.")
            pywikibot.output("")
            continue

        title = entry.title
        if title in unique_titles:
            pywikibot.warning(f"An entry for page \"{title}\" has the same title \"{title}\" as another entry.")
            pywikibot.output("")

        unique_titles.add(title)
        unique_links.add(link)
        unique_entries.append(entry)

    return unique_entries


def log_external_links_added(number_of_external_links, title, text):
    if number_of_external_links > 0:
        pywikibot.output("Add {0} {1} to page \"{2}\":{3}".format(
            number_of_external_links,
            "external link" + ("s" if number_of_external_links != 1 else ""),
            title,
            text
        ))


def populate_external_links(page_title, page_text, entries):
    wikicode = mwparserfromhell.parse(page_text)

    number_of_external_links_added = 0

    external_link_sections = wikicode.get_sections(levels=[2], matches=r"External links", include_headings=False)
    if len(external_link_sections) > 0:
        for external_link_section in external_link_sections[-1:]:
            unique_entries = entries
            text = "\n" + format_entries_to_list_markup(entries) + "\n\n"

            subsections = external_link_section.get_sections(include_headings=True)
            if len(subsections) > 0:
                lead = subsections[0]
                previous_node = lead

                previous_external_links = lead.filter_external_links(recursive=False)
                last_external_link_index = -1
                if len(previous_external_links) > 0:
                    last_external_link = previous_external_links[-1]
                    last_external_link_index = lead.index(last_external_link)
                    previous_node = last_external_link

                lines = lead.filter_text(recursive=False)
                if len(lines) > 0:
                    last_line = lines[-1]
                    last_line_index = lead.index(last_line)
                    if last_external_link_index < last_line_index:
                        previous_node = last_line

                unique_entries = get_unique_entries(page_title, previous_external_links, entries)

                text = "\n" + format_entries_to_list_markup(unique_entries) + "\n\n"

                external_link_section.replace(previous_node, previous_node.rstrip() + text)
            else:
                external_link_section.append(text)

            number_of_unique_entries = len(unique_entries)
            number_of_external_links_added += number_of_unique_entries
            log_external_links_added(number_of_unique_entries, page_title, text)
    else:
        heading = "\n\n== External links =="
        content = "\n" + format_entries_to_list_markup(entries) + "\n\n"
        text = heading + content

        lines = wikicode.filter_text(recursive=False)
        if len(lines) > 0:
            last_line = lines[-1]
            wikicode.replace(last_line, last_line.rstrip() + text)
        else:
            wikicode.append(text)

        number_of_unique_entries = len(entries)
        number_of_external_links_added += number_of_unique_entries
        log_external_links_added(number_of_unique_entries, page_title, content)

    revised_page_text = wikicode.rstrip()

    return revised_page_text, number_of_external_links_added


def output_separator(title, character, line_length=80):
    separator_line = (character * line_length)
    buffer = [
        separator_line,
        "\n"
    ]

    if isinstance(title, str):
        title_length = len(title)
        if title_length > 0:
            padded_line_length = (line_length - 2)
            if title_length < padded_line_length:
                side = ((padded_line_length - title_length) / 2)
                left_side_length = math.floor(side)
                right_side_length = math.ceil(side)
                left_side = (character * left_side_length)
                right_side = (character * right_side_length)
                buffer = [
                    left_side,
                    " " + title + " ",
                    right_side,
                    "\n"
                ]
            else:
                buffer.append("\n" + title + ":\n")

    return "".join(buffer)


revised_page_text_separator = output_separator("Revised page text", "-")
save_result_separator = output_separator("Save result", "-")


def save_external_links(page, title, entries):
    pywikibot.output(output_separator(f"Page \"{title}\"", "="))

    page_text = page.text

    revised_page_text, number_of_external_links_added = populate_external_links(title, page_text, entries)

    if number_of_external_links_added <= 0:
        pywikibot.output(f"No external links added to page \"{title}\".")
        pywikibot.output("")
        return

    pywikibot.output(revised_page_text_separator)
    pywikibot.output(revised_page_text)
    pywikibot.output("")

    page.text = revised_page_text

    pywikibot.output(save_result_separator)

    page.save(
        summary="Add {0} {1}.".format(
            number_of_external_links_added,
            "external link" + ("s" if number_of_external_links_added != 1 else ""),
        ),
        minor=False
    )

    pywikibot.output("")


def PageEntryGenerator(site=None, title_entries=None, page_entries=None):
    if title_entries is None:
        for page, entries in page_entries.items():
            yield page
    else:
        if page_entries is None:
            page_entries = {}

        if site is None:
            site = pywikibot.Site()

        for title, entries in title_entries.items():
            page = pywikibot.Page(site, title)
            page_entries[page] = entries
            yield page


class PopulateExternalLinksBot(SingleSiteBot, NoRedirectPageBot):
    """Populate external links bot."""

    def __init__(self, site, generator, title_entries, page_entries, **kwargs):
        """
        Initializer.
        :param site: The site.
        :param generator: The page generator that determines on which pages to work.
        :param title_entries: The `title_entries`.
        :param page_entries: The `page_entries`.
        :param kwargs:
        """

        self.availableOptions.update({
            "config_type": kwargs["config_type"],
            "config_path": kwargs["config_path"],
            "config_page_title": kwargs["config_page_title"],

            "group": kwargs["group"]
        })

        super().__init__(site=site, generator=generator, **kwargs)

        self.title_entries = title_entries
        self.page_entries = page_entries

    def run(self):
        super().run()
        pywikibot.output("")

    def treat_page(self):
        page = self.current_page
        title = page.title()
        page_entries = self.page_entries
        entries = (page_entries[page] if page in page_entries else self.title_entries[title])
        save_external_links(page, title, entries)


def main(*args):
    option = deepcopy(COMMAND_OPTION)

    local_args = pywikibot.handle_args(args)
    generator_factory = pagegenerators.GeneratorFactory()

    for arg in local_args:
        key, seperator, value = arg.partition(":")
        stripped_value = value.strip()
        if key == "-config-type":
            config_type = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter config type:").strip())
            option["config_type"] = ConfigType(config_type.lower())
        elif key == "-config-path":
            config_path = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter config file path:").strip())
            option["config_path"] = config_path
        elif key == "-config-page-title":
            config_page_title = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter config page title:").strip())
            option["config_page_title"] = config_page_title
        elif key == "-group":
            group = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter group:").strip())
            option["group"] = int(group)
        else:
            generator_factory.handleArg(arg)

    config = fetch_config(option)
    sources = config["sources"]
    queries = config["queries"]

    feeds = fetch_feeds(sources)

    title_entries = get_title_entries(feeds, queries)
    page_entries = {}

    site = pywikibot.Site()
    generator = generator_factory.getCombinedGenerator(
        pagegenerators.PreloadingGenerator(
            PageEntryGenerator(site=site, title_entries=title_entries, page_entries=page_entries),
            groupsize=option["group"]
        )
    )
    if generator is None:
        pywikibot.bot.suggest_help(missing_generator=True)
        return

    bot = PopulateExternalLinksBot(site, generator, title_entries, page_entries, **option)
    bot.run()


if __name__ == "__main__":
    main()