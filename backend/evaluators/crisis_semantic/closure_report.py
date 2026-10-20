"""Current offline step-8 report; prior delivery retained in documentation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.final8_report import build

if __name__=='__main__':build()
