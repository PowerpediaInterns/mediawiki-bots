#!/usr/bin/env python
"""feed_external_links.py

This Pywikibot script searches a list of web feeds, finds entries matched by
keywords or regexes, and adds the links to the "External links" section of
specified wiki pages.

SCRIPT OPTIONS
==============
(Arguments available for this script)

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

-history-path:x         File path of the history file.

-max-add:n              How many times a unique link is added to a page.
                        An argument for `-history-path` must be specified.

-group:n                How many pages to preload at once.

-proxy:x                Specify the same proxy as both HTTP and HTTPS for
                        all sources.

-http-proxy:x           Specify an HTTP proxy for all sources.

-https-proxy:x          Specify an HTTPS proxy for all sources.

-proxies-path:x         File path of the proxies file.
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

import math
import json
import re
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from operator import attrgetter
from enum import Enum
from copy import deepcopy
from typing import Any, Optional, Union, TypedDict, Pattern, Match, List, Dict, Tuple, Set, Iterable, Iterator, Generator
from urllib.request import ProxyHandler

import feedparser
from feedparser import FeedParserDict

import mwparserfromhell
from mwparserfromhell.nodes.external_link import ExternalLink
import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import SingleSiteBot, NoRedirectPageBot
from pywikibot.comms.http import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class ConfigQueryRegexTypedDict(TypedDict, total=False):
    pattern: str
    flags: Union[str, int, List[Union[str, int]]]


class ConfigQueryTypedDict(TypedDict, total=False):
    pages: List[str]
    keywords: List[str]
    regexes: List[Union[str, ConfigQueryRegexTypedDict]]


class ConfigTypedDict(TypedDict):
    sources: List[str]
    queries: List[ConfigQueryTypedDict]


ConfigsDataType = List[ConfigTypedDict]
ConfigResultDataType = Union[ConfigTypedDict, ConfigsDataType]


class ConfigType(Enum):
    FILE: str = "file"
    WIKI: str = "wiki"

    def __str__(self) -> str:
        return self.value


class CommandOptionTypedDict(TypedDict, total=False):
    config_type: ConfigType
    config_path: str
    config_page_title: str
    history_path: str
    max_add: int

    group: int

    proxy: str
    http_proxy: str
    https_proxy: str
    proxies_path: str


class BotOptionTypedDict(TypedDict, total=False):
    pass


class QueryResultTypedDict(TypedDict):
    q: int
    query: ConfigQueryTypedDict
    keyword_matches: List[Match]
    regex_matches: List[Match]


ProxiesValueDataType = Union[str, Dict[str, str]]
ProxiesDataType = Dict[str, ProxiesValueDataType]


class SourceOptionValueTypedDict(TypedDict, total=False):
    proxies: Dict[str, str]
    has_proxy: bool
    proxy_regex: str
    handlers: Optional[Union[ProxyHandler, List[Any]]]


SourceOptionDataType = Dict[str, SourceOptionValueTypedDict]


class SourceConfigValueTypedDict(TypedDict):
    option: SourceOptionValueTypedDict
    feed: FeedParserDict
    queries: List[ConfigQueryTypedDict]


SourceConfigDataType = Dict[str, SourceConfigValueTypedDict]
LinkHistoryDataType = Dict[str, int]
HistoryDataType = Dict[str, LinkHistoryDataType]
EntriesDataType = List[FeedParserDict]
MatchesDataType = List[EntriesDataType]
TitleEntriesDataType = Dict[str, EntriesDataType]
PageEntriesDataType = Dict[pywikibot.page.Page, EntriesDataType]
PageEntryGeneratorDataType = Generator[pywikibot.page.Page, None, None]

CONFIG_FILENAME: str = "config.json"
CONFIG_PAGE_TITLE: str = f"MediaWiki:Feed external links/{CONFIG_FILENAME}"

COMMAND_OPTION: CommandOptionTypedDict = {
    "config_type": ConfigType.FILE,
    "config_path": f"./{CONFIG_FILENAME}",
    "config_page_title": CONFIG_PAGE_TITLE,

    "max_add": 1,

    "group": 50
}


def fetch_json_file(path: str) -> Any:
    with open(path, encoding="utf8") as file:
        data = json.load(file)
        return data


def fetch_config_file(path: str) -> ConfigResultDataType:
    return fetch_json_file(path)


def fetch_history_file(path: str) -> HistoryDataType:
    return fetch_json_file(path)


def fetch_proxies_file(path: str) -> ProxiesDataType:
    return fetch_json_file(path)


def write_json_file(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf8") as file:
        json.dump(data, file, indent=4)


def write_history_file(path: str, history: HistoryDataType) -> None:
    write_json_file(path, history)


def fetch_config_wiki_page(title: str) -> ConfigResultDataType:
    site = pywikibot.Site()
    page = pywikibot.Page(site, title)

    if not page.exists():
        raise pywikibot.exceptions.NoPage(page)

    page_text = page.text

    try:
        config = json.loads(page_text)
        return config
    except json.decoder.JSONDecodeError as exception:
        pywikibot.error("Invalid JSON syntax:")
        pywikibot.output(page_text)
        pywikibot.output("")
        raise exception


def fetch_config(command_option: CommandOptionTypedDict) -> ConfigResultDataType:
    config_type: ConfigType = command_option["config_type"]
    if config_type == ConfigType.WIKI:
        config_page_title: str = command_option["config_page_title"]
        try:
            return fetch_config_wiki_page(config_page_title)
        except (pywikibot.exceptions.NoPage, json.decoder.JSONDecodeError) as exception:
            pywikibot.exception(exception, tb=True)
            pywikibot.output("")
            pywikibot.output("")

    config_path: str = command_option["config_path"]
    return fetch_config_file(config_path)


def parse_config(command_option: CommandOptionTypedDict) -> Tuple[ConfigsDataType, Set[str]]:
    configs: ConfigResultDataType = fetch_config(command_option)
    if isinstance(configs, dict):
        configs = [configs]
    elif not isinstance(configs, list):
        raise TypeError("`configs` must be a dict or list.")

    unique_sources: Set[str] = set()
    for config in configs:
        sources = config["sources"]
        unique_sources.update(sources)

    return configs, unique_sources


def get_source_options(command_option: CommandOptionTypedDict, sources: Iterable[str]) -> SourceOptionDataType:
    # Create proxy handlers.
    proxy_handler: Optional[ProxyHandler] = None
    proxies: Dict[str, str] = {}
    has_proxy: bool = False
    if "proxy" in command_option:
        proxy: str = command_option["proxy"]
        proxies["http"] = proxy
        proxies["https"] = proxy
        has_proxy = True

    if "http_proxy" in command_option:
        http_proxy: str = command_option["http_proxy"]
        proxies["http"] = http_proxy
        has_proxy = True

    if "https_proxy" in command_option:
        https_proxy: str = command_option["https_proxy"]
        proxies["https"] = https_proxy
        has_proxy = True

    if has_proxy:
        proxy_handler = ProxyHandler(proxies)

    regex_proxies: ProxiesDataType = {}
    if "proxies_path" in command_option:
        path: str = command_option["proxies_path"]
        regex_proxies = fetch_proxies_file(path)

    compiled_pattern_proxies: Dict[Pattern, ProxiesValueDataType] = {re.compile(regex): proxies_value for regex, proxies_value in regex_proxies.items()}

    source_option: SourceOptionDataType = {}
    for source in sources:
        option: SourceOptionValueTypedDict = {
            "proxies": proxies,
            "has_proxy": has_proxy,
            "handlers": proxy_handler
        }

        for compiled_pattern, proxies_value in compiled_pattern_proxies.items():
            result = compiled_pattern.search(source)
            if result is not None:
                p = (proxies_value if isinstance(proxies_value, dict) else {
                    "http": proxies_value,
                    "https": proxies_value
                })

                option["proxies"] = p
                option["has_proxy"] = True
                option["proxy_regex"] = compiled_pattern.pattern
                option["handlers"] = ProxyHandler(p)

        source_option[source] = option

    return source_option


def fetch_feeds(source_option: SourceOptionDataType) -> Dict[str, FeedParserDict]:
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(feedparser.parse, source, handlers=option["handlers"]): source for source, option in source_option.items()}
        feeds = {futures[future]: future.result() for future in concurrent.futures.as_completed(futures)}
        return feeds


def get_source_queries(configs: ConfigsDataType) -> Dict[str, List[ConfigQueryTypedDict]]:
    source_queries: Dict[str, List[ConfigQueryTypedDict]] = {}

    for config in configs:
        sources = config["sources"]
        queries = config["queries"]
        for source in sources:
            source_queries[source] = queries

    return source_queries


def get_source_config(command_option: CommandOptionTypedDict) -> SourceConfigDataType:
    configs, unique_sources = parse_config(command_option)
    source_option = get_source_options(command_option, unique_sources)
    source_feed = fetch_feeds(source_option)
    source_queries = get_source_queries(configs)

    source_config: SourceConfigDataType = {}
    for source in unique_sources:
        source_config[source] = {
            "option": source_option[source],
            "feed": source_feed[source],
            "queries": source_queries[source]
        }

    return source_config


keyword_compiled_pattern: Dict[str, Pattern] = {}


def execute_queries(text: str, queries: List[ConfigQueryTypedDict]) -> Tuple[List[QueryResultTypedDict], int, int]:
    query_results: List[QueryResultTypedDict] = []
    number_of_keyword_matches: int = 0
    number_of_regex_matches: int = 0
    for q, query in enumerate(queries):
        # Search by keywords.
        keyword_matches: List[Match] = []
        if "keywords" in query:
            keywords = query["keywords"]
            for keyword in keywords:
                compiled_pattern: Optional[Pattern] = None
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
        regex_matches: List[Match] = []
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
                        regex_flags = regex["flags"]
                        if isinstance(regex_flags, (str, int)):
                            regex_flags = [regex_flags]
                        elif not isinstance(regex_flags, list):
                            pywikibot.error(f"Flags \"{regex_flags}\" must be a list, string, or int.")
                            pywikibot.output("")
                            continue

                        f = 0
                        for regex_flag in regex_flags:
                            if isinstance(regex_flag, str):
                                f += getattr(re, regex_flag)
                            elif isinstance(regex_flag, int):
                                f += regex_flag
                            else:
                                pywikibot.error(f"Flag \"{regex_flag}\" must be a string or int.")
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

    return query_results, number_of_keyword_matches, number_of_regex_matches


def search_entries(feed: FeedParserDict, queries: List[ConfigQueryTypedDict], matches: MatchesDataType) -> Tuple[int, int]:
    total_keyword_matches: int = 0
    total_regex_matches: int = 0

    entries: EntriesDataType = feed.entries
    for entry in entries:
        title: str = entry.title

        query_results, number_of_keyword_matches, number_of_regex_matches = execute_queries(title, queries)
        total_keyword_matches += number_of_keyword_matches
        total_regex_matches += number_of_regex_matches
        for query_result in query_results:
            keyword_matches = query_result["keyword_matches"]
            regex_matches = query_result["regex_matches"]
            if len(keyword_matches) > 0 or len(regex_matches) > 0:
                q = query_result["q"]
                matches[q].append(entry)

    return total_keyword_matches, total_regex_matches


get_publish_date = attrgetter("published_parsed")


def process_matches(
    queries: List[ConfigQueryTypedDict],
    matches: MatchesDataType,
    history: HistoryDataType,
    max_add: int = 1
) -> TitleEntriesDataType:
    title_entries: TitleEntriesDataType = {}

    # Add all matches to a page title in `title_entries`.
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

        # History.
        link_history: LinkHistoryDataType = (history[title] if title in history else {})

        # Remove duplicates.
        unique_entries: EntriesDataType = []
        unique_titles: Set[str] = set()
        unique_links: Set[str] = set()
        for entry in entries:
            entry_link: str = entry.link
            if entry_link in link_history:
                number_of_times_added: int = link_history[entry_link]
                if number_of_times_added >= max_add:
                    pywikibot.warning("An entry for page \"{0}\" was discarded because its link \"{1}\" was added {2} {3} before.".format(
                        title,
                        entry_link,
                        number_of_times_added,
                        "time" + ("s" if number_of_times_added != 1 else "")
                    ))
                    pywikibot.output("")
                    continue

            if entry_link in unique_links:
                pywikibot.warning(f"An entry for page \"{title}\" was discarded because its link \"{entry_link}\" was a duplicate.")
                pywikibot.output("")
                continue

            entry_title: str = entry.title
            if title in unique_titles:
                pywikibot.warning(f"An entry for page \"{title}\" has the same title \"{entry_title}\" as another entry.")
                pywikibot.output("")

            unique_titles.add(entry_title)
            unique_links.add(entry_link)
            unique_entries.append(entry)

        title_entries[title] = unique_entries

    return title_entries


def get_title_entries(
    source_config: SourceConfigDataType,
    history: HistoryDataType,
    max_add: int = 1
) -> TitleEntriesDataType:
    title_entries: TitleEntriesDataType = {}

    for source, config in source_config.items():
        pywikibot.output(f"Parsing feed from source \"{source}\"...")

        option: SourceOptionValueTypedDict = config["option"]
        feed: FeedParserDict = config["feed"]
        queries: List[ConfigQueryTypedDict] = config["queries"]

        has_proxy: bool = option["has_proxy"]
        if has_proxy:
            proxies = option["proxies"]
            proxy_source = "command line"
            if "proxy_regex" in option:
                proxy_regex = option["proxy_regex"]
                proxy_source = f"matched regex pattern \"{proxy_regex}\""
            pywikibot.output(f"Using proxies \"{proxies}\" from {proxy_source}...")

        if "bozo_exception" in feed:
            if "status" in feed:
                status = feed["status"]
                href = feed["href"]
                pywikibot.error(f"Received HTTP status code {status} for \"{href}\".")

            pywikibot.exception(feed["bozo_exception"])
        else:
            matches: MatchesDataType = [[] for i in range(len(queries))]
            total_keyword_matches, total_regex_matches = search_entries(feed, queries, matches)
            te: TitleEntriesDataType = process_matches(queries, matches, history, max_add)
            for title, entries in te.items():
                if title not in title_entries:
                    title_entries[title] = []

                title_entries[title].extend(entries)

            pywikibot.output("Found {0} {1} and {2} {3}.".format(
                total_keyword_matches,
                "keyword match" + ("es" if total_keyword_matches != 1 else ""),
                total_regex_matches,
                "regex match" + ("es" if total_regex_matches != 1 else ""),
            ))

        pywikibot.output("Done.")
        pywikibot.output("")

    # Remove duplicates.
    for title, entries in title_entries.items():
        title_entries[title] = get_unique_entries(title, [], entries)

    return title_entries


def format_entry_to_link_markup(entry: FeedParserDict) -> str:
    title: str = entry.title
    link: str = entry.link
    external_link = ExternalLink(link, title)
    # return f"* [{link} {title}]"
    return f"* {external_link}"


def map_entries_to_list_markup(entries: EntriesDataType) -> Iterator[str]:
    return map(format_entry_to_link_markup, entries)


def format_entries_to_list_markup(entries: EntriesDataType) -> str:
    return "\n".join(map_entries_to_list_markup(entries))


def get_unique_entries(title: str, previous_external_links: List[ExternalLink], entries: EntriesDataType) -> EntriesDataType:
    """Merge entries by excluding duplicate links that already exist."""

    unique_entries: EntriesDataType = []
    unique_titles: Set[str] = set()
    unique_links: Set[str] = set()

    # Add titles and links from existing external links.
    for previous_external_link in previous_external_links:
        previous_title = str(previous_external_link.title)
        previous_link = str(previous_external_link.url)
        unique_titles.add(previous_title)
        unique_links.add(previous_link)

    # Check for titles and links that already exist, and remove duplicates.
    for entry in entries:
        entry_link: str = entry.link
        if entry_link in unique_links:
            pywikibot.warning(f"An entry for page \"{title}\" was discarded because its link \"{entry_link}\" was a duplicate.")
            pywikibot.output("")
            continue

        entry_title: str = entry.title
        if entry_title in unique_titles:
            pywikibot.warning(f"An entry for page \"{title}\" has the same title \"{entry_title}\" as another entry.")
            pywikibot.output("")

        unique_titles.add(entry_title)
        unique_links.add(entry_link)
        unique_entries.append(entry)

    return unique_entries


def log_external_links_added(number_of_external_links: int, title: str, text: str) -> None:
    if number_of_external_links > 0:
        pywikibot.output("Add {0} {1} to page \"{2}\":{3}".format(
            number_of_external_links,
            "external link" + ("s" if number_of_external_links != 1 else ""),
            title,
            text
        ))


def feed_external_links(page_title: str, page_text: str, entries: EntriesDataType) -> Tuple[str, int]:
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
        previous_external_links = []
        unique_entries = get_unique_entries(page_title, previous_external_links, entries)
        content = "\n" + format_entries_to_list_markup(unique_entries) + "\n\n"
        text = heading + content

        lines = wikicode.filter_text(recursive=False)
        if len(lines) > 0:
            last_line = lines[-1]
            wikicode.replace(last_line, last_line.rstrip() + text)
        else:
            wikicode.append(text)

        number_of_unique_entries = len(unique_entries)
        number_of_external_links_added += number_of_unique_entries
        log_external_links_added(number_of_unique_entries, page_title, content)

    revised_page_text = wikicode.rstrip()

    return revised_page_text, number_of_external_links_added


def output_separator(title: str, character: str, line_length: int = 80) -> str:
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


revised_page_text_separator: str = output_separator("Revised page text", "-")
save_result_separator: str = output_separator("Save result", "-")


def save_external_links(page: pywikibot.page.Page, title: str, entries: EntriesDataType) -> None:
    pywikibot.output(output_separator(f"Page \"{title}\"", "="))

    page_text = page.text

    revised_page_text, number_of_external_links_added = feed_external_links(title, page_text, entries)

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


def update_history(history: HistoryDataType, title: str, entries: EntriesDataType) -> None:
    link_history: Optional[LinkHistoryDataType] = None
    if title not in history:
        link_history = {entry.link: 1 for entry in entries}
        history[title] = link_history
    else:
        link_history = history[title]
        for entry in entries:
            entry_link: str = entry.link
            number_of_times_added: int = (link_history[entry_link] if entry_link in link_history else 0)
            link_history[entry_link] = (number_of_times_added + 1)


def PageEntryGenerator(
    site: Optional[pywikibot.site.APISite] = None,
    title_entries: Optional[TitleEntriesDataType] = None,
    page_entries: Optional[PageEntriesDataType] = None
) -> Generator[pywikibot.page.Page, None, None]:
    if page_entries is None:
        page_entries = {}

    if title_entries is None:
        for page, entries in page_entries.items():
            yield page
    else:
        if site is None:
            site = pywikibot.Site()

        for title, entries in title_entries.items():
            page = pywikibot.Page(site, title)
            page_entries[page] = entries
            yield page


class FeedExternalLinksBot(SingleSiteBot, NoRedirectPageBot):
    """Feed external links bot."""

    def __init__(
        self,
        site: pywikibot.site.APISite,
        generator: PageEntryGeneratorDataType,
        title_entries: TitleEntriesDataType,
        page_entries: PageEntriesDataType,
        history: HistoryDataType,
        **kwargs: BotOptionTypedDict
    ) -> None:
        """
        Initializer.
        :param site: The site.
        :param generator: The page generator that determines on which pages to work.
        :param title_entries: The `title_entries`.
        :param page_entries: The `page_entries`.
        :param history: The `history`.
        :param kwargs:
        """

        super().__init__(site=site, generator=generator, **kwargs)

        self.title_entries = title_entries
        self.page_entries = page_entries
        self.history = history

    def run(self) -> None:
        super().run()
        pywikibot.output("")

    def treat_page(self) -> None:
        page = self.current_page
        try:
            title = page.title()
            page_entries = self.page_entries
            entries = (page_entries[page] if page in page_entries else self.title_entries[title])
            save_external_links(page, title, entries)
            update_history(self.history, title, entries)
        except Exception as exception:
            pywikibot.exception(exception, tb=True)
            pywikibot.output("")


def main(*args: Tuple[Any, ...]) -> None:
    command_option: CommandOptionTypedDict = deepcopy(COMMAND_OPTION)
    bot_option: BotOptionTypedDict = {}

    history_path: str = ""
    has_history_path: bool = False

    local_args = pywikibot.handle_args(args)
    generator_factory = pagegenerators.GeneratorFactory()

    for arg in local_args:
        key, seperator, value = arg.partition(":")
        stripped_value = value.strip()
        if key == "-config-type":
            config_type = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter config type:").strip())
            command_option["config_type"] = ConfigType(config_type.lower())
        elif key == "-config-path":
            config_path = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter config file path:").strip())
            command_option["config_path"] = config_path
        elif key == "-config-page-title":
            config_page_title = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter config page title:").strip())
            command_option["config_page_title"] = config_page_title
        elif key == "-history-path":
            history_path = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter history file path:").strip())
            command_option["history_path"] = history_path
            has_history_path = True
        elif key == "-max-add":
            max_add = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter max add:").strip())
            command_option["max_add"] = int(max_add)
        elif key == "-group":
            group = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter group:").strip())
            command_option["group"] = int(group)
        elif key == "-proxy":
            proxy = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter proxy:").strip())
            command_option["proxy"] = proxy
        elif key == "-http-proxy":
            http_proxy = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter HTTP proxy:").strip())
            command_option["http_proxy"] = http_proxy
        elif key == "-https-proxy":
            https_proxy = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter HTTPS proxy:").strip())
            command_option["https_proxy"] = https_proxy
        elif key == "-proxies-path":
            proxies_path = (stripped_value if len(stripped_value) > 0 else pywikibot.input("Enter proxies file path:").strip())
            command_option["proxies_path"] = proxies_path
        else:
            generator_factory.handleArg(arg)

    source_config: SourceConfigDataType = get_source_config(command_option)

    history: HistoryDataType = (fetch_history_file(history_path) if has_history_path else {})

    title_entries: TitleEntriesDataType = get_title_entries(source_config, history, command_option["max_add"])
    page_entries: PageEntriesDataType = {}

    site = pywikibot.Site()
    generator = generator_factory.getCombinedGenerator(
        pagegenerators.PreloadingGenerator(
            PageEntryGenerator(site=site, title_entries=title_entries, page_entries=page_entries),
            groupsize=command_option["group"]
        )
    )
    if generator is None:
        pywikibot.bot.suggest_help(missing_generator=True)
        return

    bot = FeedExternalLinksBot(site, generator, title_entries, page_entries, history, **bot_option)  # type: ignore
    bot.run()

    is_simulation: bool = pywikibot.config.simulate
    if has_history_path and not is_simulation:
        write_history_file(history_path, history)


if __name__ == "__main__":
    main()