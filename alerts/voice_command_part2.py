def process_command(self, command):
        if command is None:
            self.speak("Sorry, I did not catch that. Please repeat.")
            return
        if "move forward" in command:
            self.speak("Moving forward")
            self.navigation_controller.move_forward(1)  # move 1 unit
        elif "turn left" in command:
            self.speak("Turning left")
            self.navigation_controller.turn_left()
        elif "turn right" in command:
            self.speak("Turning right")
            self.navigation_controller.turn_right()
        elif "stop" in command:
            self.speak("Stopping")
            self.navigation_controller.stop()
        elif "status" in command:
            self.speak("All systems operational")
        elif "help" in command:
            self.speak("You can say move forward, turn left, turn right, stop, or status.")
        else:
            self.speak("Command not recognized. Say help to hear available commands.")

    def voice_command_loop(self):
        self.running = True
        while self.running:
            command = self.listen()
            self.process_command(command)
            time.sleep(1)

    def start(self):
        self.thread = threading.Thread(target=self.voice_command_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

if __name__ == "__main__":
    from automation.navigation import NavigationController
    nav_controller = NavigationController()
    vci = VoiceCommandInterface(nav_controller)
    try:
        vci.start()
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        vci.stop()
