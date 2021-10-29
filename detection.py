from parse.eventParsing import parse_event
from parse.nodeParsing import parse_subject, parse_object
from parse.lttng.recordParsing import read_lttng_record
import re
import sys
import os
import tqdm
import json
from datetime import *
from morse import Morse

def parse_logs(file):
    null = 0
    mo = Morse()
    data_line = 0
    last_time = 0
    for i in range(7):
        with open(file+'.'+str(i),'r') as fin:
            # for line in tqdm.tqdm(fin):
            for line in fin:
                data_line += 1
                if data_line % 100000 == 0:
                    print("Morse has parsed {} lines.".format(data_line))

                record_datum = eval(line)['datum']
                record_type = list(record_datum.keys())
                assert len(record_type)==1
                record_datum = record_datum[record_type[0]]
                record_type = record_type[0].split('.')[-1]
                if record_type == 'Event':
                    # if record_datum['timestampNanos'] < last_time:
                    #     a = 0
                    # else:
                    #     last_time = record_datum['timestampNanos']
                    event = parse_event(record_datum)
                    mo.add_event(event)
                elif record_type == 'Subject':
                    subject_node, subject = parse_subject(record_datum)
                    mo.add_subject(subject)
                elif record_type == 'TimeMarker':
                    b = 0
                elif record_type == 'StartMarker':
                    b = 0
                elif record_type == 'UnitDependency':
                    b = 0
                elif record_type == 'Host':
                    b = 0
                elif record_type == 'Principal':
                    mo.Principals[record_datum['uuid']] = record_datum
                elif record_type.endswith('Object'):
                    object_node, object = parse_object(record_datum, record_type)
                    mo.add_object(object)
                else:
                    pass



def parse_lttng_logs(file):
    null = 0
    mo = Morse(format='lttng')
    log_types = set()
    event_types = set()
    with open(file,'r') as fin:
        for line in tqdm.tqdm(fin):
            if line[:4] == "data":
                record = read_lttng_record(fin)
            if record.type == 1:
                #edge data
                event = parse_event(record,format='lttng')
                event_types.add(event['type'])
                mo.add_event(event)
            elif record.type == -1:
                #node data
                if record.subtype == 5:
                    # process node
                    if len(record.params)>0:
                        subject_node, subject = parse_subject(record, format='lttng')
                        # print(subject.cmdLine)
                        mo.add_subject(subject)
                elif 0 < record.subtype < 5:
                    # non-common file node
                    object_node, object = parse_object(record, record.subtype, format='lttng')
                    mo.add_object(object)
                elif record.subtype == -1:
                    # common file node
                    object_node, object = parse_object(record, 0, format='lttng')
                    mo.add_object(object)
            else:
                pass

    return log_types


if __name__ == '__main__':
    file = '/Users/lexus/Documents/research/APT/Data/E3/ta1-trace-e3-official-1.json/ta1-trace-e3-official-1.json'
    parse_logs(file)
    # file = '/Users/lexus/Documents/research/APT/Data/lttng/reverseshell_debug.out'
    # parse_lttng_logs(file)
    
    
