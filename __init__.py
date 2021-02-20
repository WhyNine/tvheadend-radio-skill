from mycroft.util.log import getLogger
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.audio.services.vlc import VlcService
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
        while True:
            if phrase in self.channelnames:
                LOGGER.info('Matched {}'.format(phrase))
                i = self.channelnames.index(phrase)
                data = {'url': self.channelurls[i], 'name': phrase}
                return phrase, CPSMatchLevel.TITLE, data
            if phrase.lower().find("radio") < 0:
                phrase += " radio"
            else:
                break
        return None

    def CPS_start(self, phrase, data):
#        if self.audioservice:
#           self.audioservice.stop()
        url = []
        url.append(data["url"])
        station = data["name"]
        if self.vlc_player.player.is_playing():
            self.vlc_player.stop()
        self.vlc_player.clear_list()
        try:
            self.vlc_player.add_list(url)
            self.vlc_player.play()
            LOGGER.info(f"Playing from \n{url}")
        except Exception as e:
            LOGGER.info(type(e))
            LOGGER.info("Unexpected error:", sys.exc_info()[0])
            raise
#        self.audioservice.play(url)
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
        self.vlc_player = VlcService(config={'duck': False})
        self.vlc_player.normal_volume = 85
        self.vlc_player.low_volume = 20
        
    def get_settings(self):
        self.channelnames = []
        self.channelurls = []
        names = []
        aliases = []
        for i in range(1, 6):
            name = self.settings.get('name{}'.format(i), "")
            alias = self.settings.get('alias{}'.format(i), "")
            LOGGER.info('Settings: {} {} {}'.format(i, name, alias))
            if (len(name) > 1) and (len(alias) > 1):
                LOGGER.info('appending')
                names.append(name.lower())
                aliases.append(alias)
        username = self.settings.get('username', "")
        password = self.settings.get('password', "")
        servername = self.settings.get('servername', "")
        if (len(servername) == 0):
            LOGGER.info('Missing server name')
            return
        url = 'http://{}:9981/playlist/channels.m3u'.format(servername)
        r = requests.get(url, auth=(username, password))
#        LOGGER.info('returned code is {}'.format(r.status_code))
#        LOGGER.info('returned file is\n{}'.format(r.text))
        data = r.text.splitlines()
        if (r.status_code is not 200) or (len(r.text) < 100) or (data[0] != "#EXTM3U"):
            LOGGER.info('Unable to get channel list from server or wrong format')
            return
        i = 1
        ch_count = 0
        while i < len(data):
            try:
                extinf = data[i].split(',', 1)
                name = extinf[1]
                i += 1
                full_url = data[i].split('?', 1)
                url = "http://" + username + ":" + password + "@" + full_url[0][7:] + '?profile=audio'
#                url = "http://" + username + ":" + password + "@" + data[i][7:]
                i += 1
            except:
                LOGGER.info('Problem parsing channel info (wrong format?)')
                next
            if (len(name) < 2) or (len(url) < 50):
                LOGGER.info('Problem parsing channel info:\n' + data[i-2] + "\n" + data[i-1])
                next
            self.channelnames.append(name.lower())
            self.channelurls.append(url)
            ch_count += 1
#            LOGGER.info(f"Added channel {name}")
            if name.lower() in names:
                alias = aliases[names.index(name.lower())]
                self.channelnames.append(alias.lower())
                self.channelurls.append(url)
                ch_count += 1
#                LOGGER.info(f'Added alias {alias} for channel {name}')
        LOGGER.info(f"Added {ch_count} channels")


def create_skill():
    return TVHeadendRadio()

