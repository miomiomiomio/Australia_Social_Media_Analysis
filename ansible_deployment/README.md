Readme For Ansible


This fold includes:
1 ansible files 
2 dockerfiles for building docker images
3 docker-compose file for applying swarm
4 nginx.conf.j2 filr for reverse proxy.

Users just need type in ./run-nectar.sh to deploy instances. After the run-nectar.sh run. We will deploy four instances on nectar and configure proxy. Then docker and docker compose will be installed and configured. Finally, we will deploy docker services properly to these instances. Different dockre files to build images are in dockerFileFolder. The responsibility of them is for building corresponding environment for python files. Some python files are not in current floder, for displaying propose, they are in other folder. For couchDB, we use official image and make some change to the configure file, so that we could make them a cluster.