"""
Report endpoints — PDF executivo e Excel de alertas (Epic 6)
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.report_service import generate_pdf_report, generate_excel_report, generate_pdf_document

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/period/{year}/{month}/pdf")
async def download_period_pdf(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gera e retorna o relatório executivo em PDF para o período informado."""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Mês inválido (1–12)")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Ano inválido")

    try:
        pdf_bytes = generate_pdf_report(db, current_user.tenant_id, year, month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {e}")

    filename = f"fiscalai-auditoria-{year:04d}-{month:02d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/period/{year}/{month}/excel")
async def download_period_excel(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gera e retorna planilha Excel com todas as inconsistências do período."""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Mês inválido (1–12)")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Ano inválido")

    try:
        xlsx_bytes = generate_excel_report(db, current_user.tenant_id, year, month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar Excel: {e}")

    filename = f"fiscalai-alertas-{year:04d}-{month:02d}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/document/{document_id}/pdf")
async def download_document_pdf(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gera e retorna relatório PDF para um documento específico."""
    try:
        pdf_bytes = generate_pdf_document(db, current_user.tenant_id, document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {e}")

    filename = f"fiscalai-documento-{document_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
