"""Administrative Decimal reservations; no physics, imports or network side effects."""
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path


def money(value):
    if isinstance(value, bool) or value is None:
        raise ValueError('MISSING_OR_BOOLEAN_COST')
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError('NEGATIVE_OR_NONFINITE_COST')
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def charge_total(pages):
    """Complete pagination and unique provider source/interval, not a guessed zero."""
    total = Decimal(0)
    seen = set()
    if not pages:
        raise ValueError('BILLING_PAGES_REQUIRED')
    for i, page in enumerate(pages):
        if (page.get('success') is not True or not isinstance(page.get('results'), list)
                or page.get('count') != len(page['results'])
                or 'next_token' not in page
                or (i == len(pages)-1) != (page['next_token'] is None)):
            raise ValueError('INCOMPLETE_BILLING_QUERY')
        for row in page['results']:
            if not row.get('source') or row.get('start') is None or row.get('end') is None:
                raise ValueError('UNIDENTIFIED_BILLING_INTERVAL')
            key = (row['source'], row['start'], row['end'], row.get('type'))
            if key in seen:
                raise ValueError('DUPLICATE_BILLING_INTERVAL')
            seen.add(key)
            total += money(row.get('amount'))
    return total, len(seen)


def reservation(offer, *, seconds, disk_gb, up_gb, down_gb, uncertainty):
    """Offer storage_cost is USD/GB/month; reserve another hourly disk charge.

    dph_total already contains quoted storage: keeping this explicit extra reserve
    is conservative overhead, never presented as a provider invoice.
    """
    if type(seconds) is not int or not 1 <= seconds <= 3600:
        raise ValueError('BOUNDED_LEASE_REQUIRED')
    rate = money(offer.get('dph_total'))
    storage = money(offer.get('storage_cost')) * money(disk_gb) / 720
    upload = money(offer.get('inet_down_cost')) * money(up_gb)
    download = money(offer.get('inet_up_cost')) * money(down_gb)
    compute = rate * seconds / 3600
    disk = storage * seconds / 3600
    slack = money(uncertainty)
    return dict(compute_and_preparation=str(compute), additional_storage_reserve=str(disk),
                upload_reserve=str(upload), download_reserve=str(download),
                uncertainty_reserve=str(slack), total=str(compute+disk+upload+download+slack))


class Ledger:
    """Exclusive append-only hash chain; outstanding reservations survive crashes.

    Lock files intentionally survive a crash. No automatic budget reset/recovery.
    """
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        events = []
        previous = '0'*64
        if self.path.exists():
            for line in self.path.read_bytes().splitlines():
                envelope = json.loads(line)
                event = envelope['event']
                digest = hashlib.sha256(canonical(dict(previous=previous, event=event))).hexdigest()
                if envelope['previous'] != previous or envelope['sha256'] != digest:
                    raise ValueError('LEDGER_CHAIN_DRIFT')
                events.append(event)
                previous = digest
        return events, previous

    def balances(self, events):
        if not events or events[0]['action'] != 'INIT':
            raise ValueError('NO_INITIAL_BUDGET')
        cap = money(events[0]['cap'])
        spent = money(events[0]['historical_bound'])
        active = {}
        used = set()
        for event in events[1:]:
            if event['action'] == 'RESERVE':
                token = event['token']
                if token in used:
                    raise ValueError('DUPLICATE_RESERVATION')
                used.add(token)
                active[token] = money(event['amount'])
            elif event['action'] == 'SETTLE':
                token = event['token']
                if token not in active or event.get('destroy_confirmed') is not True:
                    raise ValueError('SETTLE_REQUIRES_OWNED_DESTROY')
                spent += max(active.pop(token), money(event['observed_cost_bound']))
            elif event['action'] == 'AMEND_CAP':
                raw=Path(event['approval_raw_path']).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=event.get('approval_raw_sha256') or event.get('approval_raw_sha256')!='163e9ae386d68559e0e19423f0cdb968a7dc9d3c0af2e98327559c146e71d751':raise ValueError('ACTUAL_CAP_AMENDMENT_REQUIRED')
                if cap!=Decimal('1') or money(event['new_cap'])!=Decimal('2'):raise ValueError('ONLY_APPROVED_ONE_TO_TWO_AMENDMENT')
                cap=Decimal('2')
            elif event['action'] == 'OBSERVE':
                spent = max(spent, money(event['historical_bound']))
            else:
                raise ValueError('UNKNOWN_LEDGER_EVENT')
        remaining = cap-spent-sum(active.values(), Decimal(0))
        return dict(cap=cap, spent=spent, active=active, remaining=remaining, used=used)

    def append(self, event):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix('.lock')
        handle = lock.open('xb')
        try:
            with handle:
                events, previous = self.read()
                if events:
                    before = self.balances(events)
                    if event['action'] == 'INIT':
                        raise ValueError('NO_BUDGET_REINITIALIZATION')
                    if event['action'] == 'RESERVE' and money(event['amount']) > before['remaining']:
                        raise ValueError('PROJECT_BUDGET_EXHAUSTED')
                elif event['action'] != 'INIT' or money(event['cap']) != Decimal('1'):
                    raise ValueError('PROJECT_CAP_MUST_BE_ONE')
                after = self.balances(events+[event])
                if after['remaining'] < 0:
                    raise ValueError('PROJECT_BUDGET_EXHAUSTED')
                raw = canonical(dict(previous=previous, event=event))
                envelope = dict(previous=previous, event=event, sha256=hashlib.sha256(raw).hexdigest())
                with self.path.open('ab') as f:
                    f.write(canonical(envelope)+b'\n')
                    f.flush()
                    os.fsync(f.fileno())
        finally:
            lock.unlink()
        return after
