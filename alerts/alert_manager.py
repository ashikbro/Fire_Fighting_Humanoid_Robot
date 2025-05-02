import pandas as pd
import smtplib
from email.mime.text import MIMEText
import time
import os
import logging
from automation.sensor_manager import SensorManager

PREDICTION_LOG = "alerts/prediction_logs.csv"
ALERT_THRESHOLD = 0.5  # Threshold probability to trigger alert

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class AlertManager:
    def __init__(self, email_sender, email_password, email_receiver):
        self.email_sender = email_sender
        self.email_password = email_password
        self.email_receiver = email_receiver
        self.sensor_manager = SensorManager()

    def check_and_send_alert(self):
        sensor_data = self.sensor_manager.poll_sensors()
        smoke_density = sensor_data.get("smoke_density", 0)
        fire_threshold = 150  # example threshold

        # Check latest prediction severity from log
        severity = self.get_latest_prediction_severity()
        alert_needed = False
        alert_message = ""

        if smoke_density >= fire_threshold:
            alert_needed = True
            alert_message += f"Smoke density threshold exceeded: {smoke_density} units.\n"

        if severity in ["Moderate", "Severe"]:
            alert_needed = True
            alert_message += f"Fire severity alert: {severity}.\n"

        if alert_needed:
            self.send_email_alert(alert_message.strip())

    def get_latest_prediction_severity(self):
        if not os.path.exists(PREDICTION_LOG):
            logging.warning(f"Prediction log file {PREDICTION_LOG} does not exist.")
            return None
        try:
            df = pd.read_csv(PREDICTION_LOG)
            if df.empty:
                logging.warning("Prediction log is empty.")
                return None
            # Assuming the latest prediction is the last row
            latest_severity = df.iloc[-1].get("FireSeverity", None)
            return latest_severity
        except Exception as e:
            logging.error(f"Error reading prediction log: {e}")
            return None

    def send_email_alert(self, message_body):
        subject = "Fire Alert Notification"
        body = f"Alert!\n\n{message_body}"
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.email_sender
        msg['To'] = self.email_receiver

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.email_sender, self.email_password)
                server.sendmail(self.email_sender, self.email_receiver, msg.as_string())
            logging.info("Alert email sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send alert email: {e}")

if __name__ == "__main__":
    alert_manager = AlertManager("sender@example.com", "password", "receiver@example.com")
    while True:
        alert_manager.check_and_send_alert()
        time.sleep(300)  # Check every 5 minutes
