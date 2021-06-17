# Alexa App for AppDaemon

This AppDaemon app allows you to wire up custom alexa skills with your AppDaemon instance.

## How does it work?

When your custom alexa skill is invoked, Amazon sends an API request to the `alexa.py` app via the AppDaemon API. This script then inspects the request and tries to find the right intent-app to handle it. It passes on the request to the app which can then act on the data and provide an appropriate response back to Alexa. 

### What can I do with it?

You can do those things that are outside or beyond the default Alexa home automation commands or things like `haaska`. If you are familiar with [ReneTode's Alexa-AppDaemon-App](https://github.com/ReneTode/Alexa-AppDaemon-App), this thing pretty much does the same with a few differences or improvements. 

You can for example:
- "Alexa, tell the vacuum to clean the kitchen"
- "Alexa, tell the TV to switch to xyz"
- Register fast voice command like "Alexa, code red!"
- ...or whatever you can express in an Alexa skill with intents and with some python magic in AppDaemon

### How do I use it?

Since `alexa.py` is just another AppDaemon app, you can simply put it in your AppDaemon apps folder alongside a `alexa.yaml` for configuration.

**Note** `alexa.py` (and maybe some intent apps) make use of a method in `helpers.py`. So make sure this one is found, either by placing it alongside the apps, or registering it once as "global" in AppDaemons `apps.yaml` like so:

```yaml
global_modules:
  - helpers
```

The intents you are handling in the end are also AppDaemon apps, so it does not matter where they are as long as AppDaemon is able to find them. For example, my app structure looks like this:

```
appdaemon/apps/apps.yaml
appdaemon/apps/helpers.py
appdaemon/apps/alexa/alexa.py
appdaemon/apps/alexa/alexa.yaml
appdaemon/apps/alexa/tvIntent/tvIntent.py
appdaemon/apps/alexa/tvIntent/tvIntent.yaml
appdaemon/apps/alexa/vacuumIntent/vacuumIntent.py
appdaemon/apps/alexa/vacuumIntent/vacuumIntent.yaml
...
```

As far as the Alexa custom skill configuration is concerned, follow [Rene's guide](https://github.com/ReneTode/Alexa-AppDaemon-App/blob/master/alexa%20skill%20tutorial.md) -- Even though some things have changed since this document was written, it roughly is still valid and you should be able to get started.

**Note** You might have to create multiple skills, i.e. one skill that activates with the keywords "the tv", one that uses "the vacuum" as activation name etc. in order to have more natural language conversations with Alexa (as opposed to "Alexa, tell AppDaemon...")

All intents of all custom skills are handled within the same `alexa.py` instance without any distinction which skill it is invoked from, the intent name is the one that counts. That means that the AppDaemon-Intent-App that will handle your request should have the same name as the intent, i.e. `tvIntent` in Alexa and `tvIntent` as the name of the AppDaemon app.

**Note** You might also want to create a yesIntent (or use the AMAZON.YesIntent) in your custom skills that responds to "yes", "ok", etc. for better experience when being asked "is there anything else I could do?". 


### How do I write my own intent apps?

Take a look at the `exampleIntent` which provides a simple skeleton for you to get started. All intentApps are also AppDaemon apps and thus can implement `initialize(self)` method to initialize config values from the accompanying yaml file. Behaviour of the dialog (what will be said by alexa, cards, reprompts, directives and whether the session should end) is controlled via return values in the methods you implement:

*Return value and parameters are documented further below*

- `intentCompleted(self, request)` *mandatory*: This method gets invoked when Alexa has completely resolved you intent, i.e. when all slots are filled properly according to your definition. For simple apps, this is probably the only method you implement

- `intentStarted(self, request)` *optional*: This method gets called when the user has invoked a new dialog and slots still need be filled. If no slots were to be filled, the dialog would be completed. This allows you to control your dialog with for example custom speech prompts, or to tell Alexa to delegate to a different intent. Note that you might have to disable auto delegate for your intent in order for your skill to receive an `IntentRequest` for each turn of the dialog. The default behavior, if this method is not provided, is to delegate the dialog back to Alexa, which results in Alexa asking the user automatically for the slot prompts.

- `intentInProgress(self, request)` *optional*: This method will be called when a dialog is already in progress and there are still slots to be filled. See `intentStarted`

- `canFulfill(self, request)` *optional*: This method gets invoked when Alexa is querying skills to determine whether the skill can understand and fulfill the intent request with detected slots, before actually asking the skill to take action. Note that according to Alexa docs, you should not actually perform any actions on `canFulfillIntentRequest`s.

- `launchRequest(self, request)` *optional*: This method gets called when your skill is invoked by a user without an intent. This allows you to trigger fast commands like "Alexa, code red!" by creating a custom skill with "code red" as invocation name and no intents. Since no intent is required for this to work, you need to configure `launchRequestApp` in `alexa.yaml` with the name of the AppDaemon app that should receive this call


All methods above get passed a `request` object that is a pre-processed object of what Alexa sends to AppDaemon. The object has the following properties (you'll probably only need the device and the slots from it):

```python
{
  'type': '...',
  'intent': '...',
  'confirmation_status': '...',
  'dialog_state': '...',
  'device': '...',  # The device the intent is called
                    # from. This is the human readable
                    # translation from the alexa.yaml
                    #configuration. Device IDs are logged
  'slots': {
    # Slot dictionary, with key being the slot name and
    # value being a dictionary with:
    # {
    #  'value': 'slot value',
    #  'resolutions': [{slot resolution objects}]
    # }
  },
  'error': '...'
}
```

Behavior of the intent dialog is controlled by the return values of the methods you implement. The return value is ultimately what is sent back to Alexa in response to the different request. Since the one of the goals is to make it as easy as possible while still having maximum flexibility in your intent apps, you have **five different return value options**:

1. *A plain string*: A simple string as return value will be treated as spoken text.

2. *A dictionary*: A returned dictionary in whose keys should correspond to the entries in the `response` property of the response dictionary (`outputSpeech`, `card`, `reprompt`, `directives`, `shouldEndSession`). Values of the keys will be copied over to the response dict (the dict in `AlexaAPI.create_response_dict`). See Alexa documentation for your options here

3. *A tuple of (Dict, int)*: In this case the `dict` is treated as a complete response and the `int` as the return code. No modification of the response dict occurs. The dict is returned to Alexa **as is**, so make sure you return a valid structure from your app

4. *A tuple of (str, Dict)*: The `str` is treated as the text to speak and the `dict` provides possible overrides to the keys in the `response` dictionary of the response JSON.

5. *A tuple of (str, str)*: The first `str` is treated as the text to speak and the second one can be any of `['stop', 'next']`. In case of `stop` a random `intentEnd` phrase is appended to the text and the intent ends. For `next` a random `nextConversationQuestion` is appended and the dialog continues. If the second `str` is not given or not one of the options given options, it is effectively the same as (1), and the text is spoken

Option (5) and (1) are probably the most used ones as your intent just confirms the action, says goodbye or similar. Option (5) is an easy shortcut to be able to end after you're done, or conveniently ask the user if there is something else to help with.

For more detailed information about the requests and valid response values see the [Request Type Reference](https://developer.amazon.com/en-US/docs/alexa/custom-skills/request-types-reference.html)
