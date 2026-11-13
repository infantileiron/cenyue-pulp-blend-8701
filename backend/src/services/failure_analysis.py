import csv,io,math
from ..constants.enums import PROPERTIES,CONSTRAINT_TOLERANCE

PROPERTY_LABELS={"strength":"强度","whiteness":"白度","recycled":"回收率"}
CHECKS=[]
for _property in PROPERTIES:
 CHECKS.append({"code":_property+"_low","property":_property,"side":"low","bound_key":_property+"_min","label":PROPERTY_LABELS[_property]+"低于下界"})
 CHECKS.append({"code":_property+"_high","property":_property,"side":"high","bound_key":_property+"_max","label":PROPERTY_LABELS[_property]+"高于上界"})
CHECK_BY_CODE={check["code"]:check for check in CHECKS}
CHECK_INDEX={check["code"]:index for index,check in enumerate(CHECKS)}
SAMPLE_FIELDS=["index","cost","strength","whiteness","recycled","compliant"]
PROPERTY_FIELDS=SAMPLE_FIELDS[2:5]


class FailureAnalysisUnavailable(ValueError):
 pass


class InvalidFailureQuery(ValueError):
 pass


def _number(value,message):
 if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(float(value)):raise FailureAnalysisUnavailable(message)
 return float(value)


def _ordered(codes):
 return sorted(codes,key=lambda code:CHECK_INDEX[code])


def _combination_key(codes):
 return ",".join(_ordered(codes))


def _combination_label(codes):
 return " + ".join(CHECK_BY_CODE[code]["label"] for code in _ordered(codes))


def _violations(values,bounds,tolerance):
 result=[]
 for check in CHECKS:
  value=values[check["property"]];bound=bounds[check["bound_key"]]
  violated=not(value>=bound-tolerance) if check["side"]=="low" else not(value<=bound+tolerance)
  if violated:result.append(check["code"])
 return result


def _requirements(robustness,spec):
 if not isinstance(robustness,dict):raise FailureAnalysisUnavailable("该运行没有固定配方扰动结果（可能不可行或未完成），无法补算失败组合")
 if not isinstance(spec,dict):raise FailureAnalysisUnavailable("历史结果缺少质量上下界，无法补算失败组合")
 missing=[check["bound_key"] for check in CHECKS if check["bound_key"] not in spec]
 if missing:raise FailureAnalysisUnavailable("历史结果缺少质量界限 "+"、".join(missing)+"，无法补算失败组合")
 bounds={check["bound_key"]:_number(spec[check["bound_key"]],check["bound_key"]+" 必须为有限数") for check in CHECKS}
 tolerance=_number(robustness.get("comparison_tolerance",CONSTRAINT_TOLERANCE),"比较容差必须为非负有限数")
 if tolerance<0:raise FailureAnalysisUnavailable("比较容差必须为非负有限数")
 return tolerance,bounds


def _rows(robustness,spec):
 tolerance,bounds=_requirements(robustness,spec)
 samples=robustness.get("samples")
 if not isinstance(samples,list) or not samples:raise FailureAnalysisUnavailable("历史结果未保存扰动样本，无法补算失败组合；请重新运行该情景生成样本")
 declared=robustness.get("n_samples")
 if declared is not None and (isinstance(declared,bool) or not isinstance(declared,int) or declared<1):raise FailureAnalysisUnavailable("历史结果的样本数声明无效，无法补算失败组合")
 if declared is not None and declared!=len(samples):raise FailureAnalysisUnavailable(f"历史结果扰动样本不完整（存{len(samples)}条，声明{declared}条），无法逐条对账，无法补算失败组合")
 indexes=set();rows=[]
 for sample in samples:
  if not isinstance(sample,dict):raise FailureAnalysisUnavailable("历史结果扰动样本格式无效，无法补算失败组合")
  index=sample.get("index")
  if isinstance(index,bool) or not isinstance(index,int) or index<1:raise FailureAnalysisUnavailable("扰动样本序号无效，无法逐条对账")
  if index in indexes:raise FailureAnalysisUnavailable(f"扰动样本序号{index}重复，无法逐条对账")
  indexes.add(index)
  values={}
  for field in PROPERTY_FIELDS:
   values[field]=_number(sample.get(field),f"扰动样本{index}缺少{field}数值，无法补算失败组合")
  violations=_violations(values,bounds,tolerance)
  marker=sample.get("compliant")
  if not isinstance(marker,bool):raise FailureAnalysisUnavailable(f"扰动样本{index}缺少合规标记，无法逐条对账")
  if marker==bool(violations):raise FailureAnalysisUnavailable(f"扰动样本{index}的合规标记与按容差计算的超界结果不一致，无法逐条对账")
  rows.append({"index":index,"values":values,"violations":violations,"compliant":marker})
 reported_failed=robustness.get("failed");reported_passed=robustness.get("passed")
 failed=sum(1 for row in rows if not row["compliant"]);passed=len(rows)-failed
 if reported_failed is not None and _number(reported_failed,"历史结果失败样本数无效")!=failed:raise FailureAnalysisUnavailable(f"历史结果失败样本数为{reported_failed}，但扰动样本逐条合计为{failed}，无法对账")
 if reported_passed is not None and _number(reported_passed,"历史结果通过样本数无效")!=passed:raise FailureAnalysisUnavailable(f"历史结果通过样本数为{reported_passed}，但扰动样本逐条合计为{passed}，无法对账")
 return rows,tolerance,bounds


def analyze(robustness,spec):
 rows,tolerance,bounds=_rows(robustness,spec)
 failed=sum(1 for row in rows if not row["compliant"])
 single_failures=[{"code":check["code"],"property":check["property"],"side":check["side"],"label":check["label"],"bound":bounds[check["bound_key"]],"count":sum(1 for row in rows if check["code"] in row["violations"])} for check in CHECKS]
 groups={}
 for row in rows:
  if row["violations"]:groups.setdefault(_combination_key(row["violations"]),[]).append(row["index"])
 combinations=[]
 for key,indices in groups.items():
  codes=key.split(",")
  combinations.append({"key":key,"label":_combination_label(codes),"checks":codes,"check_count":len(codes),"kind":"single" if len(codes)==1 else "joint","count":len(indices),"sample_indices":sorted(indices)})
 combinations.sort(key=lambda item:(-item["count"],item["key"]))
 assigned=[index for combination in combinations for index in combination["sample_indices"]]
 duplicate_assignments=len(assigned)-len(set(assigned))
 failed_indices=sorted(row["index"] for row in rows if not row["compliant"])
 unclassified=failed-len(assigned)
 reconciliation={"failed_samples":failed,"combination_sample_total":len(assigned),"unclassified_failed":unclassified,"duplicate_sample_assignments":duplicate_assignments,"failed_sample_indices":failed_indices,"balanced":unclassified==0 and duplicate_assignments==0 and len(assigned)==failed}
 if not reconciliation["balanced"]:raise FailureAnalysisUnavailable("共同失败组合与失败样本未能逐条对账")
 return {"sample_count":len(rows),"passed":len(rows)-failed,"failed":failed,"compliance_rate":(len(rows)-failed)/len(rows),"failed_rate":failed/len(rows),"comparison_tolerance":tolerance,"bounds":bounds,"single_failures":single_failures,"combinations":combinations,"reconciliation":reconciliation,"seed":robustness.get("seed"),"perturb_cost":robustness.get("perturb_cost"),"dimension_count":robustness.get("dimension_count"),"source":"stored_perturbation_samples","resampled":False,"assumption":"单项失败为可重叠计数，同一失败样本可违反多项；共同失败组合按每个样本实际超界的全部界限归类，组合之间互斥，组合样本数合计等于失败样本数。"}


def from_result(result,status=None):
 if not isinstance(result,dict):raise FailureAnalysisUnavailable(f"该运行状态为{status or '未知'}，没有保存结果，无法补算失败组合")
 if status is not None and status!="completed":raise FailureAnalysisUnavailable(f"该运行状态为{status}，没有可用的固定配方扰动结果，无法补算失败组合；不可行或未完成的运行不补造组合")
 return analyze(result.get("robustness"),result.get("spec"))


def normalize_combination(combination):
 if combination is None or not combination.strip():return None
 codes=[code.strip() for code in combination.split(",") if code.strip()]
 if not codes:return None
 unknown=[code for code in codes if code not in CHECK_BY_CODE]
 if unknown:raise InvalidFailureQuery("未知的失败项："+"、".join(unknown))
 if len(codes)!=len(set(codes)):raise InvalidFailureQuery("失败组合包含重复项，无法按组合查看样本")
 return _combination_key(codes)


def samples_from_result(result,combination):
 if not isinstance(result,dict):raise FailureAnalysisUnavailable("历史结果为空，无法补算失败组合")
 robustness=result.get("robustness");summary=analyze(robustness,result.get("spec"));key=normalize_combination(combination)
 expected={item["key"]:item["sample_indices"] for item in summary["combinations"]}
 if key is not None and key not in expected:raise InvalidFailureQuery("该失败组合没有对应样本，无法查看明细")
 rows=[]
 for sample in robustness["samples"]:
  values={field:_number(sample.get(field),"扰动样本缺少"+field+"数值") for field in PROPERTY_FIELDS}
  violations=_violations(values,summary["bounds"],summary["comparison_tolerance"])
  if not violations:continue
  sample_key=_combination_key(violations)
  if key is not None and sample_key!=key:continue
  rows.append({"index":sample["index"],"cost":_number(sample.get("cost"),"扰动样本缺少成本数值"),**values,"compliant":False,"combination":sample_key,"combination_label":_combination_label(violations),**{check["code"]:check["code"] in violations for check in CHECKS}})
 rows.sort(key=lambda row:row["index"])
 actual=[row["index"] for row in rows]
 if key is None:
  if actual!=summary["reconciliation"]["failed_sample_indices"]:raise FailureAnalysisUnavailable("失败样本明细与汇总的逐条序号不一致，无法对账")
 elif actual!=expected[key]:raise InvalidFailureQuery("该组合的样本明细与汇总的逐条序号不一致，无法对账")
 return {"combination":key,"count":len(rows),"summary":summary,"samples":rows}


def export_failed_samples(result,combination):
 detail=samples_from_result(result,combination);summary=detail["summary"];out=io.StringIO();writer=csv.writer(out)
 writer.writerow(SAMPLE_FIELDS+["failure_combination","failure_combination_label"]+[check["code"] for check in CHECKS]+[check["bound_key"] for check in CHECKS]+["quality_comparison_tolerance"])
 for row in detail["samples"]:
  writer.writerow([row["index"],row["cost"],row["strength"],row["whiteness"],row["recycled"],row["compliant"],row["combination"],row["combination_label"]]+[int(row[check["code"]]) for check in CHECKS]+[summary["bounds"][check["bound_key"]] for check in CHECKS]+[summary["comparison_tolerance"]])
 return {"filename":"pulp-failed-samples.csv","content":"﻿"+out.getvalue()}
