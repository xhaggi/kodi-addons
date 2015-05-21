#!/bin/sh

./TexturePacker -input addons/skin.xperience1080x/media -output addons/skin.xperience1080x/media/Textures.xbt
find ./addons/skin.xperience1080x/media ! -name 'Textures.xbt' -type df -exec rm -R {} \;

./TexturePacker -input addons/skin.droid/media -output addons/skin.droid/media/Textures.xbt
find ./addons/skin.droid/media ! -name 'Textures.xbt' -type df -exec rm -R {} \;
