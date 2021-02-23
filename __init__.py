from mycroft.util.log import getLogger
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.audio.services.vlc import VlcService
from mycroft.skills.audioservice import AudioService
from mycroft.util.parse import match_one
import requests
import sys

LOGGER = getLogger(__name__)

class TVHeadendRadio(CommonPlaySkill):
    def exists_url(self, url):
        r = requests.head(url)
        if r.status_code < 400:
            return True
        else:
            return False

    def CPS_match_query_phrase(self, phrase):
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
        url = data["url"]
        key_list = list(self.channels.keys())
        val_list = list(self.channels.values())
        pos = val_list.index(url)
        station = key_list[pos]
        self.stop()
        self.CPS_play(url, "vlc")
        LOGGER.info(f"Playing from \n{url}")
        self.speak_dialog('start', data={"station": station}, wait=False)


    def handle_stop(self, message):
        self.stop()
        self.speak_dialog('stop', data={"station": station}, wait=False)

    def on_settings_changed(self):
        self.get_settings()

    def __init__(self):
        super().__init__(name="TVHeadendRadio")
        self.vlc_player = None

    def initialize(self):
        self.settings_change_callback = self.on_settings_changed
        self.get_settings()
        self.audio = AudioService(self.bus)
        LOGGER.info(list(self.audio.available_backends().keys()))
        LOGGER.info(self.audio.available_backends())
        
    def get_settings(self):
        self.channels = {}
        names = []
        aliases = []
        for i in range(1, 6):
            name = self.settings.get(f'name{i}', "")
            alias = self.settings.get(f'alias{i}', "")
            if (len(name) > 1) and (len(alias) > 1):
                names.append(name.lower())
                aliases.append(alias)
        username = self.settings.get('username', "")
        password = self.settings.get('password', "")
        servername = self.settings.get('servername', "")
        if (len(servername) == 0):
            LOGGER.info('Missing server name')
            return
        url = f'http://{servername}:9981/playlist/channels.m3u'
        r = requests.get(url, auth=(username, password))
        data = r.text.splitlines()
        if (r.status_code is not 200) or (len(r.text) < 100) or (data[0] != "#EXTM3U"):
            LOGGER.info('Unable to get channel list from server or wrong format')
            return
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
                LOGGER.info(f'Added alias "{alias}" for channel "{name}"')
        LOGGER.info(f"Added {ch_count} channels")


def create_skill():
    return TVHeadendRadio()

