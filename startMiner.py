
import os, pathlib
import subprocess
import time, signal, json, platform
from subprocess import Popen, PIPE

class StartMiner:
    def __init__(self, log, workerName, miner, devIds, fans):
        self.log = log
        self.proc = None
        self.subChilds = None
        self.workerName = workerName
        self.config = None
        self.devIds = self.ArrToParam(devIds)
        self.fans = self.ArrToParam(fans)
        self.isRunning = False
        self.exePath = None
        self.windowsOS = self.IsWindowsOS()

        curr = pathlib.Path(__file__).parent.absolute()
        minerFolder = os.path.join(curr, "miners")
        dirs = os.listdir(minerFolder)
        for folder in dirs:
            if folder.find(miner) == 0:
                mFolder = os.path.join(minerFolder, folder)
                self.GetConfig(mFolder)
                self.exePath = self.GetExePath(mFolder)
                #self.Start("%s\\%s" % (minerFolder, folder), workerName, devIds, fans, memOCs, coreUCs)

    def ArrToParam(self, arr):
        res = ""
        for item in arr:
            res += str(item) + " "
        return res

    def IsWindowsOS(self):
        if platform.system() == "Windows":
            return True
        else:
            return False

    def GetExePath(self, folder):
        if self.windowsOS:
            return "%s\\miner.exe" % folder
        return "%s/miner" % folder

    def GetConfig(self, miningSoftwareFolder):
        try:
            configPath = os.path.join(miningSoftwareFolder, "config.json")
            self.config = json.loads(open(configPath, 'r').read())
        except Exception as e: 
            self.log.Error("could not find or parse miner software config file %s" % configPath)
            self.log.Error(e)

    def GetRequesterPath(self):
        return "%s:%i%s" % (self.config["api"]["host"], self.config["api"]["port"], self.config["api"]["path"])

    def Start(self, memOCs, coreUCs):
        #print ("ExePath: %s" % exePath)
        
        #print (configPath)
        parameters = self.config["parameters"].replace("#core#", str(coreUCs)).replace("#mem#", str(memOCs)).replace("#fan#", str(self.fans)).replace("#dev#", str(self.devIds)).replace("#worker#", self.workerName)
        self.StartProcess(parameters)
        self.log.Debug(parameters)
        self.log.Debug("will start miner %s" % self.exePath)
        self.log.Debug("started miner with pid: %i" % self.proc.pid)
        time.sleep(1)
        self.GetMinerChildProcessID()
        self.isRunning = True

    def StartProcess(self, parameters):
        if self.IsWindowsOS:
            cmd = "powershell"
            self.proc = subprocess.Popen([cmd, self.exePath, parameters], creationflags = subprocess.CREATE_NEW_CONSOLE)
        else:
            cmd = "/bin/bash"
            self.proc = subprocess.Popen([cmd, self.exePath, parameters], shell=True)
        

    def Stop(self):
        subprocess.call(['taskkill', '/F', '/T', '/PID',  str(self.proc.pid)])
        self.isRunning = False

    def GetMinerChildProcessID(self):
        self.directChilds = self.GetSubProcessIDs(self.proc.pid)
        self.log.Debug("directChilds: %s" % self.directChilds)
        self.subChilds = []
        for child in self.directChilds:
            subchild = self.GetSubProcessIDs(str(child))
            self.subChilds.append(self.GetSubProcessIDs(str(child)))
            self.log.Debug("subchild: %s" % subchild)


    def ProcessesChanged(self):
        childs = self.GetSubProcessIDs(self.proc.pid)
        if len(childs) != len(self.directChilds):
            return True

        subchilds = []
        for i in range(len(childs)):
            if childs[i] != self.directChilds[i]:
                return True
            subchilds.append(self.GetSubProcessIDs(childs[i]))

        if len(subchilds) != len(self.subChilds):
            return True

        for i in range(len(subchilds)):
            if subchilds[i] != self.subChilds[i]:
                return True

        return False

    def GetSubProcessIDsWindows(self, pid):
        command = "Get-WmiObject Win32_Process | Select ProcessID, ParentProcessID"
        process = Popen(["powershell", command], stdout=PIPE)
        (output, err) = process.communicate()
        exit_code = process.wait()
        
        if exit_code == 0 and err == None:
            lines = output.decode("utf-8").split("\r\n")
            res = []
            for line in lines:
                if line.find(str(pid)) >= 0:
                    arr = self.Strip(line)
                    if arr[1] == str(pid):
                        res.append(arr[0])
            return res
        else:
            self.log.Error("could not get subprocesses: \"%s\"" % command)
            self.log.Debug("Code: %i:\n%s" %(exit_code, err))
            return None

    def GetSubProcessIDsUnix(self, pid):
        res = []
        command = "ps -o pid --ppid %d --noheaders" % pid
        process = Popen(command, shell=True, stdout=subprocess.PIPE)
        (output, err) = process.communicate()
        exit_code = process.wait()
        if exit_code == 0:
            lines = output.decode("utf-8").replace(" ", "").split("\n")
            for pid_str in lines[:-1]:
                res.append(int(pid_str))
            return res
        else:
            self.log.Error("could not get subprocesses: \"%s\"" % command)
            self.log.Debug("Code: %i:\n%s" %(exit_code, err))
            return None

    def GetSubProcessIDs(self, pid):
        if self.IsWindowsOS():
            return self.GetSubProcessIDsWindows(pid)
        else:
            return self.GetSubProcessIDsUnix(pid)

    def Strip(self, txt):
        while txt.find("  ") >= 0:
            txt = txt.replace("  ", " ")
        res = txt.split(" ")
        newRes = []
        for item in res:
            if item != "":
                #print("adding item %s" % item.split(" ")[0])
                newRes.append(item)
        return newRes