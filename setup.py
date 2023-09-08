from distutils.core import setup
import os

lib_folder = os.path.dirname(os.path.realpath(__file__))
requirement_path = f"{lib_folder}/requirements.txt"
install_requires = []
if os.path.isfile(requirement_path):
    with open(requirement_path) as f:
        install_requires = f.read().splitlines()

setup(
   name='TvheadendRadio',
   version='0.1',
   packages=['tvheadend_radio_skill',],
   install_requires=install_requires,
   license='Apache 2.0',
   long_description='Radio player using a TVheadend URL as the source',
)
