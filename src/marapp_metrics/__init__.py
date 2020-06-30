import logging

# https://github.com/googleapis/google-api-python-client/issues/299
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.CRITICAL)
