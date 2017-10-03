# Copyright 2016 The TensorFlow Authors All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Model architecture for predictive model, including CDNA, DNA, and STP."""

import numpy as np
import tensorflow as tf
import pdb

import tensorflow.contrib.slim as slim
from tensorflow.contrib.layers.python import layers as tf_layers
from python_visual_mpc.video_prediction.basecls.utils.transformations import dna_transformation, sep_dna_transformation
from python_visual_mpc.video_prediction.basecls.utils.transformations import cdna_transformation, sep_cdna_transformation

# Amount to use when lower bounding tensors
RELU_SHIFT = 1e-12

class Descriptor_Flow(object):
    def __init__(self, conf, images):
        """Build network for predicting optical flow
        """
        if 'large_core' in conf:
            self.d0 = self.build_descriptors_large(images[0])
            self.d1 = self.build_descriptors_large(images[1])
            print 'using large core'
        else:
            with tf.variable_scope('d0'):
                self.d0 = self.build_descriptors(conf, images[0])

            with tf.variable_scope('d1'):
                self.d1 = self.build_descriptors(conf, images[1])

        trafo_kerns01 = self.get_trafo(conf, self.d0, self.d1)
        self.transformed01 = self.apply_trafo(conf, images[0], trafo_kerns01)

        if 'forward_backward' in conf:
            print 'using forward backward'
            trafo_kerns10 = self.get_trafo(conf, self.d1, self.d0)
            self.transformed10 = self.apply_trafo(conf, images[1], trafo_kerns10)

    def apply_trafo(self, conf, prev_image, kerns):
        """Apply dynamic neural advection to previous image.

            Args:
              prev_image: previous image to be transformed.
              dna_input: hidden lyaer to be used for computing DNA transformation.
            Returns:
              List of images transformed by the predicted CDNA kernels.
            """
        # Construct translated images.
        KERN_SIZE = conf['kern_size']

        pad_len = int(np.floor(KERN_SIZE / 2))
        prev_image_pad = tf.pad(prev_image, [[0, 0], [pad_len, pad_len], [pad_len, pad_len], [0, 0]])
        image_height = int(prev_image.get_shape()[1])
        image_width = int(prev_image.get_shape()[2])

        shifted = []
        for xkern in range(KERN_SIZE):
            for ykern in range(KERN_SIZE):
                shifted.append(tf.slice(prev_image_pad, [0, xkern, ykern, 0],
                                 [-1, image_height, image_width, -1]))

        shifted = tf.stack(axis=3, values=shifted)
        shifted = tf.reshape(shifted, [conf['batch_size'], 64, 64, KERN_SIZE, KERN_SIZE, 3])

        # Normalize channels to 1.

        return tf.reduce_sum(kerns[...,None] * shifted, [3,4], keep_dims=False)

    def get_trafo(self, conf, d1, d2):

        # Construct translated images.
        KERN_SIZE = conf['kern_size']
        DESC_LENGTH = conf['desc_length']

        pad_len = int(np.floor(KERN_SIZE / 2))
        padded_d2 = tf.pad(d2, [[0, 0], [pad_len, pad_len], [pad_len, pad_len], [0, 0]])
        image_height = int(d2.get_shape()[1])
        image_width = int(d2.get_shape()[2])

        shifted_d2 = []
        for row in range(KERN_SIZE):
            for col in range(KERN_SIZE):
                shifted_d2.append(tf.slice(padded_d2, [0, row, col, 0],
                                           [-1, image_height, image_width, -1]))

        shifted_d2 = tf.stack(axis= -1, values=shifted_d2)

        shifted_d2 = tf.reshape(shifted_d2, [conf['batch_size'], 64,64,DESC_LENGTH, KERN_SIZE,KERN_SIZE])

        # repeat d1 along kernel dimensions
        repeated_d1 = tf.tile(d1[:,:,:,:,None,None], [1,1,1,1, KERN_SIZE, KERN_SIZE])

        if conf['metric'] == 'inverse_euclidean':
            dist_fields = tf.reduce_sum(tf.square(repeated_d1-shifted_d2), 3)
            inverse_dist_fields = tf.div(1., dist_fields + 1e-5)
            #normed_dist_fields should correspond DNA-like trafo kernels
            trafo = inverse_dist_fields / (tf.reduce_sum(inverse_dist_fields, [3,4], keep_dims=True) + 1e-6)
            print 'using inverse_euclidean'
        elif conf['metric'] == 'cosine':

            cos_dist = tf.reduce_sum(repeated_d1*shifted_d2, axis=3)/(tf.norm(repeated_d1, axis=3)+1e-5)/(tf.norm(shifted_d2, axis=3) +1e-5)
            cos_dist = tf.reshape(cos_dist, [conf['batch_size'], 64, 64, KERN_SIZE**2])
            trafo = tf.nn.softmax(cos_dist*conf['softmax_temp'], 3)

            trafo = tf.reshape(trafo, [conf['batch_size'], 64, 64, KERN_SIZE, KERN_SIZE])
            print 'using cosine distance'

        return trafo


    def build_descriptors(self, conf, img):

        enc0 = slim.layers.conv2d(   #32x32x32
                    img,
                    32, [5, 5],
                    stride=2,
                    scope='conv0',
                )

        enc1 = slim.layers.conv2d( #16x16x64
            enc0,
            64, [5, 5],
            stride=2,
            scope='conv1',
        )

        enc2 = slim.layers.conv2d_transpose(  #32x32x32
            enc1,
            32, [5, 5],
            stride=2,
            scope='t_conv1',
        )

        enc3 = slim.layers.conv2d_transpose( # 64x64x32
            enc2,
            conf['desc_length'], [5, 5],
            stride=2,
            scope='t_conv2',
            activation_fn=None
        )

        return enc3


    def build_descriptors_large(self, concat_img):
        enc0 = slim.layers.conv2d(  # 32x32x32
            concat_img,
            32, [5, 5],
            stride=2,
            scope='conv0',
        )

        enc1 = slim.layers.conv2d(  # 32x32x32
            enc0,
            32, [5, 5],
            stride=1,
            scope='conv1',
        )

        enc2 = slim.layers.conv2d(  # 16x16x64
            enc1,
            64, [5, 5],
            stride=2,
            scope='conv2',
        )

        enc3 = slim.layers.conv2d_transpose(  # 32x32x32
            enc2,
            32, [5, 5],
            stride=2,
            scope='t_conv1',
        )

        enc4 = slim.layers.conv2d_transpose(  # 32x32x32
            enc3,
            32, [5, 5],
            stride=2,
            scope='t_conv2',
        )

        enc5 = slim.layers.conv2d_transpose(  # 64x64x32
            enc4,
            32, [5, 5],
            stride=2,
            scope='t_conv3',
            activation_fn=None
        )

        return enc5

def compute_motion_vector_cdna(conf, cdna_kerns):

    range = conf['kern_size'] / 2
    dc = np.linspace(-range, range, num= conf['kern_size'])
    dc = np.expand_dims(dc, axis=0)
    dc = np.repeat(dc, conf['kern_size'], axis=0)
    dr = np.transpose(dc)
    dr = tf.constant(dr, dtype=tf.float32)
    dc = tf.constant(dc, dtype=tf.float32)

    cdna_kerns = tf.transpose(cdna_kerns, [2, 3, 0, 1])
    cdna_kerns = tf.split(cdna_kerns, conf['num_masks'], axis=1)
    cdna_kerns = [tf.reshape(k, [conf['batch_size'], conf['kern_size'], conf['kern_size']]) for k in cdna_kerns]

    vecs = []
    for kern in cdna_kerns:
        vec_r = tf.multiply(dr, kern)
        vec_r = tf.reduce_sum(vec_r, axis=[1,2])
        vec_c = tf.multiply(dc, kern)
        vec_c = tf.reduce_sum(vec_c, axis=[1, 2])

        vecs.append(tf.stack([vec_r,vec_c], axis=1))
    return vecs


def compute_motion_vector_dna(conf, dna_kerns):

    range = conf['kern_size'] / 2
    dc = np.linspace(-range, range, num= conf['kern_size'])
    dc = np.expand_dims(dc, axis=0)
    dc = np.repeat(dc, conf['kern_size'], axis=0)

    dc = dc.reshape([1,1,conf['kern_size'],conf['kern_size']])
    dc = np.repeat(dc, 64, axis=0)
    dc = np.repeat(dc, 64, axis=1)

    dr = np.transpose(dc, [0,1,3,2])

    dr = tf.constant(dr, dtype=tf.float32)
    dc = tf.constant(dc, dtype=tf.float32)

    dna_kerns = tf.reshape(dna_kerns, [conf['batch_size'], 64,64,conf['kern_size'],conf['kern_size']])

    dr = tf.expand_dims(dr, axis=0)
    dc = tf.expand_dims(dc, axis=0)

    vec_r = tf.multiply(dr, dna_kerns)
    vec_r = tf.reduce_sum(vec_r, axis=[3,4])
    vec_c = tf.multiply(dc, dna_kerns)
    vec_c = tf.reduce_sum(vec_c, axis=[3,4])

    vec_c = tf.expand_dims(vec_c, axis=-1)
    vec_r = tf.expand_dims(vec_r, axis=-1)

    flow = tf.concat([vec_r, vec_c], axis=-1)  # size: [conf['batch_size'], 64, 64, 2]

    return [flow]