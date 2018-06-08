""" Hyperparameters for Large Scale Data Collection (LSDC) """

import os.path

import numpy as np

from python_visual_mpc.visual_mpc_core.algorithm.random_policy import Randompolicy
from python_visual_mpc.visual_mpc_core.agent.agent_mjc import AgentMuJoCo
from python_visual_mpc.visual_mpc_core.infrastructure.utility.tfrecord_from_file import pushing_touch_file2record as convert_to_record

IMAGE_WIDTH = 64
IMAGE_HEIGHT = 64
IMAGE_CHANNELS = 3

BASE_DIR = '/'.join(str.split(__file__, '/')[:-1])
current_dir = os.path.dirname(os.path.realpath(__file__))

import python_visual_mpc
DATA_DIR = '/'.join(str.split(python_visual_mpc.__file__, '/')[:-2])

agent = {
    'type': AgentMuJoCo,
    'data_save_dir': BASE_DIR + '/train', #'result/' #BASE_DIR + '/59903/data/train',
    'filename': DATA_DIR+'/mjc_models/cartgripper_grasp.xml',
    'filename_nomarkers': DATA_DIR+'/mjc_models/cartgripper_grasp.xml',
    'not_use_images':"",
    'visible_viewer':False,
    'sample_objectpos':'',
    'adim':5,
    'sdim':12,
    'cameras':['maincam', 'leftcam'],
    'finger_sensors' : True,
    'randomize_initial_pos':'',
    'dt': 0.05,
    'substeps': 200,  #6
    'T': 15,
    'skip_first': 40,   #skip first N time steps to let the scene settle
    'additional_viewer': False,
    'image_height' : 48,
    'image_width' : 64,
    'viewer_image_height' : 480,
    'viewer_image_width' : 640,
    'image_channels' : 3,
    'num_objects': 4,
    'novideo':'',
    'gen_xml':10,   #generate xml every nth trajecotry
    'pos_disp_range': 0.5, #randomize x, y
    'poscontroller_offset':'',
    'posmode':'abs',
    'ztarget':0.13,
    'min_z_lift':0.05,
    'make_final_gif':'', #keep this key in if you want final gif to be created
    'record': BASE_DIR + '/record/',
    'targetpos_clip':[[-0.5, -0.5, -0.08, -2 * np.pi, -1], [0.5, 0.5, 0.15, 2 * np.pi, 1]],
    'mode_rel':np.array([True, True, True, True, False]),
    'discrete_gripper' : -1, #discretized gripper dimension,
    'close_once_actions' : True,
    'file_to_record' : convert_to_record,
    'object_mass' : 0.1,
    'friction' : 1.0
    #'object_meshes':['giraffe'] #folder to original object + convex approximation
    # 'displacement_threshold':0.1,
}

policy = {
    'type' : Randompolicy,
    'nactions' : 5,
    'repeat' : 3,
    'no_action_bound' : False, 
    'initial_std': 0.1,   #std dev. in xy
    'initial_std_lift': 0.01,   #std dev. in z
    'initial_std_rot' : np.pi / 18,
    'initial_std_grasp' : 2, 
}

config = {
    'traj_per_file':128,
    'current_dir' : current_dir,
    'save_data': True,
    'save_raw_images' : True,
    'start_index':0,
    'end_index': 200000,
    'agent': agent,
    'policy': policy,
    'ngroup': 1000
}
