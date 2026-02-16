"""App package: configures logging for app.* so tool/data calls are visible."""
import logging

logging.getLogger("app").setLevel(logging.INFO)
