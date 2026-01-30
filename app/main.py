from fastapi import FastAPI
from app.api.routes import invoice
from app.db.session import Base, engine

# create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Invoice API")

app.include_router(invoice.router)

@app.get("/health")
def health():
    return {"status": "ok"}
