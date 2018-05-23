import os
import python_visual_mpc
current_dir = '/'.join(str.split(__file__, '/')[:-1])
bench_dir = '/'.join(str.split(__file__, '/')[:-2])

from python_visual_mpc.visual_mpc_core.algorithm.cem_controller_goalimage_sawyer import CEM_controller

ROOT_DIR = os.path.abspath(python_visual_mpc.__file__)
ROOT_DIR = '/'.join(str.split(ROOT_DIR, '/')[:-2])

from python_visual_mpc.visual_mpc_core.agent.agent_mjc import AgentMuJoCo
import numpy as np
agent = {
    'type': AgentMuJoCo,
    'T': 15,
    'substeps':200,
    'adim':5,
    'sdim':12,
    'make_final_gif':'',
    'filename': ROOT_DIR + '/mjc_models/cartgripper_grasp.xml',
    'filename_nomarkers': ROOT_DIR + '/mjc_models/cartgripper_grasp.xml',
    'gen_xml':1,   #generate xml every nth trajecotry
    'skip_first':10,
    'num_objects': 1,
    'object_mass':0.01,
    'friction':1.5,
    'viewer_image_height' : 480,
    'viewer_image_width' : 640,
    'image_height':48,
    'image_width':64,
    'sample_objectpos':'',
    'randomize_ballinitpos':'',
    'const_dist':0.0,
    'lift_obejct':"",
    'data_save_dir':current_dir + '/data/train',
    'logging_dir':current_dir + '/logging',
    'posmode':"",
    'targetpos_clip':[[-0.45, -0.45, -0.08, -np.pi*2, -100], [0.45, 0.45, 0.15, np.pi*2, 100]], ##
    'mode_rel':np.array([True, True, True, True, False]),
}

policy = {
    'verbose':"", ###################3
    # 'verbose':100,
    'type' : CEM_controller,
    'low_level_ctrl': None,
    'current_dir':current_dir,
    'usenet': True,
    'nactions': 5,
    'repeat': 3,
    'initial_std': 0.08,        # std dev. in xy
    'initial_std_lift': 0.01,
    'initial_std_rot': 0.01,
    'initial_std_grasp': 30,  #######
    'netconf': current_dir + '/conf.py',
    'iterations': 3,
    'action_cost_factor': 0,
    'rew_all_steps':"",
    'finalweight':10,
    # 'predictor_propagation': '',   # use the model get the designated pixel for the next step!
}


config = {
    'current_dir':current_dir,
    'traj_per_file':16,   # needs to be equal batch size!!
    'save_data': True,
    'start_index':0,
    'end_index': 59999,
    'agent':agent,
    'policy':policy,
}