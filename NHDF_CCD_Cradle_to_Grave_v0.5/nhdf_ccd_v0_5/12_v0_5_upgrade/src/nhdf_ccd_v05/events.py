from __future__ import annotations

from dataclasses import dataclass, field
from .model import Certificate, Status


@dataclass
class ContactEvent:
    event_id: int
    toi_lower: float
    toi_upper: float
    contacts: list[Certificate] = field(default_factory=list)

    @property
    def pair_ids(self) -> tuple[str, ...]:
        return tuple(sorted(c.pair_id for c in self.contacts))

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "toi_lower": self.toi_lower,
            "toi_upper": self.toi_upper,
            "pair_ids": list(self.pair_ids),
            "contacts": [c.to_dict(include_trace=False) for c in sorted(self.contacts, key=lambda x: (x.pair_id, x.query_type, x.feature_ids))],
        }


def group_contact_events(certificates: list[Certificate], merge_tolerance: float = 1e-9) -> list[ContactEvent]:
    if merge_tolerance < 0.0:
        raise ValueError("merge_tolerance must be nonnegative")
    contacts = [c for c in certificates if c.status in {Status.HIT, Status.INITIAL_OVERLAP} and c.toi_lower is not None and c.toi_upper is not None]
    contacts.sort(key=lambda c: (c.toi_lower, c.toi_upper, c.pair_id, c.query_type, c.feature_ids))
    events: list[ContactEvent] = []
    for cert in contacts:
        if not events or cert.toi_lower > events[-1].toi_upper + merge_tolerance:
            events.append(ContactEvent(len(events), cert.toi_lower, cert.toi_upper, [cert]))
        else:
            ev = events[-1]
            ev.toi_lower = min(ev.toi_lower, cert.toi_lower)
            ev.toi_upper = max(ev.toi_upper, cert.toi_upper)
            ev.contacts.append(cert)
    return events
