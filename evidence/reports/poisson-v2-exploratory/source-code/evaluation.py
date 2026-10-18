"""Paper arithmetic is separate from bookmaker settlement and model labels."""
import math
from data import utc


def in_decision_window(observed_at, kickoff):
    lead = (utc(kickoff)-utc(observed_at)).total_seconds()/60
    return 55 <= lead <= 65


def paper_return(odds, settlement):
    if type(odds) not in (int, float) or not math.isfinite(odds) or odds <= 1:
        raise ValueError('A legitimate finite decimal quote is required')
    if settlement not in ('win', 'loss', 'void', 'pending', 'disputed'):
        raise ValueError('Unknown settlement state')
    return {'win': odds-1, 'loss': -1, 'void': 0, 'pending': None, 'disputed': None}[settlement]
