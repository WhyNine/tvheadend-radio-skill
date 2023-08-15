# Copyright Simon Waller
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from mycroft.util.log import getLogger
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.skills.audioservice import AudioService
from mycroft.util.parse import match_one
from mycroft.messagebus.message import Message
import re
import requests
import datetime

LOGGER = getLogger(__name__)

class TVHeadendRadio(CommonPlaySkill):
    # Get the correct localised regex
    def translate_regex(self, regex):
        if regex not in self.regexes:
            path = self.find_resource(regex + '.regex')
            if path:
                with open(path) as f:
                    string = f.read().strip()
                self.regexes[regex] = string
        return self.regexes[regex]

    def CPS_match_query_phrase(self, phrase):
        if len(self.channels) == 0:
            return None
        match = re.search(self.translate_regex('on_tvheadend'), phrase)
        if match:
            data = re.sub(self.translate_regex('on_tvheadend'), '', phrase)
            LOGGER.debug(f"Found '{data}' with 'on_tvheadend' in '{phrase}'")
            phrase = data
        match, confidence = match_one(phrase, self.channels)
        r_match, r_confidence = match_one(phrase + " radio", self.channels)
        LOGGER.info(f'Match level {confidence} for {phrase}')
        LOGGER.info(f'Match level {r_confidence} for {phrase} radio')
        if confidence == 1:
            return (match, CPSMatchLevel.EXACT, {"url": match})
        if r_confidence == 1:
            return (r_match, CPSMatchLevel.EXACT, {"url": r_match})
        if confidence > 0.8:
            return (match, CPSMatchLevel.MULTI_KEY, {"url": match})
        if r_confidence > 0.8:
            return (r_match, CPSMatchLevel.MULTI_KEY, {"url": r_match})
        return None

    def CPS_start(self, phrase, data):
        self.wake_up_recognizer(None)
        url = data["url"]
        key_list = list(self.channels.keys())
        val_list = list(self.channels.values())
        pos = val_list.index(url)
        station = key_list[pos]
        self.stop()
        LOGGER.info(f"Playing from \n{url}")
        self.speak_dialog('start', data={"station": station}, wait=True)
        self.add_event("mycroft.stop.handled", self.wake_up_recognizer, once=True)
        self.CPS_play(url, utterance=self.backend)
        self.add_event("mycroft.audio.service.play", self.sleep_recognizer, once=True)

    def on_settings_changed(self):
        self.get_settings()

    def __init__(self):
        super().__init__(name="TVHeadendRadio")

    def wake_up_recognizer(self, message):
        LOGGER.info("Waking up recognizer")
        self.bus.emit(Message('recognizer_loop:wake_up'))

    def sleep_recognizer(self, message):
        LOGGER.info("Sleeping recognizer")
        self.bus.emit(Message('recognizer_loop:sleep'))

    def initialize(self):
        self.settings_change_callback = self.on_settings_changed
        self.get_settings()
        self.audio = AudioService(self.bus)
        backends = self.audio.available_backends()
        self.backend = {}
        if "vlc" in backends.keys():
            self.backend["vlc"] = backends["vlc"]
            self.backend["vlc"]["normal_volume"] = 70
            self.backend["vlc"]["duck_volume"] = 5
            LOGGER.debug("Set vlc as backend to be used")
        self.regexes = {}
        
    def get_settings(self):
        self.channels = {}
        servername = self.settings.get('servername', "")
        if (len(servername) == 0):
            LOGGER.info('Missing server name')
            return
        self.check_internet()

    def check_internet(self):
        LOGGER.info("Checking for connection to tvheadend server")
        names = []
        aliases = []
        username = self.settings.get('username', "")
        password = self.settings.get('password', "")
        servername = self.settings.get('servername', "")
        url = f'http://{servername}:9981/playlist/channels.m3u'
        try:
            r = requests.get(url, auth=(username, password))
            data = r.text.splitlines()
            if (r.status_code is not 200) or (len(r.text) < 100) or (data[0] != "#EXTM3U"):
                LOGGER.info('Unable to get channel list from tvheadend server or wrong format')
                self.schedule_event(self.check_internet, datetime.datetime.now() + datetime.timedelta(minutes=5))
                return
            for i in range(1, 6):
                name = self.settings.get(f'name{i}', "")
                alias = self.settings.get(f'alias{i}', "")
                if (len(name) > 1) and (len(alias) > 1):
                    names.append(name.lower())
                    aliases.append(alias)
            i = 1
            ch_count = 0
            while i < len(data):
                try:
                    i += 2
                    extinf = data[i-2].split(',', 1)
                    name = extinf[1]
                    full_url = data[i-1].split('?', 1)
                    url = f"http://{username}:{password}@{full_url[0][7:]}?profile=audio"
                except:
                    LOGGER.info('Problem parsing channel info (wrong format?)')
                    next
                if (len(name) < 2) or (len(url) < 50):
                    LOGGER.info('Problem parsing channel info:\n' + data[i-2] + "\n" + data[i-1])
                    next
                self.channels[name.lower()] = url
                ch_count += 1
                if name.lower() in names:
                    alias = aliases[names.index(name.lower())]
                    self.channels[alias.lower()] = url
                    ch_count += 1
                    LOGGER.debug(f'Added alias "{alias}" for channel "{name}"')
            LOGGER.info(f"Added {ch_count} channels")
        except:
            LOGGER.info('Unable to contact tvheadend server')
            self.schedule_event(self.check_internet, datetime.datetime.now() + datetime.timedelta(minutes=1))
            return

def create_skill():
    return TVHeadendRadio()

