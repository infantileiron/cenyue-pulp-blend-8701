from fastapi import APIRouter,Depends
from fastapi.responses import Response
from ..config.database import get_db
from ..utils.auth import current,write_user
from ..schemas.run import RunCreate
from ..controllers import run_controller as controller
router=APIRouter(prefix="/runs",tags=["runs"])
@router.get("")
def listing(db=Depends(get_db),user=Depends(current)):return controller.list_all(db)
@router.get("/{ident}")
def detail(ident:str,db=Depends(get_db),user=Depends(current)):return controller.detail(db,ident)
@router.post("",status_code=201)
def create(body:RunCreate,db=Depends(get_db),user=Depends(write_user)):return controller.create(db,body)
@router.get("/{ident}/failures")
def failures(ident:str,db=Depends(get_db),user=Depends(current)):return controller.failures(db,ident)
@router.get("/{ident}/failures/samples")
def failure_samples(ident:str,combination:str|None=None,db=Depends(get_db),user=Depends(current)):return controller.failure_samples(db,ident,combination)
@router.get("/{ident}/failures/samples.csv")
def failure_samples_csv(ident:str,combination:str|None=None,db=Depends(get_db),user=Depends(current)):
 detail=controller.failure_samples_csv(db,ident,combination)
 return Response(detail["content"],media_type="text/csv",headers={"Content-Disposition":"attachment; filename=pulp-failed-samples.csv"})
