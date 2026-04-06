#!/bin/bash

set -e

# Get owner of the mounted volume
VOLUME_UID=$(stat -c '%u' /workdir)
VOLUME_GID=$(stat -c '%g' /workdir)

USER=eyeon

# Create user with same UID/GID if it doesn't match root
if [ "$VOLUME_UID" = "0" ]; then
    VOLUME_UID=1000
    VOLUME_GID=1000
fi

# Create group if it doesn't exist
if ! getent group $VOLUME_GID > /dev/null 2>&1; then
    groupadd -g $VOLUME_GID eyeon
fi

# Create user if it doesn't exist
if ! getent passwd $VOLUME_UID > /dev/null 2>&1; then
    useradd -u $VOLUME_UID -g $VOLUME_GID -s /bin/bash -m eyeon
fi

#change ownership of /tmp to eyeon for surfactant
chown -R $VOLUME_UID:$VOLUME_GID /tmp
chmod g+s /tmp

# Run the command as the appropriate user
exec gosu $VOLUME_UID:$VOLUME_GID "$@"
