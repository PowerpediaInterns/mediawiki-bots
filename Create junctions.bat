@echo on

cd "C:\Users\User\pywikibot\scripts'
ren "userscripts" "userscripts.bak"
mklink /j userscripts "C:\Users\User\PycharmProjects\mediawiki-bots\pywikibot\scripts\userscripts"

cd "C:\Users\User\PycharmProjects\mediawiki-bots\venv\Lib\site-packages"
mklink /j mwparserfromhell "C:\Users\User\pywikibot\mwparserfromhell"
mklink /j pywikibot "C:\Users\User\pywikibot\pywikibot"