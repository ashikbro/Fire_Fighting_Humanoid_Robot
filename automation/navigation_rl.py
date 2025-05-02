import numpy as np
import random

class NavigationRLAgent:
    """
    Reinforcement Learning agent for dynamic path planning and obstacle avoidance.
    This is a simplified example using Q-learning.
    """

    def __init__(self, state_size, action_size, learning_rate=0.1, discount_factor=0.95, exploration_rate=1.0, exploration_decay=0.995):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay
        self.q_table = {}

    def get_state_key(self, state):
        """
        Convert state to a hashable key for Q-table.
        """
        return tuple(state)

    def choose_action(self, state):
        """
        Choose an action based on epsilon-greedy policy.
        """
        state_key = self.get_state_key(state)
        if random.uniform(0, 1) < self.exploration_rate or state_key not in self.q_table:
            return random.randint(0, self.action_size - 1)  # Explore
        else:
            return np.argmax(self.q_table[state_key])  # Exploit

    def learn(self, state, action, reward, next_state):
        """
        Update Q-table based on the action taken and reward received.
        """
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)

        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_size)
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = np.zeros(self.action_size)

        predict = self.q_table[state_key][action]
        target = reward + self.discount_factor * np.max(self.q_table[next_state_key])
        self.q_table[state_key][action] += self.learning_rate * (target - predict)

        # Decay exploration rate
        self.exploration_rate *= self.exploration_decay
        self.exploration_rate = max(0.01, self.exploration_rate)

# Example usage:
# state_size = number of features representing the environment state
# action_size = number of possible movement actions (e.g., forward, left, right, stop)
