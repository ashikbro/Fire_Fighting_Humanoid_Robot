import logging
from src.mqtt_client import MQTTClient
import time

class MQTTIntegration:
    def __init__(self, broker_address='localhost', broker_port=1883):
        self.mqtt_client = MQTTClient(broker_address=broker_address, broker_port=broker_port)
        self.mqtt_client.subscribe("firebot/commands", self.on_command_received)
        self.connected = False

    def start(self):
        while not self.connected:
            try:
                self.mqtt_client.connect()
                self.connected = True
                logging.info("MQTT integration started.")
            except Exception as e:
                logging.error(f"MQTT connection failed: {e}. Retrying in 5 seconds.")
                time.sleep(5)

    def stop(self):
        try:
            self.mqtt_client.disconnect()
            self.connected = False
            logging.info("MQTT integration stopped.")
        except Exception as e:
            logging.error(f"Error during MQTT disconnect: {e}")

    def on_command_received(self, message):
        logging.info(f"Received command: {message}")
        # Process commands here, e.g., control robot, request status, etc.

    def publish_alert(self, alert_message):
        try:
            self.mqtt_client.publish("firebot/alerts", alert_message)
            logging.info(f"Published alert: {alert_message}")
        except Exception as e:
            logging.error(f"Failed to publish alert: {e}")

if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO)
    mqtt_integration = MQTTIntegration(broker_address='test.mosquitto.org')
    mqtt_integration.start()
    try:
        while True:
            mqtt_integration.publish_alert("Test alert from FireBot")
            time.sleep(10)
    except KeyboardInterrupt:
        mqtt_integration.stop()
