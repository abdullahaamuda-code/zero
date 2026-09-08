# Zero Voice Engine // Brain Seam
"""Zero's Brain — manages the persistent autonomous LLM session."""

import os
from backtalk.config import CFG
from backtalk.zcode_brain import ZcodeBrain

SESSION_FILE = os.path.join(CFG["signals_dir"], ".backtalk_session")

# Re-export ZcodeBrain as WarmBrain for the voice line
WarmBrain = ZcodeBrain
