# feed_external_links.py

This Pywikibot script searches a list of web feeds, finds entries matched by keywords or regexes, and adds the links to the "External links" section of specified wiki pages.

## Requirements

* [Python 3+](https://www.python.org/downloads/)
* [Pywikibot 3+](https://www.mediawiki.org/wiki/Manual:Pywikibot/Installation#Install_Pywikibot)

## Installation

```
pip install feedparser
```

## Usage

```
python pwb.py feed_external_links/feed_external_links.py -help

feed_external_links.py

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

-group:n                How many pages to preload at once.

-proxy:x                Specify the same proxy as both HTTP and HTTPS for
                        all sources.

-http-proxy:x           Specify an HTTP proxy for all sources.

-https-proxy:x          Specify an HTTPS proxy for all sources.

-proxies-path:x         File path of the proxies file.


GLOBAL OPTIONS
==============
(Global arguments available for all bots)

-dir:PATH         Read the bot's configuration data from directory given by
                  PATH, instead of from the default directory.

-lang:xx          Set the language of the wiki you want to work on, overriding
                  the configuration in user-config.py. xx should be the
                  language code.

-family:xyz       Set the family of the wiki you want to work on, e.g.
                  wikipedia, wiktionary, wikitravel, ...
                  This will override the configuration in user-config.py.

-user:xyz         Log in as user 'xyz' instead of the default username.

-daemonize:xyz    Immediately return control to the terminal and redirect
                  stdout and stderr to file xyz.
                  (only use for bots that require no input from stdin).

-help             Show this help text.

-log              Enable the log file, using the default filename
                  'feed_external_links-bot.log'
                  Logs will be stored in the logs subdirectory.

-log:xyz          Enable the log file, using 'xyz' as the filename.

-nolog            Disable the log file (if it is enabled by default).

-maxlag           Sets a new maxlag parameter to a number of seconds. Defer bot
                  edits during periods of database server lag. Default is set
                  by config.py

-putthrottle:n    Set the minimum time (in seconds) the bot will wait between
-pt:n             saving pages.
-put_throttle:n

-debug:item       Enable the log file and include extensive debugging data
-debug            for component "item" (for all components if the second form
                  is used).

-verbose          Have the bot provide additional console output that may be
-v                useful in debugging.

-cosmeticchanges  Toggles the cosmetic_changes setting made in config.py or
-cc               user-config.py to its inverse and overrules it. All other
                  settings and restrictions are untouched.

-simulate         Disables writing to the server. Useful for testing and
                  debugging of new code (if given, doesn't do any real
                  changes, but only shows what would have been changed).

-<config var>:n   You may use all given numeric config variables as option and
                  modify it with command line.
```

Default values can be modified by editing the `COMMAND_OPTION` dictionary.

See also the wiki page on global options:

[https://www.mediawiki.org/wiki/Manual:Pywikibot/Global_Options](https://www.mediawiki.org/wiki/Manual:Pywikibot/Global_Options)

### Examples

Local config file with a custom path:
```
python pwb.py feed_external_links/feed_external_links.py "-config-path:./scripts/userscripts/feed_external_links/config.json"
```

Remote config file on a wiki page:
```
python pwb.py feed_external_links/feed_external_links.py -config-type:wiki "-config-page-title:MediaWiki:Feed external links/config.json"
```

Specifying proxies from the command line:
```
python pwb.py feed_external_links/feed_external_links.py "-proxy:http://localhost:8888/"
python pwb.py feed_external_links/feed_external_links.py "-http-proxy:http://localhost:8888/" "-https-proxy:https://localhost:8888/"
```

Specifying proxies from the proxies file:
```
python pwb.py feed_external_links/feed_external_links.py "-proxies-path:./scripts/userscripts/feed_external_links/proxies.json"
```

## Put throttle adjustment

The put throttle is managed by Pywikibot. A minimum value in seconds can be specified to override and increase the speed of the page edits. However, if the server becomes overloaded or the bot account becomes rate limited, Pywikibot automatically adjusts the put throttle by increasing it and then decreasing it when server the allows it.

A custom put throttle of 1 second can be added as a command-line argument:
```
python pwb.py feed_external_links/feed_external_links.py -put_throttle:1
```

A default put throttle can be specified in the "user-config.py" file. See the section starting on line 173:

[https://github.com/PowerpediaInterns/mediawiki-bots/blob/master/pywikibot/user-config.py#L173](https://github.com/PowerpediaInterns/mediawiki-bots/blob/master/pywikibot/user-config.py#L173)

## Config file

The script uses a config file, named "config.json" by default, stored in the JSON format. It will use the file locally in the current working directory.

The command-line arguments `-config-type:wiki` and `-config-page-title:x` can be used to specify a config file hosted on the wiki. On the wiki, a page titled "MediaWiki:Feed external links/config.json" can be created. By placing the config file on the wiki, the config file can be shared and updated, and the bot can be controlled by it.

### Example

```json
{
    "sources": [
        "C:\\Users\\User\\PycharmProjects\\mediawiki-bots\\pywikibot\\scripts\\userscripts\\feed_external_links\\2206921.xml",
        "http://domain.tld/rss.xml",
        "..."
    ],
    "queries": [
        {
            "pages": ["Test", "Nuclear", "Nuke"],
            "keywords": ["Nuclear"],
            "regexes": []
        },
        {
            "pages": ["Test", "STEM", "Science, Technology, Engineering, Mathematics"],
            "keywords": ["STEM"],
            "regexes": []
        },
        {
            "pages": ["Test"],
            "keywords": ["TestTestTestTestTest"],
            "regexes": [
                "Washington",
                {"pattern": "Savannah"},
                {"pattern": "graduate", "flags": ["IGNORECASE", "DOTALL"]}
            ]
        }
    ]
}
```

The "sources" array contains a list of paths to web feeds or the web feeds themselves. They can consist of web addresses, local paths, or an RSS XML string, for example.

The "queries" array contains a list of objects containing what "keywords" and "regexes" are used to match entries from web feeds. The links are added to each page in the list of "pages".

In this example, the "Test" page appears in all 3 queries. The keywords "Nuclear", "STEM", and "TestTestTestTestTest", along with the regexes, are used to match entries and add links to the "Test" page.

The regex can be a pattern string or an object containing a "pattern" string and/or a "flags" array. The flags are described in the [Python documentation](https://docs.python.org/3/library/re.html#re.A).

Keywords are matched case insensitively surrounded by word boundaries. This means that "Nuclear" will match "nuclear" but not "nuclearization".

If case sensitivity and/or word boundaries are desired, a regex can be used instead. For example, "Washington" will match "Washington", "non-Washington", and "Washington's" but not "washington".

## Proxies file

The script may use an additional file, named "proxies.json" by default, stored in the JSON format. The file path must be supplied using the command-line argument `-proxies-path:x`.

The advantage of using the proxies file over the command-line arguments is that different proxies can be specified for different sources.

### Example
```json
{
    ".*": "http://localhost:8888/",
    "^https?://localhost/": "http://localhost:8888/",
    "^https?://10\\.0\\.0\\.[0-9]+/": {
        "http": "http://10.0.0.118/",
        "https": "https://10.0.0.118/"
    },
    "^https?://(www\\.)?domain.tld/": {
        "http": "http://domain.tld:8888/"
    }
}
```

The key is a regex pattern. The value can be either a proxy string or an object that contains keys as proxy schemes and values as proxy strings.

In the first key-value pair, the regex pattern ".*" matches all sources and specifies a "http://localhost:8888/" proxy for all of them.

In the second key-value pair, the regex pattern "^https?://localhost/" matches all sources starting with "http://localhost/" or "https://localhost/" and specifies a "http://localhost:8888/" proxy for all of them.