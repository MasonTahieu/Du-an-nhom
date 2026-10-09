from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vnresearch.storage import ROOT, Store
from vnresearch.analysis import analyze
from vnresearch.report import build_pdf
for ticker in ["VCB","FPT","HPG"]:
    path=ROOT/"reports"/"samples"/(ticker+".pdf")
    build_pdf(analyze(Store("sample"),ticker),path)
    print(path)
