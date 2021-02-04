#!/usr/bin/env python
"""helpers.py -- Part of Alexa App for Appdaemon
Copyright (C) 2021 foorensic

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

https://github.com/foorensic/appdaemon-alexa

"""
import random


def random_pick(entries):
    """Pick a random entry from a given list of `entries`

    """
    if isinstance(entries, list):
        return random.choice(entries)
    return entries
