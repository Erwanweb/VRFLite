# VRFLite
VRFLite

install :

cd ~/domoticz/plugins

mkdir VRFLite

sudo apt-get update

sudo apt-get install git

git clone https://github.com/Erwanweb/VRFLite.git VRFLite

cd VRFLite

sudo chmod +x plugin.py

sudo /etc/init.d/domoticz.sh restart

Upgrade :

cd ~/domoticz/plugins/VRFLite

git reset --hard

git pull --force

sudo chmod +x plugin.py

sudo /etc/init.d/domoticz.sh restart
