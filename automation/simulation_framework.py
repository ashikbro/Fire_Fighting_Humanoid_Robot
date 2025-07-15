import pygame
import numpy as np

class SimulationFramework:
    def __init__(self, width=800, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Fire Fighting Robot Simulation")
        self.robot_pose = (width // 2, height // 2, 0)
        self.obstacles = []
        self.fire_sources = []

    def add_obstacle(self, rect):
        self.obstacles.append(pygame.Rect(rect))

    def add_fire_source(self, pos, radius):
        self.fire_sources.append({'pos': pos, 'radius': radius})

    def update(self, robot_pose):
        self.robot_pose = robot_pose
        self.render()

    def render(self):
        self.screen.fill((255, 255, 255))  # White background
        # Draw robot
        pygame.draw.circle(self.screen, (0, 0, 255), self.robot_pose[:2], 10)
        # Draw obstacles
        for obs in self.obstacles:
            pygame.draw.rect(self.screen, (0, 0, 0), obs)
        # Draw fire sources
        for fire in self.fire_sources:
            pygame.draw.circle(self.screen, (255, 0, 0), fire['pos'], fire['radius'])
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            self.render()
        pygame.quit()

if __name__ == '__main__':
    sim = SimulationFramework()
    sim.add_obstacle((100, 100, 50, 50))
    sim.add_fire_source((400, 300), 20)
    sim.run()
