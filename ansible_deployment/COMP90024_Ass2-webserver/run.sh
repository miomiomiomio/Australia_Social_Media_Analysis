#!/bin/bash

sudo apt-get install python-dev python-pip git docker.io
sudo pip install virtualenv
#sudo apt-get install docker-ce docker-ce-li containerd.io
python3 -m venv WebApp/venv
#cd WebApp
source WebApp/venv/bin/activate

sudo docker build -t bububiubiu/webapp:p5000 .
# sudo docker stop containerapp
# sudo docker rm containerapp
# sudo service docker restart
# docker run -d --name containerapp --restart=always -p 5000:5000 webapp
