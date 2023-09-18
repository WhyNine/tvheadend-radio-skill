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
from ovos_utils.log import LOG
from ovos_utils.parse import match_one
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill
from ovos_plugin_common_play.ocp import MediaType, PlaybackType, MycroftAudioService
import re
import requests
import datetime


class TVHeadendRadio(OVOSCommonPlaybackSkill):
    # Get the correct localised regex
    def translate_regex(self, regex):
        if regex not in self.regexes:
            path = self.find_resource(regex + ".regex")
            if path:
                with open(path) as f:
                    string = f.read().strip()
                self.regexes[regex] = string
        return self.regexes[regex]

    @ocp_search()
    def search_my_skill(self, phrase, media_type=MediaType.GENERIC):
        if len(self.channels) == 0:
            return None
        match = re.search(self.translate_regex("on_tvheadend"), phrase)
        if match:
            data = re.sub(self.translate_regex("on_tvheadend"), "", phrase)
            LOG.debug(f"Found '{data}' with 'on_tvheadend' in '{phrase}'")
            phrase = data
        match, confidence = match_one(phrase, self.channels)
        key_list = list(self.channels.keys())
        val_list = list(self.channels.values())
        pos = val_list.index(match)
        station = key_list[pos]
        LOG.info(f"Match level {confidence} for {phrase}")
        yield {
          "match_confidence": confidence * 100,
          "media_type": MediaType.RADIO,
          "uri": match,
          "title": station,
          "playback": PlaybackType.AUDIO,
          "skill_id": self.skill_id            
        }
        r_match, r_confidence = match_one(phrase + " radio", self.channels)
        LOG.info(f"Match level {r_confidence} for {phrase} radio")
        pos = val_list.index(r_match)
        station = key_list[pos]
        return {
          "match_confidence": r_confidence * 100,
          "media_type": MediaType.RADIO,
          "uri": r_match,
          "title": station,
          "playback": PlaybackType.AUDIO,
          "skill_id": self.skill_id            
        }

    def CPS_start(self, phrase, data):
        url = data["url"]
        key_list = list(self.channels.keys())
        val_list = list(self.channels.values())
        pos = val_list.index(url)
        station = key_list[pos]
        self.stop()
        LOG.info(f"Playing from \n{url}")
        self.speak_dialog("start", data={"station": station}, wait=True)
        self.CPS_play(url, utterance=self.backend)

    def on_settings_changed(self):
        self.get_settings()

    def __init__(self, *args, **kwargs):
        super(TVHeadendRadio, self).__init__(*args, **kwargs)
        self.skill_id = "whynine-tvheadenradio-skill"
        self.supported_media = [MediaType.GENERIC,
                                MediaType.RADIO,
                                MediaType.MUSIC]

    def initialize(self):
        self.settings_change_callback = self.on_settings_changed
        self.get_settings()
        self.audio = MycroftAudioService(self.bus)
        backends = self.audio.available_backends()
        self.backend = {}
        if "vlc" in backends.keys():
            self.backend["vlc"] = backends["vlc"]
            self.backend["vlc"]["normal_volume"] = 70
            self.backend["vlc"]["duck_volume"] = 5
            LOG.debug("Set vlc as backend to be used")
        self.regexes = {}

    def get_settings(self):
        self.channels = {}
        servername = self.settings.get("servername", "")
        if len(servername) == 0:
            LOG.info("Missing server name")
            return
        self.check_internet()

    def check_internet(self):
        LOG.info("Checking for connection to tvheadend server")
        names = []
        aliases = []
        username = self.settings.get("username", "")
        password = self.settings.get("password", "")
        servername = self.settings.get("servername", "")
        url = f"http://{servername}:9981/playlist/channels.m3u"
        try:
            r = requests.get(url, auth=(username, password))
            data = r.text.splitlines()
            if (
                (r.status_code is not 200)
                or (len(r.text) < 100)
                or (data[0] != "#EXTM3U")
            ):
                LOG.info(
                    "Unable to get channel list from tvheadend server or wrong format"
                )
                self.schedule_event(
                    self.check_internet,
                    datetime.datetime.now() + datetime.timedelta(minutes=5),
                )
                return
            for i in range(1, 6):
                name = self.settings.get(f"name{i}", "")
                alias = self.settings.get(f"alias{i}", "")
                if (len(name) > 1) and (len(alias) > 1):
                    names.append(name.lower())
                    aliases.append(alias)
            i = 1
            ch_count = 0
            while i < len(data):
                try:
                    i += 2
                    extinf = data[i - 2].split(",", 1)
                    name = extinf[1]
                    full_url = data[i - 1].split("?", 1)
                    url = (
                        f"http://{username}:{password}@{full_url[0][7:]}?profile=audio"
                    )
                except:
                    LOG.info("Problem parsing channel info (wrong format?)")
                    next
                if (len(name) < 2) or (len(url) < 50):
                    LOG.info(
                        "Problem parsing channel info:\n"
                        + data[i - 2]
                        + "\n"
                        + data[i - 1]
                    )
                    next
                self.channels[name.lower()] = url
                ch_count += 1
                if name.lower() in names:
                    alias = aliases[names.index(name.lower())]
                    self.channels[alias.lower()] = url
                    ch_count += 1
                    LOG.debug(f'Added alias "{alias}" for channel "{name}"')
            LOG.info(f"Added {ch_count} channels")
        except:
            LOG.info("Unable to contact tvheadend server")
            self.schedule_event(
                self.check_internet,
                datetime.datetime.now() + datetime.timedelta(minutes=1),
            )
            return


def create_skill():
    return TVHeadendRadio()
