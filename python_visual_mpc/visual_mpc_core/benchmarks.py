from infrastructure.run_sim import Sim
import argparse
import imp
import os
import numpy as np
import pdb
import copy
import random
import cPickle
from PIL import Image
from python_visual_mpc.video_prediction.utils_vpred.online_reader import read_trajectory

from python_visual_mpc import __file__ as python_vmpc_path
from python_visual_mpc.data_preparation.gather_data import make_traj_name_list


def perform_benchmark(conf = None):
    cem_exp_dir = '/'.join(str.split(python_vmpc_path, '/')[:-2])  + '/experiments/cem_exp'

    if conf != None:
        benchmark_name = 'parallel'
        gpu_id = 0
        ngpu = 1
        bench_dir = conf.config['bench_dir']
        goalimg_save_dir = bench_dir + '/goalimage'
    else:
        parser = argparse.ArgumentParser(description='Run benchmarks')
        parser.add_argument('benchmark', type=str, help='the name of the folder with agent setting for the benchmark')
        parser.add_argument('--gpu_id', type=int, default=0, help='value to set for cuda visible devices variable')
        parser.add_argument('--ngpu', type=int, default=1, help='number of gpus to use')
        args = parser.parse_args()

        benchmark_name = args.benchmark
        gpu_id = args.gpu_id
        ngpu = args.ngpu

        # load specific agent settings for benchmark:
        bench_dir = cem_exp_dir + '/benchmarks/' + benchmark_name
        if not os.path.exists(bench_dir):
            print 'performing goal image benchmark ...'
            bench_dir = cem_exp_dir + '/benchmarks_goalimage/' + benchmark_name
            if not os.path.exists(bench_dir):
                raise ValueError('benchmark directory does not exist')

        conf = imp.load_source('mod_hyper', bench_dir + '/mod_hyper.py')
        conf = conf.config

    conf['agent']['skip_first'] = 10

    print '-------------------------------------------------------------------'
    print 'name of algorithm setting: ' + benchmark_name
    print 'agent settings'
    for key in conf['agent'].keys():
        print key, ': ', conf['agent'][key]
    print '------------------------'
    print '------------------------'
    print 'policy settings'
    for key in conf['policy'].keys():
        print key, ': ', conf['policy'][key]
    print '-------------------------------------------------------------------'

    # sample intial conditions and goalpoints

    if 'verbose' in conf['policy']:
        print 'verbose mode!! just running 1 configuration'
        nruns = 1

    if 'n_reseed' in conf['policy']:
        n_reseed = conf['policy']['n_reseed']
    else:
        n_reseed = 3

    anglecost = []
    sim = Sim(conf, gpu_id= gpu_id, ngpu= ngpu)

    if 'start_confs' not in conf['agent']:
        benchconfiguration = cPickle.load(open('infrastructure/benchmarkconfigs', "rb"))
    else:
        benchconfiguration = cPickle.load(open(conf['agent']['start_confs'], "rb"))

    if conf['start_index'] != None:  # used when doing multiprocessing
        traj = conf['start_index']
        i_conf = conf['start_index']
        nruns = conf['end_index']
        print 'started worker going from ind {} to in {}'.format(conf['start_index'], conf['end_index'])
    else:
        nruns = len(benchconfiguration['initialpos'])*n_reseed  # 60 in standard benchmark
        i_conf = 0
        traj = 0

    goalpoints = benchconfiguration['goalpoints']
    initialposes = benchconfiguration['initialpos']

    scores = np.zeros(nruns)

    if 'sourcetags' in conf:  # load data per trajectory
        traj_names = make_traj_name_list({'source_basedirs': conf['source_basedirs'],
                                                  'ngroup': conf['ngroup']}, shuffle=False)

    while traj < nruns:
        if 'sourcetags' in conf:  #load data per trajectory from folder structure
            dict = read_trajectory(conf, traj_names[traj])
            sim.agent._hyperparams['xpos0'] = dict['qpos'][0]
            sim.agent._hyperparams['object_pos0'] = dict['object_full_pose'][0]
            sim.agent.load_obj_statprop = dict['obj_statprop']
        else: #load when loading data from a single file
            sim.agent._hyperparams['xpos0'] = initialposes[i_conf]
            sim.agent._hyperparams['object_pos0'] = goalpoints[i_conf]

        if 'use_goal_image' not in conf['policy']:
            sim.agent._hyperparams['goal_point'] = goalpoints[i_conf]

        for j in range(n_reseed):
            if traj > nruns -1:
                break

            seed = traj+1
            random.seed(seed)
            np.random.seed(seed)
            print '-------------------------------------------------------------------'
            print 'run number ', traj
            print 'configuration No. ', i_conf
            print 'using random seed', seed
            print '-------------------------------------------------------------------'

            sim.agent._hyperparams['record'] = bench_dir + '/videos/traj{0}_conf{1}'.format(traj, i_conf)

            # reinitilize policy between rollouts
            if 'usenet' in conf['policy']:
                if 'use_goal_image' in conf['policy']:
                    sim.policy = conf['policy']['type'](sim.agent._hyperparams,
                                            conf['policy'], sim.predictor, sim.goal_image_waper)
                else:
                    sim.policy = conf['policy']['type'](sim.agent._hyperparams,
                                                     conf['policy'], sim.predictor)
            else:
                sim.policy = conf['policy']['type'](sim.agent._hyperparams, conf['policy'])

            sim.policy.policyparams['rec_distrib'] = bench_dir + '/videos_distrib/traj{0}_conf{1}'.format(traj, i_conf)

            if 'sourcetags' in conf:
                sim.policy.goal_image = dict['images'][-1]  # assign last image of trajectory as goalimage
            sim._take_sample(traj)

            scores[traj] = sim.agent.final_poscost

            if 'use_goal_image' in conf['agent']:
                anglecost.append(sim.agent.final_anglecost)

            print 'score of traj', traj, ':', scores[traj]

            traj +=1 #increment trajectories every step!

        i_conf += 1 #increment configurations every three steps!

        rel_scores = scores[:traj]
        sorted_ind = rel_scores.argsort()
        f = open(bench_dir + '/results', 'w')
        f.write('experiment name: ' + benchmark_name + '\n')
        f.write('overall best pos score: {0} of traj {1}\n'.format(rel_scores[sorted_ind[0]], sorted_ind[0]))
        f.write('overall worst pos score: {0} of traj {1}\n'.format(rel_scores[sorted_ind[-1]], sorted_ind[-1]))
        f.write('average pos score: {0}\n'.format(np.sum(rel_scores) / traj))
        f.write('standard deviation {0}\n'.format(np.sqrt(np.var(rel_scores))))
        f.write('----------------------\n')
        f.write('traj: score, anglecost, rank\n')
        f.write('----------------------\n')
        for t in range(traj):
            if 'use_goal_image' in conf['agent']:
                f.write('{0}: {1}, {2}, :{3}\n'.format(t, rel_scores[t], anglecost[t], np.where(sorted_ind == t)[0][0]))
            else:
                f.write('{0}: {1}, :{2}\n'.format(t, rel_scores[t], np.where(sorted_ind == t)[0][0]))
        f.close()

    print 'overall best score: {0} of traj {1}'.format(scores[sorted_ind[0]], sorted_ind[0])
    print 'overall worst score: {0} of traj {1}'.format(scores[sorted_ind[-1]], sorted_ind[-1])
    print 'overall average score:', np.sum(scores)/scores.shape
    print 'standard deviation {0}\n'.format(np.sqrt(np.var(scores)))


if __name__ == '__main__':
    perform_benchmark()