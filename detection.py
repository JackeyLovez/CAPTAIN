import json
import logging
import os
import gc
import argparse
import time
from graph.Subject import Subject
from utils.utils import *
from utils.eventClassifier import eventClassifier
from model.morse import Morse
from collections import defaultdict

from numpy import gradient, record
import sys
import tqdm
import time
import pandas as pd
from model.morse import Morse
from parse.eventType import lttng_events, cdm_events, standard_events
from graph.Event import Event
from graph.Subject import Subject
from graph.Object import Object
from utils.graph_detection import add_nodes_to_graph
import numpy as np
from pathlib import Path
import pickle

def start_experiment(args):
    begin_time = time.time()
    # format = 'cadets'
    # cdm_version = 18
    experiment = Experiment(time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()), args, args.experiment_prefix)

    mo = Morse()

    print("Begin preparing testing...")
    logging.basicConfig(level=logging.INFO,
                        filename='debug.log',
                        filemode='w+',
                        format='%(asctime)s %(levelname)s:%(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')
    experiment.save_hyperparameters()
    ec = eventClassifier(args.ground_truth_file)
        
    mo.node_inital_tags = {}
    Path(os.path.join(experiment.get_experiment_output_path(), 'alarms')).mkdir(parents=True, exist_ok=True)
    mo.alarm_file = open(os.path.join(experiment.get_experiment_output_path(), 'alarms/alarms-in-test.txt'), 'a')

    # a = [json.loads(i) for i in open(, 'r').readlines()]
    nodes = pd.read_json(os.path.join(args.test_data, 'nodes.json'), lines=True).set_index('id').to_dict(orient='index')
    princicals = pd.read_json(os.path.join(args.test_data, 'principals.json'), lines=True).set_index('uuid').to_dict(orient='index')
    mo.Principals = princicals

    loaded_line = 0
    edge_file = os.path.join(args.test_data, 'edges.json')

    # close interval
    if args.line_range:
        l_range = args.line_range[0]
        r_range = args.line_range[1]
    else:
        l_range = 0
        r_range = 1e20

    with open(edge_file, 'r') as fin:
        for line in fin:
            if loaded_line > r_range:
                break
            loaded_line += 1
            if loaded_line % 100000 == 0:
                print("Morse has loaded {} lines.".format(loaded_line))
            event = Event(None, None)
            event.loads(line)

            if loaded_line < l_range:
                continue

            if event.src not in mo.Nodes:
                assert nodes[event.src]['type'] == 'SUBJECT_PROCESS'
                add_nodes_to_graph(mo, event.src, nodes[event.src], generate_tags=True)

            if isinstance(event.dest, int) and event.dest not in mo.Nodes:
                add_nodes_to_graph(mo, event.dest, nodes[event.dest], generate_tags=True)

            if isinstance(event.dest2, int) and event.dest2 not in mo.Nodes:
                add_nodes_to_graph(mo, event.dest2, nodes[event.dest2], generate_tags=True)

            gt = ec.classify(event.id)
            diagnois = mo.add_event(event, gt)
            experiment.update_metrics(diagnois, gt)
            if gt != None and diagnois == None:
                print(event.id)
                    
    mo.alarm_file.close()
    experiment.print_metrics()
    experiment.save_metrics()
    ec.analyzeFile(open(os.path.join(experiment.get_experiment_output_path(), 'alarms/alarms-in-test.txt'),'r'))
    ec.summary(os.path.join(experiment.metric_path, "ec_summary_test.txt"))

    print(time.time()-begin_time)

    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="train or test the model")
    parser.add_argument("--ground_truth_file", type=str)
    parser.add_argument("--test_data", nargs='?', type=str)
    parser.add_argument("--experiment_prefix", type=str)
    parser.add_argument("--line_range", nargs=2, type=int)
    parser.add_argument("--mode", type=str, default='test')

    args = parser.parse_args()

    start_experiment(args)

