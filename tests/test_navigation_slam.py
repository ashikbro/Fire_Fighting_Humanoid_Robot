import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from automation.navigation_enhanced import NavigationEnhanced


def _assert_valid_path(nav, path, start, goal):
    assert path, "expected a non-empty path"
    assert path[0] == start
    assert path[-1] == goal
    for a, b in zip(path, path[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, f"non-adjacent step {a} -> {b}"
    for x, y in path:
        assert nav.grid[x, y] == 0, f"path passes through obstacle at {(x, y)}"


def test_ranges_project_to_cells_relative_to_current_position():
    nav = NavigationEnhanced(grid_size=(20, 20))
    nav.current_position = (5, 5)
    # Four beams at 0, 90, 180, 270 degrees, each 2 m away.
    cells = nav.ranges_to_cells([2.0, 2.0, 2.0, 2.0], nav.lidar_angles(4))
    assert cells == {(7, 5), (5, 7), (3, 5), (5, 3)}


def test_invalid_off_grid_and_own_cell_readings_are_ignored():
    nav = NavigationEnhanced(grid_size=(10, 10), max_range=10.0)
    nav.current_position = (5, 5)
    angles = np.zeros(6)
    # nan, zero, negative, beyond max_range, off-grid (x=13), own cell (0.2 m)
    cells = nav.ranges_to_cells([np.nan, 0.0, -1.0, 12.0, 8.0, 0.2], angles)
    assert cells == set()


def test_update_sensors_with_real_data_then_a_star_routes_around_obstacles():
    nav = NavigationEnhanced(grid_size=(20, 20), resolution=1.0, max_range=10.0)
    nav.current_position = (5, 5)
    nav.set_goal(10, 5)

    # LIDAR: 4 beams (0/90/180/270 deg) -> obstacle 2 cells away in each direction.
    lidar_data = [2.0, 2.0, 2.0, 2.0]
    # Ultrasonic: 3 sensors at -45/0/+45 deg; only the centre one has a return.
    ultrasonic_data = [np.inf, 3.0, 15.0]
    camera_data = [0.5, 0.3]

    nav.update_sensors(lidar_data, ultrasonic_data, camera_data)

    expected = {(7, 5), (5, 7), (3, 5), (5, 3), (8, 5)}
    occupied = {tuple(c) for c in np.argwhere(nav.grid == 1)}
    assert occupied == expected

    path = nav.a_star_search()
    _assert_valid_path(nav, path, start=(5, 5), goal=(10, 5))
    # Straight line along y=5 is blocked, so the path must detour.
    assert len(path) > 6


def test_update_sensors_with_original_failing_inputs_does_not_raise():
    # These inputs previously raised IndexError in update_grid_with_obstacles.
    nav = NavigationEnhanced()
    nav.current_position = (10, 10)
    nav.set_goal(15, 15)
    nav.update_sensors([1.0, 0.9, 0.8], [1.0, 0.9], [0.5, 0.3])
    assert nav.grid.sum() > 0
    path = nav.a_star_search()
    _assert_valid_path(nav, path, start=(10, 10), goal=(15, 15))


def test_a_star_returns_empty_when_goal_is_walled_off():
    nav = NavigationEnhanced(grid_size=(20, 20))
    nav.current_position = (5, 5)
    nav.set_goal(10, 10)
    # Dense 360-degree sweep at 1 m surrounds the robot on all 4 neighbours.
    nav.update_sensors(lidar_data=[1.0] * 36)
    assert nav.a_star_search() == []
