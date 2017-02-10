import os
import numpy as np
import tensorflow as tf
import imp
import sys
import cPickle
from tensorflow.python.platform import app
from tensorflow.python.platform import flags
from read_tf_record_lval import build_tfrecord_input
from datetime import datetime
import matplotlib.pyplot as plt
from PIL import Image

# How often to record tensorboard summaries.
SUMMARY_INTERVAL = 40

# How often to run a batch through the validation model.
VAL_INTERVAL = 200

# How often to save a model checkpoint
SAVE_INTERVAL = 2000

FLAGS = flags.FLAGS
flags.DEFINE_string('hyper', '', 'name of folder with hyperparameters configuration file (inside tensorflowdata_lval)')
flags.DEFINE_string('visualize', '', 'model within hyperparameter folder from which to create gifs')
flags.DEFINE_integer('device', 0 ,'the value for CUDA_VISIBLE_DEVICES variable')

def mean_squared_error(true, pred):
    """L2 distance between tensors true and pred.
    Args:
      true: the ground truth image.
      pred: the predicted image.
    Returns:
      mean squared error between ground truth and predicted image.
    """
    return tf.reduce_sum(tf.square(true - pred)) / tf.to_float(tf.size(pred))

class Model(object):
    def __init__(self, conf, images=None, scores=None, goal_pos=None, desig_pos=None):
        batchsize = int(conf['batch_size'])
        if goal_pos is None:
            self.goal_pos = tf.placeholder(tf.float32, name='goalpos', shape=(batchsize, 2))
        if desig_pos is None:
            self.desig_pos = tf.placeholder(tf.float32, name='desig_pos_pl', shape=(batchsize, 2))
        if scores is None:
            self.scores = tf.placeholder(tf.float32, name='score_pl', shape=(batchsize, 1))
        if images is None:
            self.images = tf.placeholder(tf.float32, name='images_pl', shape=(batchsize, 1, 64,64,3))

        self.prefix = prefix = tf.placeholder(tf.string, [])

        from value_model import construct_model

        summaries = []
        inf_scores = construct_model(conf, self.images, self.goal_pos, self.desig_pos)
        self.inf_scores = inf_scores
        self.loss = loss = mean_squared_error(inf_scores, self.scores)

        summaries.append(tf.scalar_summary(prefix + '_loss', loss))

        self.lr = tf.placeholder_with_default(conf['learning_rate'], ())

        self.train_op = tf.train.AdamOptimizer(self.lr).minimize(loss)
        self.summ_op = tf.merge_summary(summaries)

def mujoco_to_imagespace(mujoco_coord, numpix = 64, truncate = False, noflip= False):
    """
    convert form Mujoco-Coord to numpix x numpix image space:
    :param numpix: number of pixels of square image
    :param mujoco_coord:
    :return: pixel_coord
    """
    viewer_distance = .75  # distance from camera to the viewing plane
    window_height = 2 * np.tan(75 / 2 / 180. * np.pi) * viewer_distance  # window height in Mujoco coords
    pixelheight = window_height / numpix  # height of one pixel
    pixelwidth = pixelheight
    window_width = pixelwidth * numpix
    middle_pixel = numpix / 2

    if not noflip:
        pixel_coord = np.rint(np.array([-mujoco_coord[1], mujoco_coord[0]]) /
                              pixelwidth + np.array([middle_pixel, middle_pixel]))
    else:
        pixel_coord = np.rint(np.array([mujoco_coord[0], mujoco_coord[1]]) /
                              pixelwidth + np.array([middle_pixel, middle_pixel]))

    pixel_coord = pixel_coord.astype(int)
    if truncate:
        if np.any(pixel_coord < 0) or np.any(pixel_coord > numpix -1):
            print '###################'
            print 'designated pixel is outside the field!! Resetting it to be inside...'
            print 'truncating...'
            if np.any(pixel_coord < 0):
                pixel_coord[pixel_coord < 0] = 0
            if np.any(pixel_coord > numpix-1):
                pixel_coord[pixel_coord > numpix-1]  = numpix-1

    return pixel_coord

def imagespace_to_mujoco(pixel_coord, numpix = 64, noflip =False):
    viewer_distance = .75  # distance from camera to the viewing plane
    window_height = 2 * np.tan(75 / 2 / 180. * np.pi) * viewer_distance  # window height in Mujoco coords
    coords = (pixel_coord - float(numpix)/2)/float(numpix) * window_height
    if not noflip:
        mujoco_coords = np.array([-coords[1], coords[0]])
    else:
        mujoco_coords = coords
    return mujoco_coords

def visualize(conf):

    conf['data_dir'] = '/'.join(str.split(conf['data_dir'], '/')[:-1] + ['test'])
    conf['visualize'] = conf['output_dir'] + '/' + FLAGS.visualize
    conf['event_log_dir'] = '/tmp'
    conf['visual_file'] = conf['data_dir'] + '/traj_0_to_4.tfrecords'
    conf['batch_size'] = 1

    with tf.variable_scope('model', reuse=None) as training_scope:
        model = Model(conf)

    saver = tf.train.Saver(tf.get_collection(tf.GraphKeys.VARIABLES), max_to_keep=0)
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.9)
    sess = tf.InteractiveSession(config=tf.ConfigProto(gpu_options=gpu_options))

    sess.run(tf.initialize_all_variables())
    saver.restore(sess, conf['visualize'])

    visualize_different_goalpos(conf, model, sess)


def visualize_different_goalpos(conf, model, sess):


    image, score, goalpos, desig_pos = build_tfrecord_input(conf, training=True)
    tf.train.start_queue_runners(sess)

    num_examples = 5
    for n_ex in range(num_examples):

        image_npy, desig_pos_npy = sess.run([image, desig_pos])

        num = 64
        value = np.zeros((num, num))
        for r, r_coord in enumerate(np.linspace(0, 63, num)):
            for c, c_coord in enumerate(np.linspace(0, 63, num)):
                goal_mj_coord = imagespace_to_mujoco(np.array([r_coord, c_coord]))
                # print 'mujoco goal', goal_mj_coord
                feed_dict = {
                    model.images: image_npy,
                    model.goal_pos: goal_mj_coord.reshape((1, 2)),
                    model.desig_pos: desig_pos_npy,
                    model.lr: 0.0,
                    model.prefix: 'vis'
                }
                value[r, c] = sess.run([model.inf_scores], feed_dict)[0]

                # dist_to_zero[r,c] = np.linalg.norm(goal_mj_coord)

        # TODO: overlay designated position
        # X, Y = np.meshgrid(np.linspace(0, 63, num), np.linspace(0, 63, num))
        fig, ax = plt.subplots(1)

        desig_pos_pix = mujoco_to_imagespace(desig_pos_npy.squeeze())
        value[desig_pos_pix[0], desig_pos_pix[1]] = 0

        # value[0,0] = 0
        # value[63,63] = 1

        value = np.fliplr(value)

        # import pdb; pdb.set_trace()

        # plt.pcolor(X, Y, value, cmap=plt.get_cmap('jet'))
        plt.imshow(value, zorder=0, interpolation= 'none')
        ax.set_xlim([0, 63])
        ax.set_ylim([0, 63])
        plt.colorbar()

        # plt.show()
        # legend
        plt.savefig('{0}values_different_goalpos.png'.format(n_ex))
        print 'desig_pos mujoco', desig_pos_npy
        print 'desig_pos image', mujoco_to_imagespace(desig_pos_npy.squeeze())

        image_npy = image_npy.squeeze()
        image_npy[desig_pos_pix[0], desig_pos_pix[1]] = [1,1,1]
        im = Image.fromarray(np.uint8(image_npy.squeeze() * 255))
        im.save('{0}imvalues_different_goalpos.png'.format(n_ex),"PNG")



def main(unused_argv, conf_script= None):
    os.environ["CUDA_VISIBLE_DEVICES"] = str(FLAGS.device)
    print 'using CUDA_VISIBLE_DEVICES=', FLAGS.device
    from tensorflow.python.client import device_lib
    print device_lib.list_local_devices()

    if conf_script == None: conf_file = FLAGS.hyper
    else: conf_file = conf_script

    current_dir = os.path.dirname(os.path.realpath(__file__))
    lsdc_basedir = '/'.join(str.split(current_dir, '/')[:-3])
    hyperfile = lsdc_basedir + '/experiments/val_exp/tensorflowdata_lval/' + FLAGS.hyper +'/conf.py'

    if not os.path.exists(hyperfile):
        sys.exit("Experiment configuration not found")

    hyperparams = imp.load_source('hyperparams', hyperfile)

    conf = hyperparams.configuration

    if FLAGS.visualize:
        print 'creating visualizations ...'
        visualize(conf)
        return

    print '-------------------------------------------------------------------'
    print 'verify current settings!! '
    for key in conf.keys():
        print key, ': ', conf[key]
    print '-------------------------------------------------------------------'

    print 'Constructing models and inputs.'
    with tf.variable_scope('model', reuse=None) as training_scope:
        image_batch, score_batch, goalpos_batch, desig_pos_batch = build_tfrecord_input(conf, training=True)
        image_batch_val, score_batch_val, goalpos_batch_val, desig_pos_batch_val = build_tfrecord_input(conf, training=False)

        condition = tf.placeholder(tf.int32, shape=[], name="condition")

        image, score, goalpos, desig_pos = tf.cond(condition > 0,   # if 1 use trainigbatch else validation batch
                                       lambda: [image_batch, score_batch, goalpos_batch, desig_pos_batch],
                                       lambda: [image_batch_val, score_batch_val, goalpos_batch_val, desig_pos_batch_val])
        model = Model(conf, image, score, goalpos, desig_pos)


    print 'Constructing saver.'
    # Make saver.
    saver = tf.train.Saver(tf.get_collection(tf.GraphKeys.VARIABLES), max_to_keep=0)

    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.9)
    # Make training session.
    sess = tf.InteractiveSession(config= tf.ConfigProto(gpu_options=gpu_options))
    summary_writer = tf.train.SummaryWriter(
        conf['output_dir'], graph=sess.graph, flush_secs=10)

    tf.train.start_queue_runners(sess)
    sess.run(tf.initialize_all_variables())

    ### debug ###
    # saver = tf.train.Saver(tf.get_collection(tf.GraphKeys.VARIABLES), max_to_keep=0)
    # saver.restore(sess, conf['output_dir'] + '/' + FLAGS.visualize)
    # import pdb; pdb.set_trace()
    ### debug end

    itr_0 =0
    if conf['pretrained_model']:    # is the order of initialize_all_variables() and restore() important?!?
        saver.restore(sess, conf['pretrained_model'])
        # resume training at iteration step of the loaded model:
        import re
        itr_0 = re.match('.*?([0-9]+)$', conf['pretrained_model']).group(1)
        itr_0 = int(itr_0)
        print 'resuming training at iteration:  ', itr_0

    tf.logging.info('iteration number, cost')

    starttime = datetime.now()
    t_iter = []
    # Run training.
    for itr in range(itr_0, conf['num_iterations'], 1):
        t_startiter = datetime.now()
        # Generate new batch of data_files.
        feed_dict = {
                     condition: 1,
                     model.prefix: 'train',
                     model.lr: conf['learning_rate']}
        cost, _, summary_str = sess.run([model.loss, model.train_op, model.summ_op],
                                        feed_dict)

        # Print info: iteration #, cost.
        if (itr) % 10 ==0:
            tf.logging.info(str(itr) + ' ' + str(cost))

        if (itr) % VAL_INTERVAL == 2:
            # Run through validation set.
            feed_dict = {condition: 0,
                         model.lr: 0.0,
                         model.prefix: 'val',
                         }
            _, val_summary_str = sess.run([model.train_op, model.summ_op],
                                          feed_dict)
            summary_writer.add_summary(val_summary_str, itr)


        if (itr) % SAVE_INTERVAL == 2:
            tf.logging.info('Saving model to' + conf['output_dir'])
            saver.save(sess, conf['output_dir'] + '/model' + str(itr))

        t_iter.append((datetime.now() - t_startiter).seconds * 1e6 +  (datetime.now() - t_startiter).microseconds )

        if itr % 100 == 1:
            hours = (datetime.now() -starttime).seconds/3600
            tf.logging.info('running for {0}d, {1}h, {2}min'.format(
                (datetime.now() - starttime).days,
                hours,
                (datetime.now() - starttime).seconds/60 - hours*60))
            avg_t_iter = np.sum(np.asarray(t_iter))/len(t_iter)
            tf.logging.info('time per iteration: {0}'.format(avg_t_iter/1e6))
            tf.logging.info('expected for complete training: {0}h '.format(avg_t_iter /1e6/3600 * conf['num_iterations']))

        if (itr) % SUMMARY_INTERVAL:
            summary_writer.add_summary(summary_str, itr)

    tf.logging.info('Saving model.')
    saver.save(sess, conf['output_dir'] + '/model')
    tf.logging.info('Training complete')
    tf.logging.flush()


if __name__ == '__main__':
    tf.logging.set_verbosity(tf.logging.INFO)
    app.run()