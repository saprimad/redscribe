"""Check exported tabular values against matrix-derived expected values."""
import csv
import math
from pathlib import Path
from .benchmark_matrix_reporting import build_matrix_reports

def equal(actual,expected):
    if expected is None:
        return actual is None or actual==""
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        try:
            return math.isclose(float(actual),expected,rel_tol=1e-12,abs_tol=1e-12)
        except (ValueError,TypeError):
            return False
    return actual==expected

def check_table(actual,expected):
    if not expected:
        return not actual
    fields=list(expected[0])
    return (len(actual)==len(expected) and all(
        list(a)==fields and all(equal(a[k],e[k]) for k in fields)
        for a,e in zip(actual,expected)))

def audit_exports(directory,state):
    from openpyxl import load_workbook
    directory=Path(directory)
    summary,rows,efficiency=build_matrix_reports(state)
    tables=(("model_summary.csv","Model summary",summary),
            ("recording_results.csv","Recording results",rows),
            ("efficiency_summary.csv","Efficiency",efficiency))
    result={}
    for filename,sheet,expected in tables:
        try:
            with (directory/filename).open(encoding="utf-8-sig",newline="") as f:
                result[filename]=check_table(list(csv.DictReader(f)),expected)
        except (OSError,ValueError):
            result[filename]=False
    wb=None
    try:
        wb=load_workbook(directory/"scientific_results.xlsx",read_only=True,data_only=False)
        for filename,sheet,expected in tables:
            values=list(wb[sheet].values)
            fields=list(values[0]) if values else []
            result[sheet]=fields==list(expected[0]) and check_table([dict(zip(fields,r)) for r in values[1:]],expected) if expected else not values
    except (OSError,ValueError,KeyError):
        for _,sheet,_ in tables:
            result[sheet]=False
    finally:
        if wb is not None:
            wb.close()
    return result
