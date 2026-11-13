from fastapi import HTTPException
from ..services import run_service,failure_analysis
from ..models.run import BlendRun
from ..models.common import serialize
from .common import listing,require
def list_all(db):return listing(db,BlendRun)
def detail(db,ident):return serialize(require(db,BlendRun,ident))
def create(db,body):return serialize(run_service.create(db,body))
def failures(db,ident):
 row=require(db,BlendRun,ident)
 try:return failure_analysis.from_result(row.result,row.status)
 except failure_analysis.FailureAnalysisUnavailable as error:raise HTTPException(409,str(error))
def failure_samples(db,ident,combination):
 row=require(db,BlendRun,ident)
 try:return failure_analysis.samples_from_result(row.result,combination)
 except failure_analysis.InvalidFailureQuery as error:raise HTTPException(422,str(error))
 except failure_analysis.FailureAnalysisUnavailable as error:raise HTTPException(409,str(error))
def failure_samples_csv(db,ident,combination):
 row=require(db,BlendRun,ident)
 try:return failure_analysis.export_failed_samples(row.result,combination)
 except failure_analysis.InvalidFailureQuery as error:raise HTTPException(422,str(error))
 except failure_analysis.FailureAnalysisUnavailable as error:raise HTTPException(409,str(error))
