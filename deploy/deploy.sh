#! /bin/bash

echo 'Extracting blog...'
cd /srv/www/
rm -rf blog/
tar -xvf blog.tar

echo 'Installing python dependencies...'
cd blog
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -
source $HOME/.poetry/env
poetry config virtualenvs.in-project true --local
poetry install --no-interaction --no-ansi

echo 'Configuring systemd unit file...'
mkdir -p ~/.config/systemd/user/
cp deploy/blog.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user stop blog.service
systemctl --user start blog.service
