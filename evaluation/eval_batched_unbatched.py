from eval import *

def run_benchmark(task, PATH, seed):
    # Loads from "benchmarl/conf/experiment/base_experiment.yaml"
    experiment_config = ExperimentConfig.get_from_yaml()

    # You can override from the script
    experiment_config.train_device = "cpu"  # Change the training device
    experiment_config.off_policy_n_envs_per_worker = 10_000
    experiment_config.off_policy_collected_frames_per_batch = 1_000_000
    experiment_config.max_n_frames = 1_000_000
    experiment_config.evaluation = False
    experiment_config.render = False
    experiment_config.loggers = []
    experiment_config.checkpoint_interval = 100_000_000

    # Some basic other configs
    algorithm_config = MaddpgConfig.get_from_yaml()
    model_config = MlpConfig.get_from_yaml()
    critic_model_config = MlpConfig.get_from_yaml()

    experiment = Experiment(
        algorithm_config = algorithm_config,
        task = task,
        seed = seed,
        config = experiment_config,
        model_config = model_config,
        critic_model_config = critic_model_config
    )

    x = torch.load(PATH)

    policy = experiment.algorithm.get_policy_for_collection()
    policy.load_state_dict(x['collector']['policy_state_dict'])
    experiment.policy = policy
    experiment.run(eval = True)
    reward = experiment.reward
    episode_reward = experiment.episode_reward

    stats, mean_stats, to_graphs = process_rewards(reward, episode_reward)

    return stats, mean_stats, to_graphs

def process_rewards(reward, episode_reward):
    # Get the individual rewards for each environment
    reward = torch.squeeze(reward, -1)[:,:,0]
    max_rewards, _ = torch.max(reward.clone().detach(), dim=1, keepdim=True)
    min_rewards, _ = torch.min(reward.clone().detach(), dim=1, keepdim=True)
    mean_rewards = torch.mean(reward.clone().detach(), dim=1, keepdim=True)

    # Find the last time the rewards dip under a certain threshold (speed)
    def find_speed(row, threshold):
        out = float('nan')
        for idx, val in enumerate(row):
            if (-1*val)<threshold:
                return idx
        return float('nan')
    
    # Return the speed for each row
    speed_data = map(lambda row: find_speed(row, threshold=.2), reward.clone().detach())
    speed_tensor = torch.Tensor(list(speed_data))
    speed_length = torch.sum(torch.isnan(speed_tensor)).item()

    thresholds = []
    num_nans = []
    speed_means = []

    num_steps = 20

    for step in np.linspace(0, 2, num_steps):
        # thresh = thresh - i*inc
        speed = map(lambda row: find_speed(row, threshold=step), reward.clone().detach())
        speed = torch.Tensor(list(speed))
        speed_mean = np.nanmean(speed)
        num_nan = torch.sum(torch.isnan(speed)).item()

        thresholds.append(step)
        num_nans.append(num_nan)
        speed_means.append(speed_mean)

    # Get Unique Episode Rewards
    episode_reward = episode_reward[::2]

    stats = {
        "Max Rewards": max_rewards.squeeze(),
        "Min Rewards": min_rewards.squeeze(),
        "Mean Rewards": mean_rewards.squeeze(),
        "Episode Rewards": episode_reward,
        "Speeds": speed_tensor,
        "Speed Length": speed_length
    }

    mean_stats = {
        "Max Rewards": max_rewards.squeeze().mean().item(),
        "Min Rewards": min_rewards.squeeze().mean().item(),
        "Mean Rewards": mean_rewards.squeeze().mean().item(),
        "Episode Rewards": episode_reward.mean().item(),
        "Speeds": np.nanmean(speed_tensor),
        "Num Nans": speed_length
    }

    to_graphs = {
        "thresholds": thresholds,
        "num nans": num_nans,
        "speed means": speed_means
    }

    return stats, mean_stats, to_graphs

def compare_environments(eval_one, eval_two, alt):
    keys = eval_one.keys()
    p_vals = []
    for idx, key in enumerate(keys):
        if idx < 5:
            data_one = eval_one[key].tolist()
            data_two = eval_two[key].tolist()
            stat, p = ttest_ind(data_one, data_two, alternative=alt, nan_policy='omit')
            p_vals.append(p)    
    return p_vals

def write_csv(filename, data, arrays=True):
    with open(filename, 'w+', newline='') as csvfile:
        fieldnames = list(data.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        if arrays:
            for i in range(len(data[fieldnames[0]])):
                row_data = {field: data[field][i] for field in fieldnames}
                writer.writerow(row_data)
        else:
            row_data = {field: data[field] for field in fieldnames}
            writer.writerow(row_data)

def eval_pairs(pairs, out_dict):
    for pair in pairs:
        first = pair[0]
        second = pair[1]
        p_less = compare_environments(first, second, 'less')
        p_greater = compare_environments(first, second, 'greater')
        out_dict["less"].append(p_less)
        out_dict["greater"].append(p_greater)

def graph_data(datasets, titles, type):

    title = type+" Environments"
    threshold = datasets[0]["thresholds"]

    fig, axs = plt.subplots(2, figsize=(15, 15))
    axs[0].set_title('Speed')
    axs[0].set(xlabel='Negative Threshold', ylabel='Speed')
    axs[1].set_title('Number of Incompletions')
    axs[1].set(xlabel='Negative Threshold', ylabel='Number of Incompletions')

    for idx, data in enumerate(datasets):
        nan = data["num nans"]
        speed = data["speed means"]

        label = titles[idx]

        axs[0].plot(threshold, speed, label=label)
        axs[1].plot(threshold, nan, label=label)
    
    axs[0].legend()
    axs[1].legend()

    save_path = type+'_graph.png'
    plt.savefig(save_path)

def generate_data(paths, seed):
    # Get Paths
    batched = paths[0]
    unbatched = paths[1]

    # Get Stats for old environment
    batched_old, batched_old_means, batched_old_graphs = run_benchmark(IdiolectEvoTask.SPEED_OLD.get_from_yaml(), batched, seed)
    unbatched_old, unbatched_old_means, unbatched_old_graphs = run_benchmark(IdiolectEvoTask.SPEED_OLD.get_from_yaml(), unbatched, seed)
    old_evals = [batched_old, unbatched_old]
    old_pair = [(batched_old, unbatched_old)]
    old_graphs = [batched_old_graphs, unbatched_old_graphs]

    # Get Stats for new environment
    batched_new, batched_new_means, batched_new_graphs = run_benchmark(IdiolectEvoTask.SPEED_NEW.get_from_yaml(), batched, seed)
    unbatched_new, unbatched_new_means, unbatched_new_graphs = run_benchmark(IdiolectEvoTask.SPEED_NEW.get_from_yaml(), unbatched, seed)
    new_evals = [batched_new, unbatched_new]
    new_pair = [(batched_new, unbatched_new)]
    new_graphs = [batched_new_graphs, unbatched_new_graphs]

    titles = ["Batched", "Unbatched"]

    # Initialize the dictionaries for all p-values
    p_vals_old = {
        "Titles": titles,
        "less": [],
        "greater": []
    }
    p_vals_new = {
        "Titles": titles,
        "less": [],
        "greater": []
    }

    # Populate P-Value Dictionaries
    eval_pairs(old_pair, p_vals_old)
    eval_pairs(new_pair, p_vals_new)

    # Initialize the dictionaries for all means
    means_old = {
        "batched": batched_old_means,
        "unbatched": unbatched_old_means,
    }
    means_new = {
        "batched": batched_new_means,
        "unbatched": unbatched_new_means,
    }
    
    # Write results to files
    output_folder = '/Users/sashaboguraev/Desktop/Cornell/College Scholar/BenchMARL/evaluation/stats/batched-unbatched'
    write_csv(os.path.join(output_folder, 'p_vals_old_seed'+str(seed)+'.csv'), p_vals_old)
    write_csv(os.path.join(output_folder, 'p_vals_new'+str(seed)+'.csv'), p_vals_new)
    write_csv(os.path.join(output_folder, 'means_old'+str(seed)+'.csv'), means_old, False)
    write_csv(os.path.join(output_folder, 'means_new'+str(seed)+'.csv'), means_new, False)

    # Graph Data
    graph_data(old_graphs, titles, "Old_seed"+str(seed))
    graph_data(new_graphs, titles, "Novel_seed"+str(seed))

if __name__ == "__main__":
    # Checkpoint paths
    universal_batched = "evaluation/checkpoints/batched-unbatched/batched.pt"
    universal_unbatched = "evaluation/checkpoints/batched-unbatched/unbatched.pt"

    # Seed
    seeds = 10

    # Generate Everything
    for seed in range(seeds):
        print("SEED ", seed)
        seed = seed + 10
        generate_data(sim_paths, seed)