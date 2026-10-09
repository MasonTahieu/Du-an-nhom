"""Run using python -S with only a freshly copied dependency directory."""
import argparse
from pathlib import Path
import socket
import os
import sys

parser=argparse.ArgumentParser()
parser.add_argument("--deps",type=Path,required=True)
parser.add_argument("--serve-port", type=int)
args=parser.parse_args()
sys.path.insert(0,str(args.deps.resolve()))
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
os.environ["MPLCONFIGDIR"] = str(root/"tmp"/"mpl-cache")
old_connect=socket.socket.connect
def offline(sock,address):
    if isinstance(address,tuple) and address[0] in {"127.0.0.1","::1"}:
        return old_connect(sock,address)
    raise RuntimeError("External network is blocked during portable demo test")
socket.socket.connect=offline
from vnresearch.storage import ROOT,Store
from vnresearch.analysis import analyze
from vnresearch.web import status,home
from vnresearch.report import build_pdf
assert ROOT==root
assert status()["verified"]
assert "VN Equity" in home()
for ticker in ["VCB","FPT","HPG"]:
    data=analyze(Store(),ticker)
    assert data["market"]["rows"]==248
    assert data["news"] and data["macro"]
    out=root/"tmp"/(ticker+".pdf")
    build_pdf(data,out)
    assert out.stat().st_size>10000
print("PORTABLE OFFLINE SMOKE PASSED: app imports, storage, 3 analyses, 3 PDFs; no shared site-packages.")

if args.serve_port:
    import uvicorn
    uvicorn.run("vnresearch.web:app", host="127.0.0.1", port=args.serve_port)
