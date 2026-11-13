from fastapi import APIRouter,Depends
from fastapi.responses import Response
from ..config.database import get_db
from ..utils.auth import current,write_user,admin
from ..schemas.report import ReportCreate
from ..controllers import report_controller as controller,common
from ..models.report import Report
from ..models.common import serialize
from ..services.report_service import export
router=APIRouter(prefix="/reports",tags=["reports"])
@router.get("")
def listing(db=Depends(get_db),user=Depends(current)):return controller.list_all(db)
@router.get("/{ident}")
def detail(ident:str,db=Depends(get_db),user=Depends(current)):return controller.detail(db,ident)
@router.post("",status_code=201)
def create(body:ReportCreate,db=Depends(get_db),user=Depends(admin)):return controller.create(db,body)
@router.get("/{ident}/csv")
def recipe(ident:str,db=Depends(get_db),user=Depends(current)):
 return Response(export(common.require(db,Report,ident)),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=pulp-formula.csv"})
@router.get("/{ident}/samples.csv")
def samples(ident:str,db=Depends(get_db),user=Depends(current)):
 return Response(export(common.require(db,Report,ident),samples=True),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=pulp-lhs-samples.csv"})
@router.get("/{ident}/failures")
def failures(ident:str,db=Depends(get_db),user=Depends(current)):return controller.failures(db,ident)
@router.get("/{ident}/failures/samples")
def failure_samples(ident:str,combination:str|None=None,db=Depends(get_db),user=Depends(current)):return controller.failure_samples(db,ident,combination)
@router.get("/{ident}/failures/samples.csv")
def failure_samples_csv(ident:str,combination:str|None=None,db=Depends(get_db),user=Depends(current)):
 detail=controller.failure_samples_csv(db,ident,combination)
 return Response(detail["content"],media_type="text/csv",headers={"Content-Disposition":"attachment; filename=pulp-failed-samples.csv"})
