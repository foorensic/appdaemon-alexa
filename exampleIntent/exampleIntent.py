#!/usr/bin/env python
"""alexa.py -- Alexa App for Appdaemon
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

Example intent for handling request to an "exampleIntent"

"""
import appdaemon.plugins.hass.hassapi as hass
import helpers


class exampleIntent(hass.Hass):
    """exampleIntent Appdaemon App"""

    def initialize(self):
        """Initializes the AppDaemon App"""
        self.device_entity = self.args.get('example_device', '')
        if not self.device_entity:
            self.log('ERROR: "example_device" not configured!')

    def intentCompleted(self, request):
        """This method is called when an intent is COMPLETED"""
        if not self.device_entity:
            return '', 'stop'

        # If your slots are not validated against the ones defined, we
        # could for example check the slot resolutions we configured
        # in the custom skill intent
        resolutions = request.get('slots', {}).get('some_slot',
                                                   {}).get('resolutions', [])

        # Just in case we don't have a resolution. Should usually not
        # happen. Depends on your slot config
        if not resolutions:
            return "I'm sorry, I couldn't find that blahblah"

        slot_value = resolutions[0].get('name')
        self.log('About to do something with "%s" and "%s"' %
                 (self.tv_entity, slot_value))
        # TODO: do something useful

        return helpers.random_pick([
            '<say-as>Okay</say-as>', '<say-as>Okidoki</say-as>',
            '<say-as>Alright</say-as>'
        ]), 'next'
