from sqlalchemy.orm import Session

from backend.app.models import IdCounter, Ticket


def next_incident_number(db: Session) -> str:
    counter = db.get(IdCounter, "incident")
    if counter is None:
        # Continue past any existing seeded numbers
        max_n = 10000
        for ticket in db.query(Ticket.number).all():
            digits = "".join(ch for ch in ticket.number if ch.isdigit())
            if digits:
                max_n = max(max_n, int(digits))
        counter = IdCounter(name="incident", value=max_n)
        db.add(counter)
        db.flush()
    counter.value += 1
    db.flush()
    return f"INC{counter.value:07d}"