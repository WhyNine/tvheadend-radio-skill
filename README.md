# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/headphones.svg' card_color='#DB4E40' width='50' height='50' style='vertical-align:bottom'/> TVHeadend Radio
Plays audio streams from a TVHeadend server

## About
This skill plays a channel from a TVHeadend server, using the audio profile as defined on the server (this means that the video on TV channels is not streamed or decoded). The user can enter aliases for up to five channels to make it easier to request these channels.

This skill was originally written for Mycroft but has been migrated to OVOS.


## Examples
* "Play <radio channel>"
* "Play <channel alias>"
* "Play <radio channel> radio"
* "Play <radio channel> on TVHeadend"
* "Play <channel alias> on TVHeadend"
* "Play <radio channel> radio on TVHeadend"

## Credits
Simon Waller

## Category
Music

## Tags
#Radio
#TVHeadend


## Settings
The skill needs to know some details of the TVHeadend server so that it can retrieve the channel list and then to stream the requested channel. Specifically, it needs to have:
* The server name or IP address, such that the skill can locate the server using the URL "http://<server_name>:9981/"
* A username and password that will enable the skill to access the server (this user does not need to have admin rights but it must include Basic in the Streaming setting)

In addition, up to five aliases can be entered. This allows for shortcuts to favourite channels, particularly useful if the voice recognition doesn't like the abbreviations or acronyms in the channel name.
