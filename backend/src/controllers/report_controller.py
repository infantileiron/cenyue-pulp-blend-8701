from fastapi import HTTPException
from ..services import report_service,failure_analysis
from ..models.report import Report
from ..models.common import serialize
from .common import listing,require
def list_all(db):return listing(db,Report)
def detail(db,ident):return serialize(require(db,Report,ident))
def create(db,body):return serialize(report_service.create(db,body))
def failures(db,ident):
 row=require(db,Report,ident)
 try:return failure_analysis.from_result(_result(row),None)
 except failure_analysis.FailureAnalysisUnavailable as error:raise HTTPException(409,str(error))
def failure_samples(db,ident,combination):
 row=require(db,Report,ident)
 try:return failure_analysis.samples_from_result(_result(row),combination)
 except failure_analysis.InvalidFailureQuery as error:raise HTTPException(422,str(error))
 except failure_analysis.FailureAnalysisUnavailable as error:raise HTTPException(409,str(error))
def failure_samples_csv(db,ident,combination):
 row=require(db,Report,ident)
 try:return failure_analysis.export_failed_samples(_result(row),combination)
 except failure_analysis.InvalidFailureQuery as error:raise HTTPException(422,str(error))
 except failure_analysis.FailureAnalysisUnavailable as error:raise HTTPException(409,str(error))
def _result(row):
 snapshot=row.snapshot if isinstance(row.snapshot,dict) else {}
 return snapshot.get("result")
