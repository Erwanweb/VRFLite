"""
CASA-IA Blind percentage control python plugin for Domoticz
Author: Erwanweb,
Version:    0.0.1: alpha
            0.0.2: beta
"""
"""
<plugin key="VRFLite" name="AC Cabled Blind LITE" author="Erwanweb" version="0.0.2" externallink="https://github.com/Erwanweb/VRFLite.git">
    <description>
        <h2>Control of cabled blinds for CASA-IA</h2><br/>
        Easily control cabled blinds with FGR212<br/>
        <h3>Set-up and Configuration</h3>
    </description>
    <params>
        <param field="Address" label="Domoticz IP Address" width="200px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="40px" required="true" default="8080"/>
        <param field="Username" label="Username" width="200px" required="false" default=""/>
        <param field="Password" label="Password" width="200px" required="false" default=""/>
        <param field="Mode1" label="Blind percentage Idx (csv list of idx)" width="200px" required="true" default=""/>
        <param field="Mode6" label="Logging Level" width="200px">
            <options>
                <option label="Normal" value="Normal"  default="true"/>
                <option label="Verbose" value="Verbose"/>
                <option label="Debug - Python Only" value="2"/>
                <option label="Debug - Basic" value="62"/>
                <option label="Debug - Basic+Messages" value="126"/>
                <option label="Debug - Connections Only" value="16"/>
                <option label="Debug - Connections+Queue" value="144"/>
                <option label="Debug - All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json
import urllib.parse as parse
import urllib.request as request
from datetime import datetime, timedelta
import time
import base64
import itertools

class deviceparam:

    def __init__(self, unit, nvalue, svalue):
        self.unit = unit
        self.nvalue = nvalue
        self.svalue = svalue


class BasePlugin:

    def __init__(self):

        self.debug = False
        self.Blinds = []
        self.Autoactionchangedtime = datetime.now()
        self.loglevel = None
        self.statussupported = True
        return


    def onStart(self):

        # setup the appropriate logging level
        try:
            debuglevel = int(Parameters["Mode6"])
        except ValueError:
            debuglevel = 0
            self.loglevel = Parameters["Mode6"]
        if debuglevel != 0:
            self.debug = True
            Domoticz.Debugging(debuglevel)
            DumpConfigToLog()
            self.loglevel = "Verbose"
        else:
            self.debug = False
            Domoticz.Debugging(0)

        # create the child devices if these do not exist yet
        devicecreated = []
        if 1 not in Devices:
            Options = {"LevelActions":"||",
                       "LevelNames":"Manual|Auto",
                       "LevelOffHidden":"false",
                       "SelectorStyle":"0"}
            Domoticz.Device(Name = "Mode",Unit = 1,TypeName = "Selector Switch",Switchtype = 18,Image = 9,
                            Options = Options,Used = 1).Create()
            devicecreated.append(deviceparam(1,0,"0"))  # default is off
        if 2 not in Devices:
            Options = {"LevelActions":"||",
                       "LevelNames":"Waiting|Close|Open",
                       "LevelOffHidden":"true",
                       "SelectorStyle":"0"}
            Domoticz.Device(Name = "Manual Control",Unit = 2,TypeName = "Selector Switch",Switchtype = 18,Image = 9,
                            Options = Options,Used = 1).Create()
            devicecreated.append(deviceparam(2,0,"0"))  # default is waiting
        if 3 not in Devices:
            Options = {"LevelActions":"||",
                       "LevelNames":"Waiting|Close|Open",
                       "LevelOffHidden":"true",
                       "SelectorStyle":"0"}
            Domoticz.Device(Name = "Auto Control",Unit = 3,TypeName = "Selector Switch",Switchtype = 18,Image = 9,
                            Options = Options,Used = 1).Create()
            devicecreated.append(deviceparam(3,0,"0"))  # default is waiting

        # if any device has been created in onStart(), now is time to update its defaults
        for device in devicecreated:
            Devices[device.unit].Update(nValue=device.nvalue, sValue=device.svalue)

        # build lists of alarm sensors
        self.Blinds = parseCSV(Parameters["Mode1"])
        Domoticz.Debug("Blind percentage = {}".format(self.Blinds))


    def onStop(self):

        Domoticz.Debugging(0)


    def onCommand(self,Unit,Command,Level,Color):

        Domoticz.Debug("onCommand called for Unit {}: Command '{}', Level: {}".format(Unit, Command, Level))

        if (Unit == 1):
            Devices[1].Update(nValue = 0,sValue = str(Level))
            if (Devices[1].sValue == "10"):
                Devices[1].Update(nValue = 1,sValue = "10")
            else :
                Devices[1].Update(nValue = 0,sValue = "0")

        if (Unit == 2):
            Devices[2].Update(nValue = 1,sValue = str(Level))
            if (Devices[2].sValue == "10"):
                Devices[2].Update(nValue = 1,sValue = "10")
                for idx in self.Blinds:
                    DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Set Level&level=99".format(idx))
                    Domoticz.Debug("manual command - Close")

            elif (Devices[2].sValue == "20"):
                Devices[2].Update(nValue = 1,sValue = "20")
                for idx in self.Blinds:
                    DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Set Level&level=0".format(idx))
                    Domoticz.Debug("manual command - Open")

        if (Unit == 3):
            Devices[3].Update(nValue = 0,sValue = str(Level))
            if (Devices[3].sValue == "10"):
                Devices[3].Update(nValue = 1,sValue = "10")
            elif (Devices[3].sValue == "20"):
                Devices[3].Update(nValue = 1,sValue = "20")
            else :
                Devices[3].Update(nValue = 0,sValue = "0")


    def onHeartbeat(self):

        # fool proof checking....
        if not all(device in Devices for device in (1,2,3)):
            Domoticz.Error("one or more devices required by the plugin is/are missing, please check domoticz device creation settings and restart !")
            return

        if Devices[2].nValue == 1:
            Devices[2].Update(nValue = 0,sValue = "0")

        now = datetime.now()

        if self.Autoactionchangedtime + timedelta(seconds = 30) <= now:
            if Devices[3].nValue == 1:
                Devices[3].Update(nValue = 0,sValue = "0")

        else :
            if (Devices[1].sValue == "10"):
                if (Devices[3].sValue == "10"):
                    Devices[3].Update(nValue = 1,sValue = "10")
                    for idx in self.Blinds:
                        DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Set Level&level=99".format(idx))
                        self.Autoactionchangedtime = datetime.now()
                        Domoticz.Debug("auto command - Close")

                elif (Devices[3].sValue == "20"):
                    Devices[3].Update(nValue = 1,sValue = "20")
                    for idx in self.Blinds:
                        DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Set Level&level=0".format(idx))
                        self.Autoactionchangedtime = datetime.now()
                        Domoticz.Debug("auto command - Open")




    def WriteLog(self, message, level="Normal"):

        if self.loglevel == "Verbose" and level == "Verbose":
            Domoticz.Log(message)
        elif level == "Normal":
            Domoticz.Log(message)



global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onCommand(Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Color)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


# Plugin utility functions ---------------------------------------------------

def parseCSV(strCSV):

    listvals = []
    for value in strCSV.split(","):
        try:
            val = int(value)
        except:
            pass
        else:
            listvals.append(val)
    return listvals


def DomoticzAPI(APICall):

    resultJson = None
    url = "http://{}:{}/json.htm?{}".format(Parameters["Address"], Parameters["Port"], parse.quote(APICall, safe="&="))
    Domoticz.Debug("Calling domoticz API: {}".format(url))
    try:
        req = request.Request(url)
        if Parameters["Username"] != "":
            Domoticz.Debug("Add authentification for user {}".format(Parameters["Username"]))
            credentials = ('%s:%s' % (Parameters["Username"], Parameters["Password"]))
            encoded_credentials = base64.b64encode(credentials.encode('ascii'))
            req.add_header('Authorization', 'Basic %s' % encoded_credentials.decode("ascii"))

        response = request.urlopen(req)
        if response.status == 200:
            resultJson = json.loads(response.read().decode('utf-8'))
            if resultJson["status"] != "OK":
                Domoticz.Error("Domoticz API returned an error: status = {}".format(resultJson["status"]))
                resultJson = None
        else:
            Domoticz.Error("Domoticz API: http error = {}".format(response.status))
    except:
        Domoticz.Error("Error calling '{}'".format(url))
    return resultJson


def CheckParam(name, value, default):

    try:
        param = int(value)
    except ValueError:
        param = default
        Domoticz.Error("Parameter '{}' has an invalid value of '{}' ! defaut of '{}' is instead used.".format(name, value, default))
    return param


# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return