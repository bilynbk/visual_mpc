""" This file defines the sample class. """
import numpy as np

class Trajectory(object):
    def __init__(self, conf):

        self.T = conf['T']

        img_channels = 3

        if conf is None:
            img_height = 64
            img_width = 64
        else:
            img_height = conf['image_height']
            img_width = conf['image_width']

        self._sample_images = np.zeros((self.T,
                                        img_height,
                                        img_width,
                                        img_channels), dtype='uint8')

        # for storing the terminal predicted images of the K best actions at each time step:
        self.final_predicted_images = []
        self.predicted_images = None
        self.gtruth_images = None

        if 'adim' in conf:
            self.actions = np.empty([self.T, conf['adim']])
        else:
            self.actions = np.empty([self.T, 2])

        if 'sdim' in conf:
            state_dim = conf['sdim']
        else:
            state_dim = 2

        self.X_full = np.empty([self.T, state_dim/2])
        self.Xdot_full = np.empty([self.T, state_dim/2])
        self.X_Xdot_full = np.empty([self.T, state_dim])

        if 'num_objects' in conf:
            self.Object_pose = np.empty([self.T, conf['num_objects'], 3])  # x,y rot of  block
            self.Object_full_pose = np.empty([self.T, conf['num_objects'], 7])  # xyz and quaternion pose

        self.desig_pos = np.empty([self.T, 2])
        self.score = np.empty([self.T])