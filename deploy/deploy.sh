#! /bin/bash

echo 'Installing blog...'
cd /srv/www/
rm -rf blog/
mkdir blog
python -m venv blog/.venv
. blog/.venv/bin/activate
python -m pip install blog-0.0.0.tar.gz

echo 'Configuring systemd unit file...'
mkdir -p ~/.config/systemd/user/
cp blog.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user stop blog.service
systemctl --user start blog.service
systemctl --user enable blog.service
