import logging

class AlertManager:
    def __init__(self, sender_email=None, password=None, receiver_email=None):
        self.sender_email = sender_email
        self.password = password
        self.receiver_email = receiver_email

    def send_alert(self, message):
        logging.info(f"ALERT: {message}")
        # In a real implementation, this would send an email or SMS
        pass