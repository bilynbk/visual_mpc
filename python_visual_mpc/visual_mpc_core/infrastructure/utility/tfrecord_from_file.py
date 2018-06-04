import argparse
import os
import sys
if sys.version_info[0] == 2:
    import imp
    import cPickle as pkl

else:
    import importlib.machinery
    import importlib.util
    import pickle as pkl

import glob
import numpy as np
import cv2
from python_visual_mpc.visual_mpc_core.infrastructure.utility.save_tf_record import save_tf_record

class DefaultTraj:
    def __init__(self):
        self.actions, self.X_Xdot_full, self.images  = None, None, None

def grasping_touch_file2record(state_action):
    loaded_traj = DefaultTraj()

    loaded_traj.actions = state_action['actions']
    touch_sensors = state_action['finger_sensors']
    loaded_traj.X_Xdot_full = np.concatenate((state_action['target_qpos'][:-1, :], touch_sensors), axis = 1)

    good_lift = False

    valid_frames = np.logical_and(state_action['target_qpos'][1:, -1] > 0, np.logical_and(touch_sensors[:, 0] > 0, touch_sensors[:, 1] > 0))
    off_ground = state_action['target_qpos'][1:,2] >= 0
    object_poses = state_action['object_full_pose']

    if any(np.logical_and(valid_frames, off_ground)):
        obj_eq = object_poses[0, :, :2] == state_action['obj_start_end_pos']
        obj_eq = np.logical_and(obj_eq[:, 0], obj_eq[:, 1])
        obj_eq = np.argmax(obj_eq)
        obj_max =  np.amax(object_poses[:,obj_eq,2])
        if obj_max >=0:
            good_lift = True

    return good_lift, loaded_traj
def pushing_touch_file2record(state_action):
    loaded_traj = DefaultTraj()

    loaded_traj.actions = state_action['actions']
    touch_sensors = state_action['finger_sensors']
    loaded_traj.X_Xdot_full = np.concatenate((state_action['target_qpos'][:-1, :], touch_sensors), axis = 1)
    
    object_poses = state_action['object_full_pose']
    good_push = False

    if any(np.sum(np.sum(np.square(object_poses[1:,:,:2] - object_poses[1, :, :2].reshape((1, -1, 2))), axis = 1), axis = 1) > 0.01):
        good_push = True     
    return good_push, loaded_traj

def main():
    parser = argparse.ArgumentParser(description='run convert from directory to tf record')
    parser.add_argument('experiment', type=str, help='experiment hyperparameter path')
    parser.add_argument('output', type=str, help='new output dir')
    parser.add_argument('-g', action='store', dest='good_offset', type = int,
                    default = 0, help='Offset good records by g * traj_per_file')
    parser.add_argument('-b', action='store', dest='bad_offset', type = int,
                    default = 0, help='Offset bad records by b * traj_per_file')


    args = parser.parse_args()
    hyperparams_file = args.experiment
    out_dir = args.output

    data_coll_dir = '/'.join(hyperparams_file.split('/')[:-1])

    if sys.version_info[0] == 2:
        hyperparams = imp.load_source('hyperparams', args.experiment)
        hyperparams = hyperparams.config
        #python 2 means we're executing on sawyer. add dummy camera list
        hyperparams['agent']['cameras'] = ['main', 'left']
    else:
        loader = importlib.machinery.SourceFileLoader('mod_hyper', hyperparams_file)
        spec = importlib.util.spec_from_loader(loader.name, loader)
        conf = importlib.util.module_from_spec(spec)
        loader.exec_module(conf)
        hyperparams = conf.config

    traj_per_file = hyperparams['traj_per_file']
    agent_config = hyperparams['agent']
    T = agent_config['T']

    data_dir = agent_config['data_save_dir']
    out_dir = data_coll_dir + '/' + out_dir
    agent_config['data_save_dir'] = out_dir
    img_height = agent_config['image_height']
    img_width = agent_config['image_width']

    print('loading from', data_dir)
    print('saving to', out_dir)

    good_traj_list, bad_traj_list = [], []
    num_good_saved, num_bad_saved = args.good_offset, args.bad_offset
    print('GOOD OFFSET {}, BAD OFFSET {}'.format(num_good_saved, num_bad_saved))

    good_lift_ctr, total_ctr = 0, 0
    traj_group_dirs = glob.glob(data_dir+'/*')
    
    agent_config['goal_image'] = True 

    dirs_to_create = [agent_config['data_save_dir'] + d for d in ['/good/train', '/good/test', '/good/val', '/bad/train', '/bad/test', '/bad/val']]
    for d in dirs_to_create:
        if not os.path.exists(d):
            os.makedirs(d)
            print('Creating dir:', d)

    for g in traj_group_dirs:
        trajs = glob.glob(g + '/*')
        for t in trajs:
            if not os.path.exists(t + '/state_action.pkl'):
                continue

            if 'cameras' in agent_config:
                valid = True
                for i in range(len(agent_config['cameras'])):
                    img_files = [t + '/images{}/im{}.png'.format(i, j) for j in range(T)]
                    if not all([os.path.exists(i) and os.path.isfile(i) for i in img_files]):
                        valid = False
                        print('traj {} missing /images{}'.format(t, i))
                        break
                if not valid:
                    continue
            else:
                if len(glob.glob(t + '/images/*.png')) != T:
                    continue

            try:
                state_action = pkl.load(open(t + '/state_action.pkl', 'rb'))
            except EOFError:
                continue

            if np.sum(np.isnan(state_action['target_qpos'])) > 0:
                print("FOUND NAN AT", t)     #error in mujoco environment sometimes manifest in NANs
            else:
                total_ctr += 1
                good_lift, loaded_traj = agent_config['file_to_record'](state_action)

                if 'cameras' in agent_config:
                    loaded_traj.images = np.zeros((T, len(agent_config['cameras']), img_height, img_width, 3), dtype = np.uint8)
                else:
                    loaded_traj.images = np.zeros((T, img_height, img_width, 3), dtype = np.uint8)

                for img in range(T):
                    if 'cameras' in agent_config:
                        for cam in range(len(agent_config['cameras'])):
                            loaded_traj.images[img, cam] = cv2.imread(t + '/images{}/im{}.png'.format(cam, img))[:, :, ::-1]
                    else:
                        loaded_traj.images[img] = cv2.imread(t + '/images/im{}.png'.format(img))[:, :, ::-1]

                if good_lift:
                    print(t)
                    good_lift_ctr += 1
                    good_traj_list.append(loaded_traj)
                else:
                    bad_traj_list.append(loaded_traj)

            if len(good_traj_list) % traj_per_file == 0 and len(good_traj_list) > 0:
                folder_prep = 'good/'
                if num_good_saved == 0:
                    folder_prep += 'test'
                elif np.random.rand() <= agent_config.get('train_val_split', 0.95):
                    folder_prep += 'train'
                else:
                    folder_prep += 'val'
                f_name = '{}/good_traj_{}_to_{}'.format(folder_prep, num_good_saved * traj_per_file, (num_good_saved + 1) * traj_per_file - 1)
                print('saving', f_name)
                save_tf_record(f_name, good_traj_list, agent_config)
                good_traj_list = []
                num_good_saved += 1
            elif len(bad_traj_list) % traj_per_file == 0 and len(bad_traj_list) > 0:
                folder_prep = 'bad/'
                if num_bad_saved == 0:
                    folder_prep += 'test'
                elif np.random.rand() <= agent_config.get('train_val_split', 0.95):
                    folder_prep += 'train'
                else:
                    folder_prep += 'val'
                f_name = '{}/bad_traj_{}_to_{}'.format(folder_prep, num_bad_saved * traj_per_file, (num_bad_saved + 1) * traj_per_file - 1)
                print('saving', f_name)
                save_tf_record(f_name, bad_traj_list, agent_config)
                bad_traj_list = []
                num_bad_saved += 1

    if  len(good_traj_list) > 0:
        f_name = 'good/train/good_traj_{0}_to_{1}'.format(num_good_saved * traj_per_file, (num_good_saved + 1) * traj_per_file - 1)
        save_tf_record(f_name, good_traj_list, agent_config)
        good_traj_list = []
    elif len(bad_traj_list) > 0:
        f_name = 'bad/train/bad_traj_{0}_to_{1}'.format(num_bad_saved * traj_per_file, (num_bad_saved + 1) * traj_per_file - 1)
        save_tf_record(f_name, bad_traj_list, agent_config)
        bad_traj_list = []
        
    print('perc good_lift', good_lift_ctr / total_ctr)

if __name__ == '__main__':
    main()
