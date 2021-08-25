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

"""
from typing import Optional, Dict, List
import appdaemon.plugins.hass.hassapi as hassapi
import helpers


class AlexaAPI(hassapi.Hass):
    """AlexaAPI"""
    def initialize(self):
        """App init"""
        self.register_endpoint(self.api_call, 'alexa')
        self.sessions: Dict[str, Dict] = {}

    def api_call(self, data, kwargs):
        """Entrypoint of REST call"""
        self.log('New Alexa API request')
        session_id = data.get('session', {}).get('sessionId', None)
        # Note that the session object is missing in AudioPlayer,
        # VideoApp, or PlaybackController requests
        if not session_id:
            self.log('Request is missing session.sessionId!')
            return {}, 400

        # Record the request
        request_data = self.get_request_data_from_json(data)
        if session_id not in self.sessions:
            self.log('New session: %s' % session_id)
            self.sessions[session_id] = {'requests': list()}
        self.sessions[session_id]['requests'].append(request_data)

        # Handle request
        return self.handle_request(session_id)

    def get_request_data_from_json(self, data):
        """Extract the info we need from the data dict. Returns new dict with
        our desired fields

        """
        # Any error?
        error = data.get('request', {}).get('error', {}).get('message', '')

        # Get a proper device name
        device_id = data.get('context',
                             {}).get('System',
                                     {}).get('device',
                                             {}).get('deviceId',
                                                     '<no_device_id>')
        device = self.args.get('devices', {}).get(device_id, 'unknown device')
        # Log the device if not yet known
        if device_id not in self.args.get('devices', {}):
            self.log('Request from device: %s' % device_id)

        # The slots for this intent
        slots = {}
        for slot_value in data.get('request', {}).get('intent',
                                                      {}).get('slots',
                                                              {}).values():
            slots[slot_value.get('name')] = {
                'value': slot_value.get('value'),
                'resolutions': []
            }
            # Add the 'resolutions' flattened. Let's hope thats enough
            for resolution in slot_value.get('resolutions',
                                             {}).get('resolutionsPerAuthority',
                                                     []):
                if resolution.get('status', {}).get('code',
                                                    '') != 'ER_SUCCESS_MATCH':
                    continue
                for rpa_value in resolution.get('values', []):
                    slots[slot_value.get('name')]['resolutions'].append({
                        'id':
                        rpa_value.get('value', {}).get('id', ''),
                        'name':
                        rpa_value.get('value', {}).get('name', '')
                    })

        # The intent name. Note some amazon intents are named like AMAZON.Intent
        intent = data.get('request', {}).get('intent', {}).get('name', '')
        confirmation_status = data.get('request',
                                       {}).get('intent',
                                               {}).get('confirmationStatus',
                                                       'NONE')
        return {
            'type': data.get('request', {}).get('type', ''),
            'intent': intent,
            'confirmation_status': confirmation_status,
            'dialog_state': data.get('request', {}).get('dialogState', ''),
            'device': device,
            'slots': slots,
            'error': error
        }

    # pylint: disable=too-many-return-statements,too-many-branches
    def handle_request(self, session_id):
        """Handle latest request for `session_id`"""
        # Get the latest request in the session
        request = self.sessions[session_id]['requests'][-1]

        # There are 4 different standard request types we handle
        if request['type'] == 'LaunchRequest':
            self.log('LaunchRequest')
            # Sent when the user invokes your skill without providing
            # a specific intent.
            #
            # https://developer.amazon.com/en-US/docs/alexa/custom-skills/request-types-reference.html#launchrequest
            return self.get_app_response(self.args.get('launchRequestApp', ''),
                                         'launchRequest', session_id)

        if request['type'] == 'IntentRequest':
            self.log('IntentRequest: %s' % request['intent'])
            # Sent when the user makes a request that corresponds to
            # one of the intents defined in your intent schema.
            #
            # https://developer.amazon.com/en-US/docs/alexa/custom-skills/request-types-reference.html#intentrequest
            if not request['dialog_state']:
                self.log(
                    'Dialog not yet started (or intent has no dialog model, i.e. no multi-turn dialog)'
                )
                # TODO: Not sure how this works. Do we delegate this
                # request to a method in the intent app?
                return self.create_response_dict(shouldEndSession=True), 200
            if request['dialog_state'] == 'STARTED':
                self.log('Dialog started')
                # Dialog started, let's give the app a chance to respond, or we delegate back to Alexa
                try:
                    return self.get_app_response(request['intent'],
                                                 'intentStarted',
                                                 session_id,
                                                 error_exception=True)
                except Exception:  # pylint: disable=broad-except
                    self.log(
                        'Failed to ask %s for %s. Delegating dialog to Alexa' %
                        (request['intent'], 'intentStarted'))
                return self.create_response_dict(
                    directives=[{
                        'type': 'Dialog.Delegate',
                        'updatedIntent': None
                    }]), 200
            if request['dialog_state'] == 'IN_PROGRESS':
                self.log('Dialog in progress')
                # Dialog started, let's give the app a chance to respond, or we delegate back to Alexa
                try:
                    return self.get_app_response(request['intent'],
                                                 'intentInProgress',
                                                 session_id,
                                                 error_exception=True)
                except Exception:  # pylint: disable=broad-except
                    self.log(
                        'Failed to ask %s for %s: Delegating dialog to Alexa' %
                        (request['intent'], 'intentInProgress'))
                return self.create_response_dict(
                    directives=[{
                        'type': 'Dialog.Delegate',
                        'updatedIntent': None
                    }]), 200
            if request['dialog_state'] == 'COMPLETED':
                self.log('Dialog completed')
                # COMPLETED can either be because the dialog is really
                # completed in which case we dispatch to the app, or
                # there are dialog confirmation rules in which case
                # dialogState is COMPLETED regardless of whether the
                # user confirmed or denied the entire intent. So we
                # check that the user did not deny the confirmation
                if request['confirmation_status'] == 'DENIED':
                    self.log('User denied the intent. Aborting session')
                    self.clean_session(session_id)
                    return self.create_response_dict(
                        shouldEndSession=True), 200
                self.log('Calling user intent app %s' % request['intent'])
                return self.get_app_response(request['intent'],
                                             'intentCompleted', session_id)

            self.log('Dialog state is %s - this should not happen!' %
                     request['dialog_state'])
            return self.create_response_dict(), 200

        if request['type'] == 'SessionEndedRequest':
            self.log('SessionEndedRequest')
            # Sent when the current skill session ends for any reason
            # other than your code closing the session.
            #
            # https://developer.amazon.com/en-US/docs/alexa/custom-skills/request-types-reference.html#sessionendedrequest
            self.log('Alexa says session %s has ended: %s' %
                     (session_id, request['error']))
            self.clean_session(session_id)
            return self.create_response_dict(), 200

        if request['type'] == 'CanFulfillIntentRequest':
            self.log('CanFulfillIntentRequest')
            # Sent when the Alexa service is querying a skill to
            # determine whether the skill can understand and fulfill
            # the intent request with detected slots, before actually
            # asking the skill to take action.
            #
            # https://developer.amazon.com/en-US/docs/alexa/custom-skills/request-types-reference.html#CanFulfillIntentRequest
            try:
                return self.get_app_response(request['intent'],
                                             'canFulfill',
                                             session_id,
                                             error_exception=True)
            except Exception:  # pylint: disable=broad-except
                self.log(
                    'Failed to ask %s for %s: Delegating dialog to Alexa' %
                    (request['intent'], 'intentInProgress'))
            return self.create_response_dict(), 200

        # TODO: Non-standard request type or other interface request
        # need to be implemented
        self.log('Non-standard request we cannot handle yet')
        self.clean_session(session_id)
        return self.plain_error(request)

    # pylint: disable=too-many-arguments,no-self-use,invalid-name
    def create_response_dict(self,
                             outputSpeech: Optional[Dict] = None,
                             card: Optional[Dict] = None,
                             reprompt: Optional[Dict] = None,
                             directives: Optional[List] = None,
                             shouldEndSession: bool = False):
        """Returns a skeleton of the response structure"""
        response = {
            'version': '1.0',
            'sessionAttributes': {},
            'response': {
                'outputSpeech': outputSpeech or {},
                'card': card or {},
                'reprompt': reprompt or {},
                'directives': directives or [],
                'shouldEndSession': shouldEndSession
            }
        }
        # Clean empty properties from the object (would trigger error with Alexa)
        for prop in ['outputSpeech', 'card', 'reprompt', 'directives']:
            if not response['response'][prop]:
                del response['response'][prop]
        return response

    def get_simple_outputSpeech(self, text, request):
        """Returns a outputSpeech structure for the response filled with a
        simple <speak>text</speak>

        """
        return {
            'type': 'SSML',
            'ssml': '<speak>' + self.prepare_speech(text, request) + '</speak>'
        }

    # pylint: disable=no-self-use
    def prepare_speech(self, text, request):
        """Prepares speech text by cleaning up and replacing slots"""
        if not text:
            return text
        for slotname, slotvalue in request['slots'].items():
            text = text.replace("{{" + slotname + "}}",
                                slotvalue.get('value', '') or '')
        return text.replace("{{device}}",
                            request['device']).replace("_", " ").replace(
                                "...", "<break time='2s'/>")

    def get_app_response(self,
                         app_name,
                         method,
                         session_id,
                         error_exception=False):
        """Asks an app `app_name` for a response by calling `method(request`
        to it. `error_exception` raises an exception instead or returning an
        Alexa compatible error response

        """
        request = self.sessions[session_id]['requests'][-1]
        app = self.get_app(app_name)
        if not app:
            # If the app was not found, we implement a better response
            # for some default/common intent requests. This allows for
            # better expected behaviour while the user can still
            # override by creating an intent app for it
            if app_name in ['AMAZON.StopIntent', 'AMAZON.CancelIntent']:
                self.clean_session(session_id)
                return self.create_response_dict(
                    outputSpeech=self.get_simple_outputSpeech(
                        helpers.random_pick(
                            self.args.get('conversationEnd', 'Bye')), request),
                    shouldEndSession=True), 200
            if app_name in ['yesIntent', 'AMAZON.YesIntento']:
                # If configured and not overridden, we assume user
                # responded 'yes' to a question 'nextConversationQuestion'
                return self.create_response_dict(
                    outputSpeech=self.get_simple_outputSpeech(
                        helpers.random_pick(
                            self.args.get('conversationQuestion',
                                          'What can I do?')), request),
                    shouldEndSession=False), 200
            self.log('App not found: %s' % app_name)
            if error_exception:
                raise Exception('App not found: %s' % app_name)
            return self.plain_error(request)

        if not (hasattr(app, method) and callable(getattr(app, method))):
            self.log(
                'Requested property %s of app %s is not callable or does not exist!'
                % (method, app_name))
            if error_exception:
                raise Exception(
                    'Requested property %s of app %s is not callable or does not exist!'
                    % (method, app_name))
            return self.plain_error(request)

        try:
            app_response = getattr(app, method)(request)
        except Exception as err:  # pylint: disable=broad-except
            self.log('ERROR: Exception calling intent app %s: %s' %
                     (app_name, str(err)))
            if error_exception:
                raise err
            return self.plain_error(request)

        # For the app response we accept 5 variants, depending on
        # whether or not the app needs a custom response:
        #
        # 1. A plain string:
        #    We treat it as the text to speak
        #
        # 2. A dictionary:
        #    The keys should correspond to the entries in the
        #    'response' property of the response dictionary. Values of
        #    the keys will be copied over to the response dict (the
        #    dict in `AlexaAPI.create_response_dict`)
        #
        # 3. A tuple of (Dict, int)
        #    In this case the dict is treated as a complete response
        #    and the int as the return code. No modification occurs,
        #    dict is returned to Amazon **as is** So make sure you
        #    return a valid structure in your app
        #
        # 4. A tuple of (str, Dict)
        #    str is treated text to speak and the Dict provides
        #    possible overrides to the keys in the 'response' property
        #    of the response json
        #
        # 5. A tuple of (str, str)
        #    The first str is treated text to speak and the second one
        #    can be any of ['stop', 'next']. In case of 'stop' a
        #    random intentEnd phrase is appended to the text and the
        #    intent ends. For 'next' a random nextConversationQuestion
        #    is appended and the dialog continues. If the second str
        #    is not given or not one of the options given options, it
        #    is effectively the same as 1 (the text is spoken)

        if isinstance(app_response, tuple):
            if len(app_response) == 2:
                value1, value2 = app_response
                if isinstance(value1, dict) and isinstance(value2, int):
                    # Variant 3
                    return value1, value2
                if isinstance(value1, str) and isinstance(value2, dict):
                    # Variant 4
                    return self.create_response_dict(
                        outputSpeech=self.get_simple_outputSpeech(
                            value1, request),
                        card=value2.get('card', {}),
                        reprompt=value2.get('reprompt', {}),
                        directives=value2.get('directives', []),
                        shouldEndSession=value2.get('shouldEndSession',
                                                    False)), 200
                if isinstance(value1, str) and isinstance(value2, str):
                    # Variant 5
                    if value2 == 'stop':
                        message = helpers.random_pick(
                            self.args.get('conversationEnd', 'Bye'))
                        if value1:
                            message = value1 + '. ' + message
                        return self.create_response_dict(
                            outputSpeech=self.get_simple_outputSpeech(
                                message, request),
                            shouldEndSession=True), 200
                    if value2 == 'next':
                        message = helpers.random_pick(
                            self.args.get('nextConversationQuestion',
                                          'What else can I do?'))
                        if value1:
                            message = value1 + '. ' + message
                        return self.create_response_dict(
                            outputSpeech=self.get_simple_outputSpeech(
                                message, request),
                            shouldEndSession=False), 200

                    # Fallback to variant 1
                    return self.create_response_dict(
                        outputSpeech=self.get_simple_outputSpeech(
                            value1, request)), 200

                self.log('App %s returned tuple of unknown type combination' %
                         app_name)
                if error_exception:
                    raise Exception(
                        'App %s returned tuple of unknown type combination' %
                        app_name)
                return self.plain_error(request)

            self.log('App %s returned too many values in tuple' % app_name)
            if error_exception:
                raise Exception('App %s returned too many values in tuple' %
                                app_name)
            return self.plain_error(request)

        if isinstance(app_response, str):
            # Variant 1
            return self.create_response_dict(
                outputSpeech=self.get_simple_outputSpeech(
                    app_response, request)), 200

        if isinstance(app_response, dict):
            # Variant 2
            return self.create_response_dict(
                outputSpeech=app_response.get('outputSpeech', {}),
                card=app_response.get('card', {}),
                reprompt=app_response.get('reprompt', {}),
                directives=app_response.get('directives', []),
                shouldEndSession=app_response.get('shouldEndSession',
                                                  False)), 200

        # If we get here, we have unknown return value(s) from the app
        self.log('App %s returned unknown value(s)' % app_name)
        if error_exception:
            raise Exception('App %s returned unknown value(s)' % app_name)
        return self.plain_error(request)

    def plain_error(self, request, message=None):
        """Shorthand for returning a plain error message"""
        error_msg = message or helpers.random_pick(
            self.args.get("responseError", ['Error']))
        return self.create_response_dict(
            outputSpeech=self.get_simple_outputSpeech(error_msg, request),
            shouldEndSession=True), 200

    def clean_session(self, session_id):
        """Removes a session from the internal state"""
        if session_id in self.sessions:
            self.log('Cleaning up session %s' % session_id)
            del self.sessions[session_id]
            return True
        return False
