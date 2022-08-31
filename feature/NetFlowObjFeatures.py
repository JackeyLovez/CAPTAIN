from collections import Counter
import json
import pandas as pd
import numpy as np
import ipaddress
import math
import tqdm
import os

def ipaddr_to_list(ipaddr):
    result = []
    default_ipv4 = list(-1*np.ones(32, dtype=int))
    default_ipv6 = list(-1*np.ones(128, dtype=int))
    if ipaddr.version == 4:
        bit_len = 32
    elif ipaddr.version == 6:
        bit_len = 128
    dec_ip = int(ipaddr)
    while dec_ip > 0:
        result.append(dec_ip%2)
        dec_ip = math.floor(dec_ip/2)
    result.extend(list(np.zeros(bit_len-len(result))))
    assert len(result) == bit_len
    
    return_res = []
    if ipaddr.version == 4:
        return_res.extend(result)
        return_res.extend(default_ipv6)
    elif ipaddr.version == 6:
        return_res.extend(default_ipv4)
        return_res.extend(result)

    return_res.extend([int(flag) for flag in [ipaddr.is_global, ipaddr.is_link_local, ipaddr.is_loopback, ipaddr.is_multicast, ipaddr.is_private, ipaddr.is_reserved, ipaddr.is_unspecified]])
    
    return return_res

def main():
    feature_path = 'results/features/E31-trace/NetFlowObject.json'
    vector_dir = 'results/features/E31-trace/feature_vectors/'

    with open(feature_path,'r') as fin:
        node_features = json.load(fin)

    # df = pd.DataFrame.from_dict(node_features,orient='index')
    # a = dict(Counter(df['remotePort'].tolist()))
    # b = sorted(a.items(),key= lambda x: x[1], reverse=True)

    node_type = 'NetFlowObject'

    # TCP is 1; UDP is 0
    protocol_map = {17:0,6:1}

    # Unknown IP
    unknownip = [-1 for i in range(167)]

    # Port type
    '''
    21: ftp
    22: ssh
    25: smtp Simple Mail Transfer
    53: domain DNS
    67: bootps Bootstrap Protocol Server
    80: www-http
    123: ntp Network Time Protocol
    143: imap Internet Messafe Access Protocol
    443: https
    5353: mdns Multicast DNS
    '''
    port_type = {21:1, 22:2, 25:3, 53:4, 67:5, 80:6, 123:7, 143:8, 443:9, 5353:10}

    nodes_list = list(node_features.keys())
    for key in tqdm.tqdm(nodes_list):
        node_features[key]
        node_features[key]['features'] = []
        # 'TCP/UDP'
        node_features[key]['features'].append(protocol_map[node_features[key]['ipProtocol']])
        del node_features[key]['ipProtocol']
        if len(node_features[key]['remoteAddress'])>0:
            node_features[key]['features'].extend(ipaddr_to_list(ipaddress.ip_address(node_features[key]['remoteAddress'])))
        else:
            node_features[key]['features'].extend(unknownip)
        del node_features[key]['remoteAddress']
        node_features[key]['features'].append(port_type.get(node_features[key]['remotePort'],0))
        del node_features[key]['remotePort']
        

    df = pd.DataFrame.from_dict(node_features,orient='index')
    df.to_json(os.path.join(vector_dir,'{}.json'.format(node_type)), orient='index')


if __name__ == "__main__":
    main()
