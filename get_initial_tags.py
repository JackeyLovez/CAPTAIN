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
# from policy.initTagsAT import get_object_feature, get_subject_feature
import sys
import tqdm
import time
import pandas as pd
from model.morse import Morse
from utils.Initializer import Initializer, FileObj_Initializer, NetFlowObj_Initializer
import numpy as np
from pathlib import Path
import pickle


def start_experiment(config):
    args = config
    experiment = None
    experiment = Experiment(args['trained_model_timestamp'], args, args['experiment_prefix'])
    experiment.results_path = args['result_path']

    # ============= Tag Initializer =============== #
    node_inits = experiment.load_model()

    model_nids = {}
    model_tags = {}
    model_features = {}
    for node_type in ['NetFlowObject','SrcSinkObject','UnnamedPipeObject','MemoryObject','PacketSocketObject','RegistryKeyObject']:
        with open(os.path.join(args['feature_path'],'{}.json'.format(node_type)),'r') as fin:
            node_features = json.load(fin)
        if len(node_features) > 0:
            target_features = pd.DataFrame.from_dict(node_features,orient='index')
            model_nids[node_type] = target_features.index.tolist()
            feature_array = target_features['features'].values.tolist()
        else:
            model_nids[node_type] = []
            feature_array = []
        model_features[node_type] = torch.tensor(feature_array, dtype=torch.int64)
        model_tags[node_type] = node_inits[node_type].initialize(model_features[node_type]).squeeze()

    for node_type in ['FileObject']:
        with open(os.path.join(args['feature_path'],'{}.json'.format(node_type)),'r') as fin:
            node_features = json.load(fin)
        if len(node_features) > 0:
            target_features = pd.DataFrame.from_dict(node_features,orient='index')
            model_nids[node_type] = target_features.index.tolist()
            ori_feature_array = target_features['features'].values.tolist()
            oh_index = [item[0] for item in ori_feature_array]
            feature_array = []
            for i, item in enumerate(ori_feature_array):
                feature_array.append(np.zeros(2002))
                feature_array[-1][oh_index[i]] = 1
                feature_array[-1][2000] = item[1]
                feature_array[-1][2001] = item[2]
        else:
            model_nids[node_type] = []
            feature_array = []
        model_features[node_type] = torch.tensor(feature_array, dtype=torch.int64)
        model_tags[node_type] = node_inits[node_type].initialize(model_features[node_type]).squeeze()

    return None



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="train or test the model")
    parser.add_argument("--feature_path", default='/home/weijian/weijian/projects/ATPG/results/features/feature_vectors', type=str)
    parser.add_argument("--device", nargs='?', default="cuda", type=str)
    # parser.add_argument("--train_data", nargs='?', default="/root/Downloads/ta1-trace-e3-official-1.json", type=str)
    parser.add_argument("--mode", nargs="?", default="train", type=str)
    parser.add_argument("--trained_model_timestamp", nargs="?", default=None, type=str)
    parser.add_argument("--data_tag", default="traindata1", type=str)
    parser.add_argument("--experiment_prefix", default="groupF", type=str)
    parser.add_argument("--result_path", default="groupF", type=str)

    args = parser.parse_args()

    config = {
        "learning_rate": args.learning_rate,
        # "train_data": args.train_data,
        "mode": args.mode,
        "device": args.device,
        "feature_path": args.feature_path,
        "data_tag": args.data_tag,
        "experiment_prefix": args.experiment_prefix,
        "result_path": args.result_path
    }

    start_experiment(config)

