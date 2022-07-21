# from morse import Morse
import numpy as np
import re

class Subject:
    def __init__(self, id, type, pid: int = -1, ppid: str = None, cmdLine: str = None, processName: str = None):
        self.id = id
        self.type = type
        self.pid = pid
        self.ppid = ppid
        self.cmdLine = cmdLine
        self.processName = processName
        self.updateTime = 0
        self.owner = None

        # init tags
        self.ciTag: float = 0.0
        self.eTag: float = 0.0
        self.iTag: float = 0.0
        self.cTag: float = 0.0

        self.ciTag_grad: float = 1.0
        self.eTag_grad: float = 1.0
        self.iTag_grad: float = 1.0
        self.cTag_grad: float = 1.0

        self.ciTag_initID = None
        self.eTag_initID = None
        self.iTag_initID = None
        self.cTag_initID = None

    def dumps(self) -> str:
        json_dict = {}
        json_dict['id'] = self.id
        # json_dict['time'] = self.time
        json_dict['type'] = self.type
        # json_dict['subtype'] = self.subtype
        json_dict['pid'] = self.pid
        json_dict['ppid'] = self.ppid
        json_dict['cmdLine'] = self.cmdLine
        json_dict['processName'] = self.processName
        return str(json_dict)

    def get_id(self):
        return self.id
    
    def get_pid(self):
        return self.pid

    def get_name(self):
        return self.processName

    def get_cmdln(self):
        return self.cmdLine

    def tags(self):
        return [float(self.ciTag), float(self.eTag), float(self.iTag), float(self.cTag)]

    def setSubjTags(self,tags):
        self.ciTag = tags[0]
        self.eTag = tags[1]
        self.iTag = tags[2]
        self.cTag = tags[3]

    def get_grad(self):
        return [self.ciTag_grad, self.eTag_grad, self.iTag_grad, self.cTag_grad]

    def get_citag_grad(self):
        return self.ciTag_grad
    
    def get_etag_grad(self):
        return self.eTag_grad

    def get_itag_grad(self):
        return self.iTag_grad

    def get_ctag_grad(self):
        return self.cTag_grad

    def set_grad(self, grads):
        self.ciTag_grad = grads[0]
        self.eTag_grad = grads[1]
        self.iTag_grad = grads[2]
        self.cTag_grad = grads[3]
    
    def setInitID(self, InitID):
        self.ciTag_initID = InitID[0]
        self.eTag_initID = InitID[1]
        self.iTag_initID = InitID[2]
        self.cTag_initID = InitID[3]

    def getInitID(self):
        return [self.ciTag_initID, self.eTag_initID, self.iTag_initID, self.cTag_initID]

    def isMatch(self, string):
        if self.processName == None:
            return False
        return isinstance(re.search(string, self.processName), re.Match)
