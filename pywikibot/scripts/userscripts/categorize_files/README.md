# categorize_files.py

This Pywikibot script categorizes uncategorized files on the wiki based on the file's MIME type or extension.

## Requirements

* [Python 3+](https://www.python.org/downloads/)
* [Pywikibot 3+](https://www.mediawiki.org/wiki/Manual:Pywikibot/Installation#Install_Pywikibot)

## Installation

No other modules to install.

## Usage

```
python pwb.py categorize_files/categorize_files.py -help

categorize_files.py

This Pywikibot script categorizes uncategorized files on the wiki based on the
file's MIME type or extension.

SCRIPT OPTIONS
==============
(Script arguments available for this bot)

-total:n          Maximum number of pages to retrieve in total.

-group:n          How many pages to preload at once.


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
                  'categorize_files-bot.log'
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

See also the wiki page on global options:

[https://www.mediawiki.org/wiki/Manual:Pywikibot/Global_Options](https://www.mediawiki.org/wiki/Manual:Pywikibot/Global_Options)

## Put throttle adjustment

The put throttle is managed by Pywikibot. A minimum value in seconds can be specified to override and increase the speed of the page edits. However, if the server becomes overloaded or the bot account becomes rate limited, Pywikibot automatically adjusts the put throttle by increasing it and then decreasing it when server the allows it.

A custom put throttle of 1 second can be added as a command-line argument:
```
python pwb.py categorize_files/categorize_files.py -put_throttle:1
```

A default put throttle can be specified in the "user-config.py" file. See the section starting on line 173:

[https://github.com/PowerpediaInterns/mediawiki-bots/blob/master/pywikibot/user-config.py#L173](https://github.com/PowerpediaInterns/mediawiki-bots/blob/master/pywikibot/user-config.py#L173)