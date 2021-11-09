import json
import torch
import logging
import argparse
import time
from utils.utils import *
from model.loss import get_loss
from utils.eventClassifier import eventClassifier
from model.morse import Morse
from collections import defaultdict

from numpy import gradient, record
from parse.eventParsing import parse_event
from parse.nodeParsing import parse_subject, parse_object
from parse.lttng.recordParsing import read_lttng_record
from policy.initTagsAT import get_object_feature, get_subject_feature
import sys
import tqdm
import time
import pandas as pd
from model.morse import Morse
from utils.Initializer import Initializer, FileObj_Initializer, NetFlowObj_Initializer
import numpy as np
from pathlib import Path
import pickle
import ray
from ray import tune


def start_experiment(config):
    args = config
    experiment = None
    if args['mode'] == "train":
        experiment = Experiment(str(int(time.time())), args, args['experiment_prefix'])
    else:
        experiment = Experiment(args['trained_model_timestamp'], args, args['experiment_prefix'])

    learning_rate = args['learning_rate']
    if torch.cuda.is_available():
        device = torch.device("cuda:0")
    epochs = args['epoch']
    mode = args['mode']

    mo = Morse()

    # ============= Tag Initializer =============== #
    node_inits = {}
    node_inits['Subject'] = Initializer(1,5)
    node_inits['NetFlowObject'] = Initializer(1,2)
    node_inits['SrcSinkObject'] = Initializer(111,2)
    node_inits['FileObject'] = FileObj_Initializer(2)
    node_inits['UnnamedPipeObject'] = Initializer(1,2)
    node_inits['MemoryObject'] = Initializer(1,2)
    node_inits['PacketSocketObject'] = Initializer(1,2)
    node_inits['RegistryKeyObject'] = Initializer(1,2)
    mo.subj_init = node_inits['Subject']
    mo.obj_inits = node_inits

    # ============= Groud Truth & Optimizers ====================#
    optimizers = {}
    for key in node_inits.keys():
        optimizers[key] = torch.optim.RMSprop(node_inits[key].parameters(), lr=learning_rate)

    if (mode == "train"):
        logging.basicConfig(level=logging.INFO,
                            filename='debug.log',
                            filemode='w+',
                            format='%(asctime)s %(levelname)s:%(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
        experiment.save_hyperparameters()

        # ================= Load all nodes & edges to memory ==================== #
        pre_loaded_path = experiment.get_pre_load_morse(args['data_tag'])

        if pre_loaded_path.endswith('.pkl'):
            with open(pre_loaded_path, 'rb') as f:
                events, mo = pickle.load(f)
        else:
            events = []
            loaded_line = 0
            for i in range(7):
                with open(args['train_data']+'.'+str(i),'r') as fin:
                    for line in fin:
                        loaded_line += 1
                        if loaded_line % 100000 == 0:
                            print("Morse has loaded {} lines.".format(loaded_line))
                        record_datum = json.loads(line)['datum']
                        record_type = list(record_datum.keys())
                        assert len(record_type)==1
                        record_datum = record_datum[record_type[0]]
                        record_type = record_type[0].split('.')[-1]
                        if record_type == 'Event':
                            event = parse_event(record_datum)
                            events.append((record_datum['uuid'],event))
                        elif record_type == 'Subject':
                            subject_node, subject = parse_subject(record_datum)
                            mo.add_subject(subject)
                        elif record_type == 'Principal':
                            mo.Principals[record_datum['uuid']] = record_datum
                        elif record_type.endswith('Object'):
                            object_node, object = parse_object(record_datum, record_type)
                            mo.add_object(object)
                        elif record_type == 'TimeMarker':
                            pass
                        elif record_type == 'StartMarker':
                            pass
                        elif record_type == 'UnitDependency':
                            pass
                        elif record_type == 'Host':
                            pass
                        else:
                            pass
            # cache the loaded morse and events for next run
            with open(os.path.join(pre_loaded_path, 'morse.pkl'), "wb") as f:
                pickle.dump([events, mo], f)

        with open(args['feature_path'],'r') as fin:
            node_features = json.load(fin)
        df = pd.DataFrame.from_dict(node_features,orient='index')

        model_nids = {}
        model_features = {}
        for node_type in ['NetFlowObject','SrcSinkObject','FileObject','UnnamedPipeObject','MemoryObject','PacketSocketObject','RegistryKeyObject','Subject']:
            target_features = df[df['type']==node_type]
            model_nids[node_type] = target_features.index.tolist()
            if node_type == 'Subject':
                feature_array = [[0] for i in range(len(target_features))]
            else:
                feature_array = target_features['features'].values.tolist()
            model_features[node_type] = torch.tensor(feature_array, dtype=torch.int64)


        ec = eventClassifier(args['ground_truth_file'])

        for epoch in range(epochs):
            print('epoch: {}'.format(epoch))
            # ============== Initialization ================== #
            model_tags = {}
            node_inital_tags = {}

            for node_type in ['NetFlowObject','SrcSinkObject','FileObject','UnnamedPipeObject','MemoryObject','PacketSocketObject','RegistryKeyObject','Subject']:
                model_tags[node_type] = node_inits[node_type].initialize(model_features[node_type]).squeeze()
                for i, node_id in enumerate(model_nids[node_type]):
                    node_inital_tags[node_id] = model_tags[node_type][i,:]
            
            mo.node_inital_tags = node_inital_tags
            mo.reset_tags()

            # ============= Dectection =================== #
            node_gradients = {}
            mo.alarm_file = os.path.join(experiment.get_experiment_output_path(), 'alarms/alarms-epoch-{}.txt'.format(epoch))
            Path(os.path.join(experiment.get_experiment_output_path(), 'alarms')).mkdir(parents=True, exist_ok=True)
            for event_info in tqdm.tqdm(events):
                event_id = event_info[0]
                event = event_info[1]
                diagnois = mo.add_event(event)
                gt = ec.classify(event_id)
                s = torch.tensor(mo.Nodes[event['src']].tags(),requires_grad=True)
                o = torch.tensor(mo.Nodes[event['dest']].tags(),requires_grad=True)
                needs_to_update = False
                is_fp = False

                print("updating metrics")
                if epoch == epochs - 1:
                    experiment.update_metrics(diagnois, gt)
                if diagnois is None:
                    # check if it's fn
                    if gt is not None:
                        s_loss, o_loss = get_loss(event['type'], s, o, gt, 'false_negative')
                        # if np.random.uniform(0, 100, 1) == 1:
                        needs_to_update = True
                else:
                    # check if it's fp
                    if gt is None:
                        s_loss, o_loss = get_loss(event['type'], s, o, diagnois, 'false_positive')
                        needs_to_update = True
                        is_fp = True
                
                if needs_to_update:
                    s_loss.backward()
                    o_loss.backward()

                    if is_fp:
                        a = args['lr_imb']
                    else:
                        a = 1

                    # for key in optimizers.keys():
                    #     optimizers[key].zero_grad()

                    s_init_id = mo.Nodes[event['src']].getInitID()
                    s_morse_grads = mo.Nodes[event['src']].get_grad()
                    o_init_id = mo.Nodes[event['dest']].getInitID()
                    o_morse_grads = mo.Nodes[event['dest']].get_grad()
                    nodes_need_updated = {}
                    if s.grad != None:
                        for i, node_id in enumerate(s_init_id):
                            if node_id not in nodes_need_updated:
                                nodes_need_updated[node_id] = torch.zeros(5)
                            nodes_need_updated[node_id][i] += s.grad[i]*s_morse_grads[i]*a

                    if o.grad != None:
                        for i, node_id in enumerate(o_init_id):
                            if node_id not in nodes_need_updated:
                                nodes_need_updated[node_id] = torch.zeros(5)
                            nodes_need_updated[node_id][i] += o.grad[i]*o_morse_grads[i]*a

                    for nid in nodes_need_updated.keys():
                        if nid not in node_gradients:
                            node_gradients[nid] = []
                        node_gradients[nid].append(nodes_need_updated[nid].unsqueeze(0))

            for nid in list(node_gradients.keys()):
                node_gradients[nid] = torch.mean(torch.cat(node_gradients[nid],0), dim=0)
            
            for node_type in ['NetFlowObject','SrcSinkObject','FileObject','UnnamedPipeObject','MemoryObject','PacketSocketObject','RegistryKeyObject','Subject']:
                gradients = []
                for nid in model_nids[node_type]:
                    if nid in node_gradients:
                        gradients.append(node_gradients[nid].unsqueeze(0))
                    else:
                        gradients.append(torch.zeros(5).unsqueeze(0))
                if len(gradients) > 0:
                    gradients = torch.cat(gradients, 0)
                    optimizers[node_type].zero_grad()
                    if node_type == 'Subject':
                        model_tags[node_type].backward(gradient=gradients, retain_graph=True)
                    else:
                        model_tags[node_type].backward(gradient=gradients[:,-2:], retain_graph=True)
                    optimizers[node_type].step()

        experiment.save_model(node_inits)
        # final_metrics = experiment.get_f1_score()
        experiment.save_metrics()

        return None

    elif (mode == "test"):

        # load pytorch model
        model = experiment.load_model()
        experiment.save_hyperparameters()

        # pytorch model testing code goes here
        # ...
        pred_result = None




        # precision, recall, accuracy, f1 = experiment.evaluate_classification(pred_result)
        # save_evaluation_results(precision, recall, accuracy, f1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="train or test the model")
    parser.add_argument("--feature_path", default='/home/weijian/weijian/projects/ATPG/results/features/features.json', type=str)
    parser.add_argument("--ground_truth_file", default='/home/weijian/weijian/projects/ATPG/groundTruth.txt', type=str)
    parser.add_argument("--batch_size", nargs='?', default=5, type=int)
    parser.add_argument("--epoch", default=100, type=int)
    parser.add_argument("--learning_rate", nargs='?', default=0.001, type=float)
    parser.add_argument("--feature_dimension", nargs='?', default=12, type=int)
    parser.add_argument("--device", nargs='?', default="cuda", type=str)
    parser.add_argument("--train_data", nargs='?', default="/root/Downloads/ta1-trace-e3-official-1.json", type=str)
    parser.add_argument("--validation_data", nargs='?', default="EventData/north_korea_apt_attack_data_debug.out", type=str)
    parser.add_argument("--mode", nargs="?", default="train", type=str)
    parser.add_argument("--trained_model_timestamp", nargs="?", default=None, type=str)
    parser.add_argument("--lr_imb", type=int)

    args = parser.parse_args()

    config = {
        "learning_rate": args.learning_rate,
        "epoch": args.epoch,
        "lr_imb": args.lr_imb,
        "train_data": args.train_data,
        "mode": args.mode,
        "device": args.device,
        "ground_truth_file": args.ground_truth_file,
        "feature_path": args.feature_path,
        "data_tag": "traindata1",
        "experiment_prefix": "groupA"
    }

    start_experiment(config)

