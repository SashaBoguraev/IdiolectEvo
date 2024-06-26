#  Copyright (c) Meta Platforms, Inc. and affiliates.
#
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.
#

from typing import Callable, Dict, List, Optional

from torchrl.data import CompositeSpec
from torchrl.envs import EnvBase
from torchrl.envs.libs.vmas import VmasEnv

from benchmarl.environments.common import Task
from benchmarl.utils import DEVICE_TYPING


class IdiolectEvoTask(Task):
    SPEED_OLD = None
    SPEED_OLD_NOISE = None
    SPEED_OLD_MEM_BUFFER = None
    SPEED_OLD_NOISE_MEM = None
    SPEED_OLD_CONST = None
    SPEED_OLD_NOISE_CONST = None
    SPEED_NEW = None
    SPEED_NEW_NOISE = None
    SPEED_NEW_MEM_BUFFER = None
    SPEED_NEW_NOISE_MEM = None
    NOVEL_COORD = None
    NOVEL_COORD_NOISE = None
    NOVEL_COORD_NOVEL_COLOR = None
    NOVEL_COORD_NOVEL_COLOR_NOISE = None
    ADAPT_COLOR_0 = None
    ADAPT_COLOR_1 = None
    ADAPT_COLOR_2 = None
    ADAPT_COLOR_3 = None
    ADAPT_COLOR_4 = None
    ADAPT_COLOR_5 = None
    ADAPT_COLOR_6 = None
    ADAPT_COLOR_7 = None
    ADAPT_COLOR_8 = None
    ADAPT_COLOR_9 = None
    ADAPT_COLOR_NOISE_0 = None
    ADAPT_COLOR_NOISE_1 = None
    ADAPT_COLOR_NOISE_2 = None
    ADAPT_COLOR_NOISE_3 = None
    ADAPT_COLOR_NOISE_4 = None
    ADAPT_COLOR_NOISE_5 = None
    ADAPT_COLOR_NOISE_6 = None
    ADAPT_COLOR_NOISE_7 = None
    ADAPT_COLOR_NOISE_8 = None
    ADAPT_COLOR_NOISE_9 = None

    def get_env_fun(
        self,
        num_envs: int,
        continuous_actions: bool,
        seed: Optional[int],
        device: DEVICE_TYPING,
    ) -> Callable[[], EnvBase]:
        return lambda: VmasEnv(
            scenario=self.name.lower(),
            num_envs=num_envs,
            continuous_actions=continuous_actions,
            seed=seed,
            device=device,
            categorical_actions=True,
            **self.config,
        )

    def supports_continuous_actions(self) -> bool:
        return True

    def supports_discrete_actions(self) -> bool:
        return True

    def has_render(self, env: EnvBase) -> bool:
        return True

    def max_steps(self, env: EnvBase) -> int:
        return self.config["max_steps"]

    def group_map(self, env: EnvBase) -> Dict[str, List[str]]:
        return {"agents": [agent.name for agent in env.agents]}

    def state_spec(self, env: EnvBase) -> Optional[CompositeSpec]:
        return None

    def action_mask_spec(self, env: EnvBase) -> Optional[CompositeSpec]:
        return None

    def observation_spec(self, env: EnvBase) -> CompositeSpec:
        observation_spec = env.unbatched_observation_spec.clone()
        if "info" in observation_spec["agents"]:
            del observation_spec[("agents", "info")]
        return observation_spec

    def info_spec(self, env: EnvBase) -> Optional[CompositeSpec]:
        info_spec = env.unbatched_observation_spec.clone()
        del info_spec[("agents", "observation")]
        if "info" in info_spec["agents"]:
            return info_spec
        else:
            return None

    def action_spec(self, env: EnvBase) -> CompositeSpec:
        return env.unbatched_action_spec

    @staticmethod
    def env_name() -> str:
        return "idiolectevo"
