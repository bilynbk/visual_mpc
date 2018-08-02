""" This file defines an agent for the MuJoCo simulator environment. """
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

from .general_agent import GeneralAgent

class CreateConfigAgent(GeneralAgent):
    def __init__(self, hyperparams):
        super().__init__(hyperparams)

    def rollout(self, policy, i_tr):

        # Take the sample.
        self.large_images_traj, self.traj_points= [], None
        obs = self._post_process_obs(self.env.reset(), True)
        agent_data, policy_outputs = {}, []
        agent_data['traj_ok'] = True

        for t in range(self._hyperparams['T']):
            self.env.move_arm()
            self.env.move_objects()
            try:
                obs = self._post_process_obs(self.env._get_obs(None))
            except ValueError:
                return {'traj_ok': False}, None, None

        return agent_data, obs, policy_outputs
