"""Reviewed commentary is valid only for the exact analytical inputs reviewed."""
import hashlib
import json

def fingerprint(data):
    keys=("symbol","market","financials","peers","macro","news","sector")
    payload={k:data[k] for k in keys}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()

def apply_review(store,data):
    review=store.read_json("research_reviews.json",{}).get(data["symbol"])
    if not review:
        return data
    if review.get("input_sha256")!=fingerprint(data):
        data["review_status"]="Dữ liệu đã thay đổi; cần đối soát lại nhận định."
        return data
    data["review"]=review
    data["review_status"]="Đã đối soát các chỉ tiêu nêu trong phụ lục; không phải kiểm toán toàn bộ dữ liệu."
    data["opportunity"]={"conclusion":review["conclusion"],"positives":review["positives"],
                         "risks":review["risks"],"next_checks":review["next_checks"]}
    for row in data["coverage"]:
        if row["group"]=="Báo cáo tài chính":
            row["detail"]="2022–2025; đã đối soát chỉ tiêu trọng yếu VCB 2024–2025, xem phụ lục; chưa đối soát toàn bộ chuỗi."
    return data
