
import cv2
import numpy as np
import pickle as pkl

import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from python_visual_mpc.video_prediction.basecls.utils.get_designated_pix import Getdesig
import os
import python_visual_mpc

ROOT_DIR = os.path.abspath(python_visual_mpc.__file__)
ROOT_DIR = '/'.join(str.split(ROOT_DIR, '/')[:-2])

def annotate(exp_dir):
    num_runs = 1

    scores_l = []
    improvements_l = []
    initial_dists_l = []

    for n in range(num_runs):
        exp_dir + '/videos/' +

        desig_pix_t0 = pkl.load(open('points.pkl', 'rb'))
        goal_pix = pkl.load(open('points.pkl', 'rb'))

        start_image =
        goal_image =
        final_image = cv2.imread()

        c = Getdesig(final_image)
        final_pos = np.round(c.coords).astype(np.int)

        final_dist = np.linalg.norm(goal_pix - final_pos)
        initial_dist = np.linalg.norm(desig_pix_t0 - goal_pix)
        improvement = initial_dist - final_dist

        scores_l.append(final_dist)
        improvements_l.append(improvement)
        initial_dists_l.append(initial_dist)

        ann_stats = {'initial_dist': initial_dists_l, 'improvments':improvements_l, 'scores':scores_l}
        pkl.dump(ann_stats, open(exp_dir + '/ann_stats.pkl','wb'))

    write(exp_dir, ann_stats)

def write(exp_dir, stat):
    improvement = stat['improvement']

    scores = stat['scores']
    if 'initial_dist' in stat:
        initial_dist = stat['initial_dist']
    else:
        initial_dist = None

    sorted_ind = improvement.argsort()[::-1]

    mean_imp = np.mean(improvement)
    med_imp = np.median(improvement)
    mean_dist = np.mean(scores)
    med_dist = np.median(scores)

    lifted = stat['lifted'].astype(np.int)

    result_file = exp_dir + '/result.'
    f = open(result_file, 'w')
    f.write('---\n')
    f.write('overall best pos improvement: {0} of traj {1}\n'.format(improvement[sorted_ind[0]], sorted_ind[0]))
    f.write('overall worst pos improvement: {0} of traj {1}\n'.format(improvement[sorted_ind[-1]], sorted_ind[-1]))
    f.write('average pos improvemnt: {0}\n'.format(mean_imp))
    f.write('median pos improvement {}'.format(med_imp))
    f.write('standard error of the mean (SEM) {0}\n'.format(np.std(improvement) / np.sqrt(improvement.shape[0])))
    f.write('---\n')
    f.write('average pos score: {0}\n'.format(mean_dist))
    f.write('median pos score {}'.format(med_dist))
    f.write('standard error of the mean (SEM) {0}\n'.format(np.std(scores) / np.sqrt(scores.shape[0])))
    f.write('---\n')
    f.write('mean imp, med imp, mean dist, med dist {}, {}, {}, {}\n'.format(mean_imp, med_imp, mean_dist, med_dist))
    f.write('---\n')
    f.write('average initial dist: {0}\n'.format(np.mean(initial_dist)))
    f.write('median initial dist: {0}\n'.format(np.median(initial_dist)))
    f.write('----------------------\n')
    f.write('traj: improv, score, term_t, lifted, rank\n')
    f.write('----------------------\n')

    for n in range(improvement.shape[0]):
        f.write('{}: {}, {}, {}:{}\n'.format(n, improvement[n], scores[n], lifted[n],
                                                 np.where(sorted_ind == n)[0][0]))
    f.close()


if __name__ == '__main__':

    annotate()
