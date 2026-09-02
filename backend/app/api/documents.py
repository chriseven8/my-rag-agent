from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def upload(file: UploadFile = File(...), background: BackgroundTasks = None, request: Request = None):
    svc = request.app.state.document_service
    content = await file.read()
    rec = svc.create(file.filename, content)
    background.add_task(run_in_threadpool, svc.process, rec.doc_id)
    return {"doc_id": rec.doc_id, "status": rec.status}


@router.get("/list")
def list_documents(request: Request):
    return request.app.state.document_service.list_all()


@router.get("/{doc_id}")
def get_document(doc_id: str, request: Request):
    rec = request.app.state.document_service.get(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="document not found")
    return rec


@router.delete("/{doc_id}")
def delete_document(doc_id: str, request: Request):
    request.app.state.document_service.delete(doc_id)
    return {"ok": True}
