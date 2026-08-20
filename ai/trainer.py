# ============================================================
# ENTROPY - DQN Trainer
# ai\trainer.py
#
# WHAT THIS DOES:
# Trains the DQN model using the generated training data.
#
# TRAINING PROCESS:
# 1. Load training data (600 samples)
# 2. For each sample, create a simulated environment
# 3. Run DQN through the experience
# 4. Calculate reward (correct=positive, wrong=negative)
# 5. Train the network
# 6. Repeat for many episodes
# 7. Save the trained model
# ============================================================

import os
import sys
import json
import random
import numpy as np
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from ai.dqn_model import DQNAgent, FeatureExtractor

# ============================================================
# REWARD FUNCTION
# Defines what is good and bad behavior for the AI.
# ============================================================

def calculate_reward(action: int, true_label: int,
                     threat_score: float) -> float:
    """
    Calculate reward for the DQN action.

    REWARD TABLE:
    ─────────────────────────────────────────────────
    Situation                    │ Action  │ Reward
    ─────────────────────────────┼─────────┼────────
    Ransomware + Terminate       │ 2 or 3  │ +50
    Ransomware + Alert only      │ 1       │ +10
    Ransomware + Ignore          │ 0       │ -100
    Normal + Ignore              │ 0       │ +20
    Normal + Alert               │ 1       │ -10
    Normal + Terminate           │ 2 or 3  │ -50
    ─────────────────────────────────────────────────

    Args:
        action:      Action taken by DQN (0-3)
        true_label:  0=normal, 1=ransomware
        threat_score: 0-100 from entropy analysis

    Returns:
        Reward value (float)
    """

    is_ransomware = (true_label == 1)
    is_high_threat = (threat_score >= 70.0)

    if is_ransomware:
        # RANSOMWARE scenario
        if action == config.ACTION_TERMINATE_QUARANTINE:
            return 50.0    # Perfect response
        elif action == config.ACTION_TERMINATE:
            return 40.0    # Good response
        elif action == config.ACTION_ALERT:
            return 10.0    # Partial response (detected but not stopped)
        else:  # IGNORE
            return -100.0  # Catastrophic failure (missed ransomware)

    else:
        # NORMAL scenario
        if action == config.ACTION_IGNORE:
            return 20.0    # Correct (no false alarm)
        elif action == config.ACTION_ALERT:
            return -10.0   # Minor false positive (alert only)
        elif action == config.ACTION_TERMINATE:
            return -50.0   # Major false positive (killed normal process)
        else:  # TERMINATE + QUARANTINE
            return -80.0   # Severe false positive


# ============================================================
# TRAINING ENVIRONMENT
# Simulates the security environment for DQN training.
# ============================================================

class SecurityEnvironment:
    """
    Simulated security environment for DQN training.

    Generates states from training data.
    Returns rewards based on DQN actions.
    Tracks episode statistics.
    """

    def __init__(self, training_data: list):
        self.training_data   = training_data
        self.feature_extractor = FeatureExtractor()
        self.current_sample  = None
        self.step_count      = 0

    def reset(self) -> np.ndarray:
        """
        Start a new episode.
        Pick a random training sample as the current state.
        """
        self.current_sample = random.choice(self.training_data)
        self.step_count     = 0
        state = self.feature_extractor.extract_from_dict(
            self.current_sample
        )
        return state

    def step(self, action: int):
        """
        Take an action in the environment.

        Args:
            action: DQN's chosen action (0-3)

        Returns:
            (next_state, reward, done)
        """
        self.step_count += 1

        # Get true label and threat score
        true_label   = self.current_sample['label']
        threat_score = self._estimate_threat_score()

        # Calculate reward
        reward = calculate_reward(action, true_label, threat_score)

        # Episode is done after one action
        self.current_sample = random.choice(self.training_data)
        next_state  = self.feature_extractor.extract_from_dict(
            self.current_sample
        )

        return next_state, reward, True

    def _estimate_threat_score(self) -> float:
        """Estimate threat score from training sample features."""
        entropy = self.current_sample.get('entropy_score', 0)
        speed   = self.current_sample.get('files_per_sec', 0)
        delta   = self.current_sample.get('entropy_delta', 0)

        score = 0.0
        if entropy >= 7.5:
            score += 40
        if speed >= 5.0:
            score += 30
        if delta >= 2.0:
            score += 30

        return min(score, 100.0)


# ============================================================
# TRAINER
# Runs the training loop.
# ============================================================

class DQNTrainer:
    """
    Trains the DQN agent.

    TRAINING LOOP:
    ──────────────
    For each episode:
        1. Reset environment (pick random sample)
        2. Get state
        3. DQN selects action (epsilon-greedy)
        4. Environment returns reward
        5. Store experience
        6. Train on random batch from memory
        7. Track statistics
        8. Repeat

    After training:
        Save the model weights.
    """

    def __init__(self, training_data: list):
        self.training_data = training_data
        self.agent         = DQNAgent()
        self.env           = SecurityEnvironment(training_data)

    def train(self, num_episodes: int = 2000):
        """
        Run the training loop.

        Args:
            num_episodes: Number of training episodes
        """
        print()
        print("=" * 60)
        print("  ENTROPY - DQN Training")
        print("=" * 60)
        print(f"  Training samples : {len(self.training_data)}")
        print(f"  Episodes         : {num_episodes}")
        print(f"  Batch size       : {config.BATCH_SIZE}")
        print(f"  Learning rate    : {config.LEARNING_RATE}")
        print(f"  Device           : {self.agent.device}")
        print("=" * 60)
        print()

        # Training statistics
        episode_rewards  = []
        episode_actions  = []
        correct_decisions= 0
        total_decisions  = 0

        start_time = time.time()

        for episode in range(num_episodes):
            self.agent.episode = episode

            # Reset environment
            state = self.env.reset()
            episode_reward = 0.0

            # One step per episode
            # (each file event is one decision)
            action = self.agent.select_action(state, training=True)

            next_state, reward, done = self.env.step(action)

            # Store experience
            self.agent.store_experience(
                state, action, reward, next_state, done
            )

            # Train
            loss = self.agent.train_step()

            episode_reward = reward
            episode_rewards.append(episode_reward)
            episode_actions.append(action)

            # Track accuracy
            true_label = self.env.current_sample['label']
            is_correct = self._is_correct_action(action, true_label)
            if is_correct:
                correct_decisions += 1
            total_decisions += 1

            # Print progress every 100 episodes
            if (episode + 1) % 100 == 0:
                recent_reward = np.mean(episode_rewards[-100:])
                accuracy      = correct_decisions / max(total_decisions, 1)
                stats         = self.agent.get_stats()

                elapsed = time.time() - start_time
                eps_per_sec = (episode + 1) / elapsed

                print(f"  Episode {episode+1:5d}/{num_episodes} | "
                      f"Reward: {recent_reward:7.2f} | "
                      f"Accuracy: {accuracy:.1%} | "
                      f"Epsilon: {stats['epsilon']:.4f} | "
                      f"Loss: {stats['recent_loss']:.6f} | "
                      f"Memory: {stats['memory_size']:5d}")

                # Reset accuracy counter for next 100 episodes
                correct_decisions = 0
                total_decisions   = 0

        # Training complete
        elapsed = time.time() - start_time
        print()
        print("=" * 60)
        print("  Training Complete!")
        print("=" * 60)
        print(f"  Total episodes  : {num_episodes}")
        print(f"  Time taken      : {elapsed:.1f} seconds")
        print(f"  Final epsilon   : {self.agent.epsilon:.4f}")
        print(f"  Memory size     : {len(self.agent.memory)}")
        print()

        # Save the model
        self.agent.save()
        print("  Model saved successfully!")

        # Final evaluation
        self._evaluate()

        return self.agent

    def _is_correct_action(self, action: int,
                            true_label: int) -> bool:
        """Check if action was correct."""
        if true_label == 1:  # ransomware
            return action in [config.ACTION_TERMINATE,
                             config.ACTION_TERMINATE_QUARANTINE]
        else:  # normal
            return action in [config.ACTION_IGNORE,
                             config.ACTION_ALERT]

    def _evaluate(self, num_samples: int = 200):
        """
        Evaluate the trained model on test samples.
        Shows accuracy for normal and ransomware cases.
        """
        print()
        print("  Evaluation Results:")
        print("  " + "-" * 40)

        normal_correct    = 0
        ransom_correct    = 0
        normal_total      = 0
        ransom_total      = 0

        test_samples = random.sample(
            self.training_data,
            min(num_samples, len(self.training_data))
        )

        for sample in test_samples:
            state      = self.env.feature_extractor.extract_from_dict(
                sample
            )
            action     = self.agent.select_action(state, training=False)
            true_label = sample['label']

            if true_label == 0:  # normal
                normal_total += 1
                if action in [config.ACTION_IGNORE, config.ACTION_ALERT]:
                    normal_correct += 1
            else:  # ransomware
                ransom_total += 1
                if action in [config.ACTION_TERMINATE,
                             config.ACTION_TERMINATE_QUARANTINE]:
                    ransom_correct += 1

        normal_acc = normal_correct / max(normal_total, 1)
        ransom_acc = ransom_correct / max(ransom_total, 1)
        overall    = (normal_correct + ransom_correct) / max(
            normal_total + ransom_total, 1
        )

        print(f"  Normal files accuracy  : "
              f"{normal_correct}/{normal_total} = {normal_acc:.1%}")
        print(f"  Ransomware accuracy    : "
              f"{ransom_correct}/{ransom_total} = {ransom_acc:.1%}")
        print(f"  Overall accuracy       : {overall:.1%}")
        print()

        # Show sample decisions
        print("  Sample Decisions:")
        print("  " + "-" * 40)
        for sample in test_samples[:6]:
            state      = self.env.feature_extractor.extract_from_dict(
                sample
            )
            q_values   = self.agent.get_q_values(state)
            action     = int(np.argmax(q_values))
            true_label = sample['label']

            action_names = ['IGNORE', 'ALERT',
                           'TERMINATE', 'TERMINATE+QUARANTINE']
            label_names  = {0: 'NORMAL', 1: 'RANSOMWARE'}
            correct_mark = (
                '[OK]' if self._is_correct_action(action, true_label)
                else '[!!]'
            )

            print(f"  {correct_mark} "
                  f"True: {label_names[true_label]:10} | "
                  f"Action: {action_names[action]:25} | "
                  f"Entropy: {sample['entropy_score']:.2f}")


# ============================================================
# STANDALONE TRAINING SCRIPT
# ============================================================

if __name__ == "__main__":

    # Load training data
    training_file = os.path.join(
        config.TRAINING_DATA_DIR, "training_data.json"
    )

    if not os.path.exists(training_file):
        print(f"ERROR: Training data not found!")
        print(f"Expected: {training_file}")
        print()
        print("Run first:")
        print("  python data\\ransomware_simulator.py")
        print("  Choose option 5 (Generate training data)")
        sys.exit(1)

    print(f"Loading training data from:")
    print(f"  {training_file}")

    from data.training_schema import load_samples, validate_sample

    training_data = [s for s in load_samples(training_file) if validate_sample(s)]

    print(f"Loaded {len(training_data)} samples")

    # Count labels
    normal_count = sum(1 for d in training_data if d['label'] == 0)
    ransom_count = sum(1 for d in training_data if d['label'] == 1)
    print(f"  Normal    : {normal_count}")
    print(f"  Ransomware: {ransom_count}")

    # Train
    trainer = DQNTrainer(training_data)
    agent   = trainer.train(num_episodes=2000)

    print()
    print("Training complete!")
    print(f"Model saved to: {agent.model_path}")
    print()
    print("Next step: Run the full system with AI decisions")