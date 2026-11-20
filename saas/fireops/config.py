"""Runtime configuration, read from environment variables."""
import os
import secrets


class Settings:
    def __init__(self) -> None:
        self.database_path = os.getenv("FIREOPS_DB", "fireops.db")
        # A random secret is generated per process when none is configured.
        # Set FIREOPS_SECRET in production so tokens survive restarts.
        self.jwt_secret = os.getenv("FIREOPS_SECRET") or secrets.token_urlsafe(48)
        self.jwt_ttl_minutes = int(os.getenv("FIREOPS_JWT_TTL", "720"))
        self.enable_simulator = os.getenv("FIREOPS_SIMULATOR", "1") == "1"
        self.simulator_interval = float(os.getenv("FIREOPS_SIM_INTERVAL", "2.0"))
        self.webhook_timeout = float(os.getenv("FIREOPS_WEBHOOK_TIMEOUT", "5"))


# Subscription plans: robot limits and monthly telemetry quotas.
PLANS = {
    "free": {"name": "Free", "price": 0, "max_robots": 3, "max_users": 3,
             "telemetry_per_month": 50_000, "webhooks": False},
    "pro": {"name": "Pro", "price": 199, "max_robots": 25, "max_users": 25,
            "telemetry_per_month": 2_000_000, "webhooks": True},
    "enterprise": {"name": "Enterprise", "price": 999, "max_robots": 10_000, "max_users": 10_000,
                   "telemetry_per_month": 100_000_000, "webhooks": True},
}

settings = Settings()
