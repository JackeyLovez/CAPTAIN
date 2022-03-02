import time
import sys
sys.path.extend(['.','..','...'])

# import floatTags
from graph.Subject import Subject
from graph.Object import Object
from policy.floatTags import TRUSTED, UNTRUSTED, BENIGN, PUBLIC
from policy.floatTags import isTRUSTED, isUNTRUSTED
from policy.floatTags import citag,ctag,invtag,itag,etag,alltags, isRoot, permbits
from parse.eventType import SET_UID_SET, lttng_events, cdm_events, standard_events
from parse.eventType import READ_SET, LOAD_SET, EXECVE_SET, WRITE_SET, INJECT_SET, CREATE_SET, RENAME_SET, MPROTECT_SET, REMOVE_SET

class AlarmArguments():
   
   def __init__(self) -> None:
       self.rootprinc = None

def printTime(ts):
   # Transfer time to ET
   time_local = time.localtime((ts/1000000000) + 3600)
   dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
   print(dt, end='')

def getTime(ts):
   # Transfer time to ET
   time_local = time.localtime((ts/1000000000) + 3600)
   dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
   return dt

def prtSOAlarm(ts, an, s, o, alarms, event_id, alarmfile= None):
   if not alarms[(s.get_pid(), o.get_name())]:
      alarms[(s.get_pid(), o.get_name())] = True
      if alarmfile:
         # with open(alarmfile, 'a') as fout:
         alarm_string = "{} AlarmS {} : Alarm: {} : Object {} ({}) Subject {}  pid={} {}  AlarmE\n".format(event_id, getTime(ts), an, o.get_id(),o.get_name(), s.get_id(), s.get_pid(), s.get_cmdln())
         alarmfile.write(alarm_string)
      return an
   

def prtSSAlarm(ts, an, s, ss, event_id, alarmfile= None):
   # Question
   # print(": Alarm: ", an, ": Subject ", s.get_subjid(), " pid=", s.get_pid(),
   #        " ", s.get_cmdln(), " Subject ", ssubjid(ss), " pid=", ss.get_pid(), " ", ss.get_cmdln(), " AlarmE", "\n")
   if alarmfile:
      # with open(alarmfile, 'a') as fout:
      alarm_string = "{} AlarmS {} : Alarm: {} : Subject {} pid={} {} Subject {} pid={} {} AlarmE\n".format(event_id, getTime(ts), an, s.get_id(), s.get_pid(), s.get_cmdln(),ss.get_id(), ss.get_pid(), ss.get_cmdln())
      alarmfile.write(alarm_string)
   return an


def prtSAlarm(ts, an, s, event_id, alarmfile= None):
   if alarmfile:
      # with open(alarmfile, 'a') as fout:
      alarm_string = "{} AlarmS {} : Alarm: {} : Subject {} pid={} {} AlarmE\n".format(event_id, getTime(ts), an, s.get_id(), s.get_pid(), s.get_cmdln())
      alarmfile.write(alarm_string)
   return an

def check_alarm_pre(event, s, o, alarms, created, alarm_sum, format = 'cdm', morse = None, alarm_file = None):
   ts = event['timestamp']
   if format == 'cdm':
      event_type = cdm_events[event['type']]
   elif format == 'lttng':
      event_type = lttng_events[event['type']]

   alarmarg = AlarmArguments()
   alarmarg.origtags = None
   alarmarg.pre_alarm = None

   if event_type in READ_SET or event_type in LOAD_SET or event_type in EXECVE_SET or event_type in INJECT_SET or event_type in MPROTECT_SET:
      alarmarg.origtags = s.tags()

   # write_pre(_, o, useful, _, _)|useful --> origtags = o.tags()
   if event_type in WRITE_SET:
      alarmarg.origtags = o.tags()

   # inject_pre(_, s, useful, _)|useful -->  origtags = subjTags(s);
   if event_type in INJECT_SET:
      alarmarg.origtags = o.tags()

   # setuid_pre(s, _, ts) --> {
   #    if (itag(subjTags(s)) < 128) {
   #       rootprinc = isRoot(sowner(s));
   #    }
   # }
   if event_type in SET_UID_SET:
      if (itag(s.tags()) < 0.5):
         alarmarg.rootprinc = isRoot(morse.Principals[s.owner])

   # if event_type in {standard_events['EVENT_WRITE'],standard_events['EVENT_SENDMSG']}:
   #    alarmarg.origtags = o.tags()

   #    remove_pre(s, o, ts) --> {
   #       if (itag(objTags(o)) > 127 && itag(subjTags(s)) < 128 && !isMatch(o, "null")  ) {
   #          if (!alarms[(pid(s), name(o))]) talarms = talarms + 1
   #          prtSOAlarm(ts, "FileCorruption", s, o, alarms)
   #       }
   #    }
   if event_type in REMOVE_SET:
      assert isinstance(o,Object) and isinstance(s,Subject)
      if (itag(o.tags()) > 0.5 and itag(s.tags()) < 0.5 and o.isMatch("null") == False):
            if not alarms[(s.get_pid(), o.get_name())]:
               alarm_sum[1] = alarm_sum[1] + 1
            alarmarg.pre_alarm = prtSOAlarm(ts, "FileCorruption", s, o, alarms, event['uuid'], alarm_file)
  
   #    rename_pre(s, o, _, _, ts) --> {
   #       if (itag(objTags(o)) > 127 && itag(subjTags(s)) < 128 && !isMatch(o, "null") ) {
   #          if (!alarms[(pid(s), name(o))]) talarms = talarms + 1
   #          prtSOAlarm(ts, "FileCorruption", s, o, alarms)
   #       }

   #    }

   if event_type in RENAME_SET :
      if itag(o.tags()) > 0.5 and itag(s.tags()) < 0.5 and o.isMatch("null")==False:
         if not alarms[(s.get_pid(), o.get_name())]:
            alarm_sum[1] = alarm_sum[1] + 1
         alarmarg.pre_alarm = prtSOAlarm(ts, "FileCorruption", s, o, alarms, event['uuid'], alarm_file)


   #    chmod_pre(s, o, p, ts) --> {
   #       unsigned ositag = itag(objTags(o))
   #       unsigned prm = permbits(p)
      
   #       if (ositag < 128 && ((prm & 0111) != 0)) {
   #    if (!alarms[(pid(s), name(o))]) talarms = talarms + 1
   #          prtSOAlarm(ts, "MkFileExecutable", s, o, alarms)
   #       }
   #    }

   if event_type == standard_events['EVENT_MODIFY_FILE_ATTRIBUTES']:
      ositag = itag(o.tags())
      prm = permbits(event)
      if (ositag < 0.5 and ((prm & int('0111',8)) != 0)):
         if (alarms[(s.get_pid(), o.get_name())] == False):
            alarm_sum[1] = alarm_sum[1] + 1
         alarmarg.pre_alarm = prtSOAlarm(ts, "MkFileExecutable", s, o, alarms, event['uuid'], alarm_file)
   

   return alarmarg


def check_alarm(event, s, o, alarms, created, alarm_sum, alarmarg, format = 'cdm', morse = None, alarm_file = None):
   ts = event['timestamp']

   alarm_result = None

   if format == 'cdm':
      event_type = cdm_events[event['type']]
   elif format == 'lttng':
      event_type = lttng_events[event['type']]

   if alarmarg.pre_alarm != None:
      alarm_result = alarmarg.pre_alarm
   
   if event_type in CREATE_SET:
      created[(s.get_pid(), o.get_name())] = True  

   if event_type in EXECVE_SET:
      if (isTRUSTED(citag(alarmarg.origtags)) and isUNTRUSTED(citag(s.tags()))):
         if (alarms[(s.get_pid(), o.get_name())]==False):
            alarm_sum[1] = alarm_sum[1] + 1
         alarm_result = prtSOAlarm(ts,"FileExec", s, o, alarms, event['uuid'], alarm_file)

   if event_type in LOAD_SET:
      if o.isFile():
         if (isTRUSTED(citag(alarmarg.origtags)) and isUNTRUSTED(citag(s.tags()))):
            if not alarms[(s.get_pid(), o.get_name())]:
               alarm_sum[1] = alarm_sum[1] + 1
            alarm_result = prtSOAlarm(ts,"FileExec", s, o, alarms, event['uuid'], alarm_file)

   if event_type in INJECT_SET:
      if (isTRUSTED(citag(alarmarg.origtags)) and isUNTRUSTED(citag(o.tags()))):
         alarm_result = prtSSAlarm(ts,"Inject", s, o,event['uuid'], alarm_file)
         alarm_sum[1] = alarm_sum[1] + 1
   
   if event_type in WRITE_SET:
      # if s.id == '37B8D23F-E214-B0B7-C35F-4CEFE9407660':
      #    stop = 1
      if (not o.isIP() and not o.isMatch("UnknownObject") and not o.isMatch("Pipe\[") and not o.isMatch("pipe") and not o.isMatch("null") and itag(alarmarg.origtags) > 0.5 and itag(o.tags()) <= 0.5):
         if not created.get((s.get_pid(), o.get_name()), False):
            if not alarms[(s.get_pid(), o.get_name())]:
               alarm_sum[1] = alarm_sum[1] + 1
            alarm_result = prtSOAlarm(ts, "FileCorruption", s, o, alarms, event['uuid'], alarm_file)

      if (itag(s.tags()) < 0.5 and ctag(s.tags()) < 0.5):
         if (o.isIP() and itag(o.tags()) < 0.5):
            if not alarms[(s.get_pid(), o.get_name())]:
               alarm_sum[1] = alarm_sum[1] + 1
            alarm_result = prtSOAlarm(ts, "DataLeak", s, o, alarms, event['uuid'], alarm_file)
   
   
   #    setuid(s, _, ts) --> {
   #       if (itag(subjTags(s)) < 128 && !rootprinc) {
   #          if (isRoot(sowner(s))) {
   #             prtSAlarm(ts, "PrivilegeEscalation", s)
   #             talarms = talarms + 1
   #    }
   #       }
   #    }
   if event_type in SET_UID_SET:
      if itag(s.tags()) < 0.5 and alarmarg.rootprinc == False:
         if isRoot(morse.Principals[o.owner]):
            alarm_result = prtSAlarm(ts, "PrivilegeEscalation", s, event['uuid'], alarm_file)
            alarm_sum[1] = alarm_sum[1] + 1
   

   #    mprotect(s, o, p, ts) --> {
   #       unsigned it = itag(subjTags(s))
   #       unsigned prm = permbits(p)
      
   #       if (it < 128 && ((prm & 0100) == 0100)) {
   #    if (!alarms[(pid(s), name(o))]) talarms = talarms + 1
   #          prtSOAlarm(ts, "MkMemExecutable", s, o, alarms)
   #       }
   #    }
   
   if event_type in MPROTECT_SET:
      it = itag(s.tags())
      # prm = permbits(event)
      prm = int(event['properties']['map']['protection'])
      # print(event['properties']['map']['protection'])

      if o.isFile() == False:
         if (it < 0.5 and ((prm & int('01',8)) == int('01',8))):
            if not alarms[(s.get_pid(), o.get_name())]:
               alarm_sum[1] = alarm_sum[1] + 1
            alarm_result = prtSOAlarm(ts, "MkMemExecutable", s, o, alarms, event['uuid'], alarm_file)
   
   

   # open(s, _, _, ts) \/ close(s, _, ts) \/ chown_pre(s, _, _, ts) \/
   #    chmod(s, _, _, ts) \/ mprotect(s, _, _, ts) \/ mmap_pre(s, _, _, ts) \/
   #    remove_pre(s, _, ts) \/ rename_pre(s, _, _, _, ts) \/ clone(s, _, _, ts) \/
   #    read(s, _, _, _, ts) \/ load(s, _, _, _, ts) \/ execve(s, _, _, ts) \/
   #    inject(s, _, _, ts) \/ setuid(s, _, ts) \/ create(s, _, ts) \/ 
   #    write(s, _, _, _, ts)  --> {
   #    if (start_ts == 0) start_ts = ts
   #    else if (ts - start_ts >= 3600000000) {
   #       start_ts = ts
   #       print("Total Alarms: ", talarms)
   #       talarms = 0
   #    }
   
   # if 0 <= event_type < len(standard_events):
   #    if alarm_sum[0] == 0:
   #       alarm_sum[0] = ts
   #    elif ts - alarm_sum[0] >= 3600000000:
   #       alarm_sum[0] = ts
   #       print("Total Alarms: ", alarm_sum[1])
   #       alarm_sum[1] = 0

   return alarm_result