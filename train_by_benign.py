import json
import torch
import logging
from datetime import datetime
import pdb
import os
import argparse
import time
from utils.utils import *
from collections import Counter
from utils.eventClassifier import eventClassifier
from model.morse import Morse

import tqdm
import time
import pandas as pd
from model.morse import Morse
from utils.graph_detection import add_nodes_to_graph
from utils.graphLoader import read_events_from_files
import numpy as np
from pathlib import Path
import pickle

def start_experiment(args):
    experiment = Experiment(time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()), args, args.experiment_prefix)
    mode = args.mode
    mo = Morse()

    # ============= Tag Initializer =============== #
    node_inits = {}

    if (mode == "train"):
        logging.basicConfig(level=logging.INFO,
                            filename='debug.log',
                            filemode='w+',
                            format='%(asctime)s %(levelname)s:%(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
        epochs = args.epoch

        # load the checkpoint if it is given
        if args.checkpoint:
            checkpoint_epoch_path = args.checkpoint
            node_inits = experiment.load_checkpoint(node_inits, checkpoint_epoch_path)

        # ================= Load all nodes & edges to memory ==================== #
        pre_loaded_path = experiment.get_pre_load_morse(args.data_tag)

        if pre_loaded_path.endswith('.pkl'):
            with open(pre_loaded_path, 'rb') as f:
                events, nodes, principals = pickle.load(f)
        else:
            events = read_events_from_files(os.path.join(args.train_data, 'edges.json'), args.time_range)
            nodes = pd.read_json(os.path.join(args.train_data, 'nodes.json'), lines=True).set_index('id').to_dict(orient='index')
            principals = pd.read_json(os.path.join(args.train_data, 'principals.json'), lines=True).set_index('uuid').to_dict(orient='index')
            # cache the loaded morse and events for next run
            with open(os.path.join(pre_loaded_path, 'morse.pkl'), "wb") as f:
                pickle.dump([events, nodes, principals], f)

        # #edge tuning cadets
        # mo.white_name_set = {'207.46.73.59', '127.0.0.1', '128.55.12.10', '128.55.12.118', '83.150.97.73', '128.55.12.67', '216.87.162.115', '128.55.12.55', '207.25.80.123', '10.0.6.9', '128.55.12.166', '69.20.49.234', '128.55.12.167', '207.46.73.60', '212.60.66.243', '193.40.5.73', '128.55.12.110', '212.190.125.38', '162.99.3.50', '194.90.181.242', '66.252.21.131', '128.55.12.56'}
        # #edge tuning trace
        # mo.white_name_set = {'128.55.12.73', '128.55.12.10', '158.28.238.9', '64.86.71.27', '204.2.179.67', '8.15.32.34', '64.4.125.136', '10.0.4.1', '83.222.15.109', '216.163.248.17', '64.191.208.114', '12.149.161.245', '208.17.90.10', '67.28.122.168', '128.55.12.122', '209.132.177.50', '66.252.21.131', '65.214.39.18', '129.33.46.231', '162.97.114.199', '216.9.245.101', '203.192.141.18', '208.75.170.1', '0.0.0.0'}
        mo.Principals = principals
        for epoch in range(epochs):
            print('epoch: {}'.format(epoch))
            Path(os.path.join(experiment.get_experiment_output_path(), 'alarms')).mkdir(parents=True, exist_ok=True)
            mo.alarm_file = open(os.path.join(experiment.get_experiment_output_path(), 'alarms/alarms-epoch-{}.txt'.format(epoch)),'a')
            mo.reset_morse()
            mo.reset_tags()

            # ============= Dectection =================== #
            node_gradients = []
            propagation_chains = []
            for event in tqdm.tqdm(events):
                if event.type == 'UPDATE':
                    try:
                        if 'exec' in event.value:
                            mo.Nodes[event.nid].processName = event.value['exec']
                        elif 'name' in event.value:
                            mo.Nodes[event.nid].name = event.value['name']
                            mo.Nodes[event.nid].path = event.value['name']
                        elif 'cmdl' in event.value:
                            mo.Nodes[event.nid].cmdLine = event.value['cmdl']
                    except KeyError:
                        pass
                    continue
                if event.src not in mo.Nodes:
                    add_nodes_to_graph(mo, event.src, nodes[event.src])

                if isinstance(event.dest, int) and event.dest not in mo.Nodes:
                    add_nodes_to_graph(mo, event.dest, nodes[event.dest])

                if isinstance(event.dest2, int) and event.dest2 not in mo.Nodes:
                    add_nodes_to_graph(mo, event.dest2, nodes[event.dest2])

                diagnosis, s_labels, o_labels, pc = mo.add_event_generate_loss(event, None)
                experiment.update_metrics(diagnosis, None)

                if diagnosis == None:
                    continue

                if s_labels:
                    node_gradients.extend(s_labels)

                if o_labels:
                    node_gradients.extend(o_labels)

                propagation_chains.extend(pc)
            
            mo.alarm_file.close()
            experiment.print_metrics()
            experiment.save_metrics()
            experiment.reset_metrics()

            pc_event_counter = Counter()
            for item in propagation_chains:
                pc_event_counter.update(item)

            benign_nid_labels = {}
            public_nid_labels = {}
            for item in node_gradients:
                if item[0][1] == 'i':
                    if item[0] not in benign_nid_labels:
                        benign_nid_labels[item[0]] = []
                    benign_nid_labels[item[0]].append(item[1])
                elif item[0][1] == 'c':
                    if item[0] not in public_nid_labels:
                        public_nid_labels[item[0]] = []
                    public_nid_labels[item[0]].append(item[1])
                
            benign_node_dict = {}
            for node, value in benign_nid_labels.items():
                if mo.Nodes[node[0]].get_name() not in benign_node_dict:
                    benign_node_dict[mo.Nodes[node[0]].get_name()] = []
                benign_node_dict[mo.Nodes[node[0]].get_name()].extend(value)

            public_node_dict = {}
            for node, value in public_nid_labels.items():
                if mo.Nodes[node[0]].get_name() not in public_node_dict:
                    public_node_dict[mo.Nodes[node[0]].get_name()] = []
                public_node_dict[mo.Nodes[node[0]].get_name()].extend(value)

            pdb.set_trace()

            for key, item in benign_node_dict.items():
                if len(item) > 10 and sum(item)/len(item) > 0.9:
                    mo.white_name_set.add(key)
            
            print(mo.white_name_set)

    elif (mode == "test"):
        begin_time = time.time()
        experiment = Experiment(time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()), args, args.experiment_prefix)
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

        # ================= Load all nodes & edges to memory ==================== #
        pre_loaded_path = experiment.get_pre_load_morse(args.data_tag)

        if pre_loaded_path.endswith('.pkl'):
            with open(pre_loaded_path, 'rb') as f:
                events, nodes, princicals = pickle.load(f)
        else:
            events = read_events_from_files(os.path.join(args.train_data, 'edges.json'), args.time_range)
            nodes = pd.read_json(os.path.join(args.train_data, 'nodes.json'), lines=True).set_index('id').to_dict(orient='index')
            princicals = pd.read_json(os.path.join(args.train_data, 'principals.json'), lines=True).set_index('uuid').to_dict(orient='index')
            # cache the loaded morse and events for next run
            with open(os.path.join(pre_loaded_path, 'morse.pkl'), "wb") as f:
                pickle.dump([events, nodes, princicals], f)

        mo.Principals = princicals
        # # Cadets
        # mo.white_name_set = {'207.46.73.59', '127.0.0.1', '128.55.12.10', '128.55.12.118', '83.150.97.73', '128.55.12.67', '216.87.162.115', '128.55.12.55', '207.25.80.123', '10.0.6.9', '128.55.12.166', '69.20.49.234', '128.55.12.167', '207.46.73.60', '212.60.66.243', '193.40.5.73', '128.55.12.110', '212.190.125.38', '162.99.3.50', '194.90.181.242', '66.252.21.131', '128.55.12.56'}
        # Trace
        # mo.white_name_set = {'128.55.12.73', '128.55.12.10', '158.28.238.9', '64.86.71.27', '204.2.179.67', '8.15.32.34', '64.4.125.136', '10.0.4.1', '83.222.15.109', '216.163.248.17', '64.191.208.114', '12.149.161.245', '208.17.90.10', '67.28.122.168', '128.55.12.122', '209.132.177.50', '66.252.21.131', '65.214.39.18', '129.33.46.231', '162.97.114.199', '216.9.245.101', '203.192.141.18', '208.75.170.1', '0.0.0.0'}
        
        # Linux L11
        mo.white_name_set = {'/usr/libexec/grepconf.sh'}
        
        # # Linux L12
        # mo.white_name_set = {'192.168.20.56', '18.225.36.18', '61.75.63.184', '/tmp/atScript/atomic-red-team-Gray_dev1.0/execution-frameworks/contrib/python/Python-3.5.0/conftest', '/data/cs/opt/script/check_service.sh', '/usr/libexec/grepconf.sh'}

        # # Linux L13
        # mo.white_name_set = {'/usr/libexec/grepconf.sh', '/opt/threatbook/OneAV/oneav/script/install/oneav_service_monitor.sh', '/titan/agent/diag_agent.sh'}

        false_alarms = []
        for event in tqdm.tqdm(events):
            if event.type == 'UPDATE':
                try:
                    if 'exec' in event.value:
                        mo.Nodes[event.nid].processName = event.value['exec']
                    elif 'name' in event.value:
                        mo.Nodes[event.nid].name = event.value['name']
                        mo.Nodes[event.nid].path = event.value['name']
                    elif 'cmdl' in event.value:
                        mo.Nodes[event.nid].cmdLine = event.value['cmdl']
                except KeyError:
                    pass
                continue
                
            if event.src not in mo.Nodes:
                add_nodes_to_graph(mo, event.src, nodes[event.src])

            if isinstance(event.dest, int) and event.dest not in mo.Nodes:
                add_nodes_to_graph(mo, event.dest, nodes[event.dest])

            if isinstance(event.dest2, int) and event.dest2 not in mo.Nodes:
                add_nodes_to_graph(mo, event.dest2, nodes[event.dest2])

            gt = ec.classify(event.id)
            diagnosis = mo.add_event(event, gt)
            experiment.update_metrics(diagnosis, gt)
            # if gt != None and diagnosis == None:
            #     print(event.id)
            if gt == None and diagnosis != None:
                false_alarms.append(diagnosis)
                        
        mo.alarm_file.close()
        experiment.print_metrics()
        experiment.save_metrics()
        ec.analyzeFile(open(os.path.join(experiment.get_experiment_output_path(), 'alarms/alarms-in-test.txt'),'r'))
        ec.summary(os.path.join(experiment.metric_path, "ec_summary_test.txt"))

        print(Counter(false_alarms))

        print("Detecting Time: {:.2f}s".format(time.time()-begin_time))
        print("Metrics saved in {}".format(experiment.get_experiment_output_path()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="train or test the model")
    parser.add_argument("--ground_truth_file", type=str)
    parser.add_argument("--train_data", type=str)
    parser.add_argument("--test_data", type=str)
    parser.add_argument("--epoch", default=100, type=int)
    parser.add_argument("--mode", type=str)
    parser.add_argument("--data_tag", type=str)
    parser.add_argument("--experiment_prefix", type=str)
    parser.add_argument("--checkpoint", type=str)
    parser.add_argument("--time_range", nargs=2, type=str, default = None)

    args = parser.parse_args()
    if args.time_range:
        args.time_range[0] = (datetime.timestamp(datetime.strptime(args.time_range[0], '%Y-%m-%dT%H:%M:%S%z')))*1e9
        args.time_range[1] = (datetime.timestamp(datetime.strptime(args.time_range[1], '%Y-%m-%dT%H:%M:%S%z')))*1e9

    start_experiment(args)

