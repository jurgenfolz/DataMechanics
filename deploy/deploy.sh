#!/usr/bin/env bash
# Ship the working tree to the VPS and restart the site. Run from the project root:
#   deploy/deploy.sh root@<vps-address>
# It needs only tar and ssh on this machine; the server mirrors the release into place with rsync.
set -euo pipefail

TARGET=${1:?"usage: deploy/deploy.sh root@<vps-address>"}
APP=/srv/datamechanics
STAGE=/tmp/datamechanics-release

tar --exclude-from=deploy/rsync-exclude -czf - . | ssh "$TARGET" "rm -rf $STAGE && mkdir -p $STAGE && tar -xzf - -C $STAGE"

ssh "$TARGET" bash -s <<EOF
set -euo pipefail
# Code: mirror the release, minus local-only files. Media is copied separately below.
rsync -a --delete --chown=datamechanics:datamechanics --exclude-from=$STAGE/deploy/rsync-exclude --exclude=/media $STAGE/ $APP/
# Media: add new flags and images, but never delete files that only exist on the server.
rsync -a --chown=datamechanics:datamechanics $STAGE/media/ $APP/media/
rm -rf $STAGE
bash $APP/deploy/update.sh
EOF
