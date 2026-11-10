import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from automation.navigation_enhanced import NavigationEnhanced
from automation.slam_module import SLAMModule


@pytest.fixture
def slam():
    return SLAMModule(map_size=(50, 50), resolution=1.0)


def test_slam_update_and_position(slam):
    slam.update(np.array([1.0, 0.8, 0.6, 0.4, 0.5]))
    position, orientation = slam.get_position()
    assert isinstance(position, np.ndarray)
    assert position.shape == (2,)
    assert isinstance(orientation, float)
    assert slam.get_map().shape == (50, 50)


def test_a_star_reaches_goal_from_slam_position(slam):
    navigation = NavigationEnhanced(grid_size=(50, 50))
    slam.update(np.array([1.0, 0.9, 0.8]))
    position, _ = slam.get_position()
    navigation.current_position = tuple(int(round(c)) for c in position)

    goal = (navigation.current_position[0] + 5, navigation.current_position[1] + 5)
    navigation.set_goal(*goal)
    path = navigation.a_star_search()

    assert len(path) >= 2
    assert path[0] == navigation.current_position
    assert path[-1] == goal


def test_a_star_avoids_obstacles():
    navigation = NavigationEnhanced(grid_size=(10, 10))
    # Wall at x == 2 with a single gap at y == 5
    navigation.grid[2, :] = 1
    navigation.grid[2, 5] = 0
    navigation.set_goal(4, 0)

    path = navigation.a_star_search()

    assert path[0] == (0, 0)
    assert path[-1] == (4, 0)
    assert (2, 5) in path
    assert all(navigation.grid[x, y] == 0 for x, y in path)


def test_a_star_without_goal_returns_empty():
    assert NavigationEnhanced().a_star_search() == []
