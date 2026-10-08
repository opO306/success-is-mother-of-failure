"""Observed objective costs; forecasts never certify realized net benefit."""
from .common import Ledger


def recovery(*,overhead_ns,baseline_ns,learned_ns,observed_reuses):
    if any(type(value) is not int or value<0 for value in (overhead_ns,baseline_ns,learned_ns,observed_reuses)):
        raise ValueError('INVALID_COST')
    saving=baseline_ns-learned_ns; net=saving*observed_reuses-overhead_ns
    return {'per_reuse_saving_ns':saving,'break_even_reuses':None if saving<=0 else (overhead_ns+saving-1)//saving,
            'realized_net_ns':net,'observed_reuses':observed_reuses,
            'cost_status':'RECOVERED_FOR_OBSERVED_REUSES' if net>0 else 'COST_NOT_YET_RECOVERED',
            'future_net_profit':'UNCONFIRMED'}


class Book:
    def __init__(self,directory): self.events=Ledger(directory)
    def charge(self,category,wall_ns,cpu_ns,**evidence):
        if type(wall_ns) is not int or type(cpu_ns) is not int or min(wall_ns,cpu_ns)<0: raise ValueError('UNKNOWN_COST_STOP')
        return self.events.append(dict(category=category,wall_ns=wall_ns,cpu_ns=cpu_ns,evidence=evidence))
    def total(self,exclude=()):
        events=[event['payload'] for event in self.events.history() if event['payload']['category'] not in exclude]
        return {metric:sum(event[metric] for event in events) for metric in ('wall_ns','cpu_ns')}
