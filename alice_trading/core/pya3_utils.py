import sys
import logging
import datetime
import time

logger = logging.getLogger(__name__)

# --- PYA3 CORE MONKEY-PATCH ---
try:
    import pya3.alicebluepy
    from datetime import time as dt_time
    from time import sleep as t_sleep
    if hasattr(pya3.alicebluepy, 'time') and not callable(pya3.alicebluepy.time):
        pya3.alicebluepy.time = dt_time
    if not hasattr(pya3.alicebluepy, 'sleep'):
        pya3.alicebluepy.sleep = t_sleep
    logger.info("pya3 library patched successfully (time + sleep)")
except Exception as e:
    logger.warning(f"pya3 patch skipped: {e}")
# --- PYA3 CORE MONKEY-PATCH END ---

# Try to import Aliceblue
try:

    from pya3 import Aliceblue, Instrument
except ImportError:
    try:
        from alice_blue import AliceBlue as Aliceblue, Instrument
    except ImportError as e:
        logger.error(f"Failed to import Aliceblue: {e}")
        Aliceblue = None
        Instrument = None

# Centralized fallback logic for LiveFeedType in pya3
try:
    from pya3 import LiveFeedType
except ImportError:
    try:
        from alice_blue import LiveFeedType
    except ImportError:
        try:
            from pya3.alicebluepy import LiveFeedType
        except ImportError:
            class DummyLiveFeedType:
                MARKET_DATA = 1
                COMPACT = 2
                SNAPQUOTE = 3
            LiveFeedType = DummyLiveFeedType
            logger.warning("Could not import LiveFeedType. Using DummyLiveFeedType stub.")

__all__ = ["Aliceblue", "Instrument", "LiveFeedType"]
