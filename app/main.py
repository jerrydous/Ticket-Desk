from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import TICKET_STATUSES, Ticket, Note, engine, get_db, init_db
from app.schemas import HealthOut, NoteCreate, NoteOut, TicketCreate, TicketOut

app = FastAPI(title="Ticket Desk", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "wrong_parameter"})


@app.get("/healthz", response_model=HealthOut)
def healthz():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "db": "up"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "db": "down"},
        )


@app.post("/tickets", response_model=TicketOut, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    ticket = Ticket(
        title=payload.title,
        assignee=payload.assignee,
        priority=payload.priority,
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.get("/tickets", response_model=list[TicketOut])
def list_tickets(
    status: str | None = Query(default=None),
    assignee: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if status is not None and status not in TICKET_STATUSES:
        return JSONResponse(status_code=400, content={"error": "wrong_parameter"})

    query = db.query(Ticket)
    if status is not None:
        query = query.filter(Ticket.status == status)
    if assignee is not None:
        if not assignee.strip():
            return JSONResponse(status_code=400, content={"error": "wrong_parameter"})
        query = query.filter(Ticket.assignee == assignee.strip())

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return tickets


@app.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        return JSONResponse(status_code=404, content={"error": "ticket_not_found"})
    return ticket


@app.post("/tickets/{ticket_id}/done", response_model=TicketOut)
def mark_done(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        return JSONResponse(status_code=404, content={"error": "ticket_not_found"})
    if ticket.status == "done":
        return JSONResponse(status_code=409, content={"error": "already_done"})

    ticket.status = "done"
    db.commit()
    db.refresh(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/block", response_model=TicketOut)
def block_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        return JSONResponse(status_code=404, content={"error": "ticket_not_found"})
    if ticket.status == "blocked":
        return ticket

    ticket.status = "blocked"
    db.commit()
    db.refresh(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/notes", response_model=NoteOut, status_code=201)
def add_note(ticket_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        return JSONResponse(status_code=404, content={"error": "ticket_not_found"})

    note = Note(ticket_id=ticket.id, body=payload.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
