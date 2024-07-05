
import logging

logger = logging.getLogger("linedify")
logger.setLevel(logging.INFO)
log_format = logging.Formatter("[%(levelname)s] %(asctime)s : %(message)s")
streamHandler = logging.StreamHandler()
streamHandler.setFormatter(log_format)
logger.addHandler(streamHandler)

from .integration import LineDifyIntegrator as LineDify
from .dify import DifyAgent, DifyType
