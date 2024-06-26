#  Copyright (c) 2022-2023.
#  ProrokLab (https://www.proroklab.org/)
#  All rights reserved.

import torch, random

from vmas.simulator.core import World, Agent, Landmark
from vmas.simulator.scenario import BaseScenario


class Scenario(BaseScenario):
    def make_world(self, batch_dim: int, device: torch.device, **kwargs):
        world = World(batch_dim=batch_dim, device=device, dim_c=10)

        n_agents = 2
        n_landmarks = 3

        # Add agents
        for i in range(n_agents):
            agent = Agent(name=f"agent_{i}", collide=False, silent=False)
            world.add_agent(agent)
        # Add landmarks
        for i in range(n_landmarks):
            landmark = Landmark(
                name=f"landmark {i}",
                collide=False,
            )
            world.add_landmark(landmark)

        return world

    def reset_world_at(self, env_index: int = None):
        if env_index is None:
            # assign goals to agents
            for agent in self.world.agents:
                agent.goal_a = None
                agent.goal_b = None
            # want other agent to go to the goal landmark
            self.world.agents[0].goal_a = self.world.agents[1]
            self.world.agents[0].goal_b = self.world.landmarks[
                torch.randint(0, len(self.world.landmarks), (1,)).item()
            ]
            self.world.agents[1].goal_a = self.world.agents[0]
            self.world.agents[1].goal_b = self.world.landmarks[
                torch.randint(0, len(self.world.landmarks), (1,)).item()
            ]
            # random properties for agents
            for i, agent in enumerate(self.world.agents):
                agent.color = torch.tensor(
                    [0.25, 0.25, 0.25], device=self.world.device, dtype=torch.float32
                )
            # random properties for landmarks
            colors = [
                torch.tensor(
                    [0.75, 0.25, 0.25], device=self.world.device, dtype=torch.float32
                ), 
                torch.tensor(
                    [0.25, 0.75, 0.25], device=self.world.device, dtype=torch.float32
                ),
                torch.tensor(
                    [0.25, 0.25, 0.75], device=self.world.device, dtype=torch.float32
                )
            ]
            # random.shuffle(colors)
            self.world.landmarks[0].color = colors[0]
            self.world.landmarks[1].color = colors[1]
            self.world.landmarks[2].color = colors[2]
            # special colors for goals
            self.world.agents[0].goal_a.color = self.world.agents[0].goal_b.color
            self.world.agents[1].goal_a.color = self.world.agents[1].goal_b.color

        # set random initial states
        for idx, agent in enumerate(self.world.agents):
            agent.set_pos(
                torch.zeros(
                    (1, self.world.dim_p)
                    if env_index is not None
                    else (self.world.batch_dim, self.world.dim_p),
                    device=self.world.device,
                    dtype=torch.float32,
                ).uniform_(
                    -1.0,
                    1.0,
                ),
                batch_index=env_index,
            )
            if idx==0:
                agent.ref_frame = torch.Tensor([[0.4973, 0.3819],[0.0203, 0.8856]]).unsqueeze(0).repeat(self.world.batch_dim, 1, 1)
            elif idx==1: 
                agent.ref_frame = torch.Tensor([[0.7729, 0.8743],[0.1327, 0.7566]]).unsqueeze(0).repeat(self.world.batch_dim, 1, 1)
            else:
                print("NO REFERENCE FRAME FOR "+self.name+" AS THERE ARE MORE THAN TWO AGENTS")
            
        for landmark in self.world.landmarks:
            landmark.set_pos(
                torch.zeros(
                    (1, self.world.dim_p)
                    if env_index is not None
                    else (self.world.batch_dim, self.world.dim_p),
                    device=self.world.device,
                    dtype=torch.float32,
                ).uniform_(
                    -1.0,
                    1.0,
                ),
                batch_index=env_index,
            )

    def reward(self, agent: Agent):
        is_first = agent == self.world.agents[0]
        if is_first:
            self.rew = torch.zeros(self.world.batch_dim, device=self.world.device)
            for a in self.world.agents:
                if a.goal_a is None or a.goal_b is None:
                    return torch.zeros(
                        self.world.batch_dim,
                        device=self.world.device,
                        dtype=torch.float32,
                    )
                self.rew += -torch.sqrt(
                    torch.sum(
                        torch.square(a.goal_a.state.pos - a.goal_b.state.pos), dim=-1
                    )
                )
        return self.rew

    def observation(self, agent: Agent):
        # goal color
        goal_color = agent.goal_b.color

        # get positions of all entities in this agent's reference frame
        entity_pos = []
        entity_cols = []
        for entity in self.world.landmarks:
            entity_pos.append(
                torch.bmm(
                    agent.ref_frame,
                    (entity.state.pos - agent.state.pos).unsqueeze(2)
                ).squeeze(2)
            )
            color = torch.Tensor(entity.color)
            entity_cols.append(
                color.repeat(self.world.batch_dim, 1)
            )

        # communication of all other agents
        comm = []
        external_noise = torch.randn(torch.Size(agent.state.c.shape))
        for other in self.world.agents:
            if other is agent:
                continue
            loc_noise = agent.noise.sample(sample_shape=torch.Size(agent.state.c.shape)).squeeze(dim = 2) if agent.noise != None else 0.0
            comm.append(other.state.c + loc_noise/2 + external_noise*.8)
        return torch.cat(
            [
                agent.state.vel,
                *entity_pos,
                # *entity_cols,
                goal_color.repeat(self.world.batch_dim, 1),
                *comm,
            ],
            dim=-1,
        )
