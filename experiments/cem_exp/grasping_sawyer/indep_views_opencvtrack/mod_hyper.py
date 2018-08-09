""" Hyperparameters for Robot Large Scale Data Collection (RLSDC) """

import numpy as np
from python_visual_mpc.visual_mpc_core.algorithm.visual_mpc_policy import VisualMPCPolicy
from python_visual_mpc.visual_mpc_core.algorithm.cem_controller_goalimage_sawyer import CEM_controller
import os
from python_visual_mpc.sawyer.visual_mpc_rospkg.src.agent.agent_robot import AgentSawyer
from python_visual_mpc.visual_mpc_core.infrastructure.utility.tfrecord_from_file import grasping_sawyer_file2record as convert_to_record
BASE_DIR = '/'.join(str.split(__file__, '/')[:-1])
current_dir = os.path.dirname(os.path.realpath(__file__))


agent = {'type' : AgentSawyer,
         'data_save_dir': BASE_DIR + '/train',
         'T' : 15,  #number of commands per episodes (issued at control_rate / substeps HZ)
         'step_duration' : 0.75,  #time each substep takes to execute
         'impedance_stiffness' : 150, #stiffness commanded to impedance controller
         'control_rate' : 1000,  #substep are taken at control_rate HZ
         'image_height' : 48,
         'image_width' : 64,
         'adim' : 5,
         'sdim' : 5,
         'mode_rel' : np.array([True, True, True, True, False]),
         'autograsp' : {'zthresh' :  0.15, 'touchthresh' : 0.0, 'reopen' : ''},   #15% of total height is zthresh,
         'file_to_record' : convert_to_record,
         'cameras':['front', 'left'],
         'benchmark_exp':'',
         'opencv_tracking' : ''
         }

policy = {
    'current_dir':current_dir,
    'type' : VisualMPCPolicy,
    'cem_type':CEM_controller,
    'nactions' : 5,
    'repeat' : 3,
    'initial_std': 0.02, #0.035,   #std dev. in xy
    'initial_std_lift': 0.04,   #std dev. in z
    'initial_std_rot' : np.pi / 18,
    'initial_std_grasp' : 2,
    'netconf': current_dir + '/conf.py',
    'iterations': 3,
    'action_cost_factor': 0,
    'rew_all_steps':"",
    'finalweight':10,
}

config = {
    'traj_per_file':128,
    'current_dir' : current_dir,
    'save_data': True,
    'save_raw_images' : True,
    'start_index':0,
    'end_index': 30000,
    'agent': agent,
    'policy': policy,
    'ngroup': 1000,
    'nshuffle' : 200
}
