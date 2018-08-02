from python_visual_mpc.visual_mpc_core.envs.mujoco_env.sawyer_sim.base_sawyer_mujoco_env import BaseSawyerMujocoEnv
import copy

class VanillaSawyerMujocoEnv(BaseSawyerMujocoEnv):
    def __init__(self, env_params):
        self._hyper = copy.deepcopy(env_params)
        super().__init__(**env_params)
        self._adim, self._sdim = self._base_adim, self._base_sdim

    def _init_dynamics(self):
        return

    def _next_qpos(self, action):
        return self._previous_target_qpos * self.mode_rel + action