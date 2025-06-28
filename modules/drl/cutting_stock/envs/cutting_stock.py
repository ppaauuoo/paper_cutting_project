import gymnasium as gym
from gymnasium import spaces
import numpy as np

class CuttingStockEnv(gym.Env):
    """A Gymnasium environment for the 1D Cutting Stock Problem."""
    
    def __init__(self, W, required_widths):
        """
        Initialize the environment.
        
        Args:
            W (float): Width of each stock piece.
            required_widths (list): List of required widths to cut.
        """
        super(CuttingStockEnv, self).__init__()
        self.W = float(W)
        self.required_widths = np.array(required_widths, dtype=np.float32)
        self.n = len(required_widths)
        
        # Action space: select one of the n required widths
        self.action_space = spaces.Discrete(self.n)
        
        # Observation space: [remaining_width/W, selected, action_mask]
        self.observation_space = spaces.Box(
            low=0, high=1, shape=(1 + self.n,), dtype=np.float32
        )
        
        # Verify all required widths are feasible
        if np.any(self.required_widths > self.W):
            raise ValueError("All required widths must be <= stock width W")
        
        # Init assignemnts
        self.assignments = []
        self.current_assignment = []

    def reset(self, seed=None, options=None):
        """
        Reset the environment to the initial state.
        
        Returns:
            observation (np.ndarray): Initial observation.
            info (dict): Additional info.
        """
        super().reset(seed=seed)
        self.remaining_width = self.W
        #init [0,0,0,0,0,0]
        self.selected = np.zeros(self.n, dtype=int)
        #mask only the one that can be include.
        # [1,0,0,0,1,0,0,0,1]
        self.action_mask = np.array(
            [1 if self.required_widths[i] <= self.remaining_width else 0 
             for i in range(self.n)], 
            dtype=int
        )
        self.assignments = []
        self.current_assignment = []
        observation = self._get_observation()
        return observation, {}

    def step(self, action):
        """
        Take a step in the environment.
        
        Args:
            action (int): Index of the required width to cut.
            
        Returns:
            observation (np.ndarray): Next observation.
            reward (float): Reward for the action.
            done (bool): Whether the episode is finished.
            truncated (bool): Whether the episode was truncated (not used).
            info (dict): Additional info.
        """
        #if action(widths) is too much, exit.
        if self.action_mask[action] == 0:
            done = True
            raise ValueError(f"Action {action} is invalid in current state")
        
        
        # Apply the action
        self.current_assignment.append(action)
        self.selected[action] = 1
        self.remaining_width -= self.required_widths[action]
        reward = 0
        done = False
        
        # Check if all widths are cut
        # [1,1,1,1,1,1]
        if np.all(self.selected):
            done = True
            self.assignments.append(self.current_assignment)
            reward = -1
        else:
            # Check if any widths can still be cut
            # save index if it selectable [i,i,i]
            valid_actions = [
                i for i in range(self.n) 
                if self.selected[i] == 0 and self.required_widths[i] <= self.remaining_width
            ]
            # in case nothing was selectable
            # small reset but save the selected
            if not valid_actions:
                self.assignments.append(self.current_assignment)
                self.current_assignment = []
                self.remaining_width = self.W
                reward = -1
        
        # Update action mask
        self.action_mask = np.array(
            [1 if self.selected[i] == 0 and self.required_widths[i] <= self.remaining_width 
             else 0 for i in range(self.n)], 
            dtype=int
        )
        
        observation = self._get_observation()
        return observation, reward, done, False, {}

    def _get_observation(self):
        """
        Get the current observation.
        
        Returns:
            np.ndarray: Concatenated array of [remaining_width/W, selected, action_mask].
        """
        return np.concatenate(
            [[self.remaining_width / self.W], self.selected],
            dtype=np.float32
        )
    
    def action_masks(self):
            return self.action_mask
        
    def render(self, mode="human"):
        """
        Render the environment.
        
        Args:
            mode (str): Rendering mode. Only 'human' is supported.
        """
        if mode == "human":
            print("Stock pieces used so far:")
            for i, assignment in enumerate(self.assignments, 1):
                widths = [self.required_widths[j] for j in assignment]
                print(f"  Stock piece {i}: {widths}")
            print("Current stock piece:")
            current_widths = [self.required_widths[j] for j in self.current_assignment]
            print(f"  {current_widths}, remaining length: {self.remaining_length}")
            remaining_widths = [self.required_widths[i] for i in range(self.n) if self.selected[i] == 0]
            print(f"Remaining widths to cut: {remaining_widths}")
            available_actions = [self.required_widths[i] for i in range(self.n) if self.action_mask[i] == 1]
            print(f"Available actions: {available_actions}")
        else:
            raise NotImplementedError("Only human mode is supported")
