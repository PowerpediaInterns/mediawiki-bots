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

from pywikibot import family

"""Meza family."""
class Family(family.Family):
    name = "meza"
    langs = {
        "en": None
    }

    def hostname(self, code):
        return "192.168.56.56"

    def scriptpath(self, code):
        return "/demo"

    def protocol(self, code):
        return "HTTPS"

    def ignore_certificate_error(self, code):
        return True