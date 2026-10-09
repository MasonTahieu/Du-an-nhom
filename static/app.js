"use strict";
const $ = id => document.getElementById(id);
let dataset=null, active="overview", loadVersion=0, catalogue=[];
const esc = value => String(value ?? "").replace(/[&<>"']/g, x => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
const number = (v,d=1) => v==null ? "Chưa có" : Number(v).toLocaleString("vi-VN",{maximumFractionDigits:d});
const contentStatus = value => ({rss_metadata:"RSS metadata · chưa kiểm chứng",source_reviewed_summary:"Tóm tắt đã đối chiếu nguồn",user_reviewed:"Nội dung đã kiểm tra",metadata_only:"Chỉ có tiêu đề / URL",extracted_unreviewed:"Đã trích nội dung · chưa đối soát"}[value] || "Nội dung do người dùng nhập");
const pct = v => v==null ? "Chưa có" : number(v*100)+"%";
const money = v => v==null ? "Chưa có" : number(v,0)+" đ";
const billion = v => v==null ? "Chưa có" : number(v/1e9);
const list = items => '<ul class="clean-list">'+items.map(x=>"<li>"+esc(x)+"</li>").join("")+"</ul>";
const card = (title,content,subtitle="") => '<section class="card"><h3>'+esc(title)+'</h3>'+(subtitle?'<p class="subheading">'+esc(subtitle)+"</p>":"")+content+"</section>";
const table = (heads,rows) => '<div class="table-wrap"><table><thead><tr>'+heads.map(x=>"<th>"+esc(x)+"</th>").join("")+"</tr></thead><tbody>"+rows.map(r=>"<tr>"+r.map(x=>"<td>"+esc(x)+"</td>").join("")+"</tr>").join("")+"</tbody></table></div>";
const metric = (label,value,hint="",color="") => '<div class="metric"><div class="label">'+esc(label)+'</div><div class="value '+color+'">'+esc(value)+'</div><div class="hint">'+esc(hint)+"</div></div>";
const hint = s => '<p class="table-note">'+esc(s)+"</p>";
const empty = s => '<div class="empty">'+esc(s)+"</div>";
function notice(message){$("notice").textContent=message;$("notice").hidden=!message;}
async function api(url,opts){const r=await fetch(url,opts);if(!r.ok){let e;try{e=await r.json()}catch{e={detail:r.statusText}}throw Error(typeof e.detail==="string"?e.detail:"Dữ liệu nhập chưa hợp lệ.");}return r.json();}
function link(url,label){return /^https?:\/\//.test(url||"") ? '<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+" ↗</a>" : esc(label);}
function lineChart(rows,key="close"){
 if(!rows.length)return empty("Chưa có dữ liệu giá.");
 // Prices are already sorted by the API. The horizontal axis is the sequence
 // of actual sessions; weekends and public holidays do not consume any space.
 const volume=key==="volume";
 const w=850,h=255,l=58,r=18,t=20,b=34,values=rows.map(x=>Number(x[key]));
 const lo=volume?0:Math.min(...values)*.98;
 const hi=volume?Math.max(1,...values)*1.05:Math.max(...values)*1.02;
 const x=i=>l+i*(w-l-r)/Math.max(1,rows.length-1),y=v=>h-b-(v-lo)*(h-b-t)/Math.max(1,hi-lo);
 let svg='<svg class="chart" viewBox="0 0 '+w+" "+h+'" role="img" aria-label="Biểu đồ '+key+'">';
 for(let i=0;i<5;i++){let v=lo+(hi-lo)*i/4,Y=y(v);svg+='<line x1="'+l+'" y1="'+Y+'" x2="'+(w-r)+'" y2="'+Y+'" stroke="#e8eef3"/><text x="'+(l-8)+'" y="'+(Y+4)+'" text-anchor="end">'+number(v/(key==="volume"?1e6:1000))+"</text>";}
 if(volume){
  const width=Math.min(10,Math.max(.6,(w-l-r)/Math.max(1,rows.length)*.85));
  svg+=values.map((v,i)=>'<rect x="'+(x(i)-width/2)+'" y="'+y(v)+'" width="'+width+'" height="'+Math.max(0,y(0)-y(v))+'" fill="#79a8c2"/>').join("");
 }else{
  const points=values.map((v,i)=>x(i)+","+y(v)).join(" ");
  svg+='<polygon points="'+l+","+(h-b)+" "+points+" "+x(rows.length-1)+","+(h-b)+'" fill="#e8f2f9"/><polyline points="'+points+'" fill="none" stroke="#125b86" stroke-width="2"/>';
 }
 for(let i of [0,Math.floor(rows.length/2),rows.length-1])svg+='<text x="'+x(i)+'" y="'+(h-9)+'" text-anchor="'+(i===0?"start":i===rows.length-1?"end":"middle")+'">'+esc(rows[i].date)+"</text>";
 return svg+"</svg>";
}
function financialChart(rows){
 const w=850,h=260,l=70,r=15,t=15,b=35,values=rows.flatMap(row=>[row.revenue,row.net_income]).filter(v=>v!=null),lo=Math.min(0,...values),hi=Math.max(1,...values),span=hi-lo;
 const y=value=>h-b-(value-lo)*(h-b-t)/span,step=(w-l-r)/Math.max(1,rows.length),barWidth=Math.min(45,step*.25);
 let svg='<svg class="chart" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="Doanh thu và lợi nhuận theo năm">';
 for(let i=0;i<5;i++){const value=lo+span*i/4,Y=y(value);svg+='<line x1="'+l+'" x2="'+(w-r)+'" y1="'+Y+'" y2="'+Y+'" stroke="#e8eef3"/><text x="'+(l-8)+'" y="'+(Y+4)+'" text-anchor="end">'+number(value/1e9,0)+'</text>';}
 rows.forEach((row,i)=>{const center=l+step*(i+.5);[row.revenue,row.net_income].forEach((value,k)=>{if(value==null)return;const x=center+(k-1)*barWidth,top=Math.min(y(value),y(0)),height=Math.abs(y(value)-y(0));svg+='<rect x="'+x+'" y="'+top+'" width="'+(barWidth-3)+'" height="'+height+'" fill="'+(k?'#54b1ab':'#125b86')+'"><title>'+esc(row.period+': '+billion(value)+' tỷ')+'</title></rect>';});svg+='<text x="'+center+'" y="'+(h-10)+'" text-anchor="middle">'+esc(row.period)+'</text>';});
 return svg+'</svg><div class="legend"><span><i style="background:#125b86"></i>Doanh thu / thu nhập hoạt động</span><span><i style="background:#54b1ab"></i>LNST</span></div>';
}
function coverage(d){return table(["Nhóm dữ liệu","Trạng thái","Phạm vi"],d.coverage.map(r=>[r.group,r.status,r.detail]));}
function hero(d){return '<div class="hero"><div class="ticker-title"><div class="ticker-box">'+esc(d.symbol)+'</div><div><h2>'+esc(d.profile.name)+'</h2><div class="muted">'+esc(d.sector.label)+" · Giá cuối phiên "+esc(d.market.date||"chưa có")+'</div></div></div><span class="chip">'+("DỮ LIỆU CHUNG")+"</span></div>";}
function reviewView(d){return d.review?card("Đối soát chỉ tiêu trọng yếu",table(["Chỉ tiêu / kỳ","Giá trị","Đối chiếu"],d.review.audit.map(r=>[r.metric+" · "+r.period,r.value,r.status+" · "+r.source+" · "+r.location]))+hint(d.review.limitations)+d.review.sources.map(s=>"<p>"+esc(s.id)+" · "+link(s.url,s.title)+"</p>").join("")):"";}
function overview(d){
 const m=d.market,f=d.financials.at(-1)||{};
 return '<div class="grid">'+metric("Giá cuối phiên",money(m.close),m.date||"", "")+metric("Thay đổi 20 phiên",pct(m.return_20),"Lợi suất giá; chưa cộng cổ tức",m.return_20>=0?"positive":"negative")+metric("LNST "+(f.period||""),billion(f.net_income),"Tỷ đồng · dữ liệu năm")+metric("ROE "+(f.period||""),pct(f.roe),"Dùng vốn chủ sở hữu bình quân")+'</div>'+
 '<div class="two-col">'+card("Diễn biến giá",lineChart(d.prices),"Nghìn đồng / cổ phiếu · dữ liệu đã lưu")+
 card("Luận điểm đầu tư",'<div class="research-status">'+esc(d.opportunity.conclusion)+"</div>"+list(d.research?.executive||d.opportunity.positives))+"</div>"+
 '<div class="two-col">'+card("Từ vĩ mô đến ngành","<p>"+esc(d.sector.context)+"</p>"+list(d.sector.drivers))+
 card("Rủi ro cần theo dõi",list(d.opportunity.risks.slice(0,4)))+"</div>"+
 card("Mức độ đầy đủ của dữ liệu",coverage(d))+reviewView(d);
}
function newsCards(rows){
 if(!rows?.length)return empty("Chưa có tin phù hợp trong bộ đã lưu. Bấm cập nhật tin CafeF trong khung nạp dữ liệu.");
 const seen=new Set();
 const recent=rows.slice().sort((a,b)=>String(b.published_at||"").localeCompare(String(a.published_at||"")))
  .filter(n=>{if(!n.url||seen.has(n.url))return false;seen.add(n.url);return true;}).slice(0,10);
 return recent.map(n=>
 '<article class="news-item"><h3>'+link(n.url,n.title)+'</h3><div class="meta">'+esc(n.published_at||"Chưa rõ ngày")+' · '+esc(n.source||"Nguồn đã lưu")+' · '+esc((n.symbols||[n.symbol]).filter(x=>x&&x!=="MARKET").join(", "))+' · '+esc(contentStatus(n.content_status))+'</div>'+(n.summary?'<p>'+esc(n.summary)+'</p>':"")+'<small class="news-classification">'+esc(n.category||"chưa phân loại")+' · '+esc((n.sectors||[]).join(", "))+' · '+esc(n.classification_status==="auto_unverified"?"Tự phân loại · chưa đối soát":"Nội dung lưu trước đó")+'</small></article>').join("");
}
function macro(d){return (d.research?.macro?.length?card("Diễn giải vĩ mô chọn lọc theo ngành",list(d.research.macro)):"")+(d.review?card("Vĩ mô → ngân hàng",list(d.review.macro_to_bank)):"")+(!d.research?.macro?.length&&d.macro_analysis?.length?card("Nhận định từ số liệu đã lưu",list(d.macro_analysis.map(r=>r.text))):"")+(d.exchange_rates?.length?card("Tỷ giá niêm yết Vietcombank",table(["Đồng tiền","Mua tiền mặt","Mua chuyển khoản","Bán","Thời điểm nguồn"],d.exchange_rates.map(r=>[r.currency,number(r.buy,0),number(r.transfer,0),number(r.sell,0),r.source_time]))+hint("Đơn vị VND/ngoại tệ. Đây là tỷ giá niêm yết của ngân hàng.")):"")+card("Bối cảnh kinh tế",d.macro.length?table(["Chỉ tiêu","Giá trị","Kỳ tham chiếu","So sánh","Công bố"],d.macro.map(r=>[r.label,number(r.value,2)+" "+r.unit,r.period,r.basis,r.published_at]))+hint("Số liệu có kỳ tham chiếu riêng. Mỗi chỉ tiêu giữ URL nguồn; không dùng ngày thu thập thay ngày công bố."):empty("Chưa nạp dữ liệu vĩ mô."))+
 '<div class="two-col">'+card("Tác động đến "+d.sector.label,"<p>"+esc(d.sector.context)+"</p>"+list(d.sector.drivers))+
 card("Chỉ tiêu cần kiểm tra",'<div class="checklist">'+d.sector.checks.map(x=>"<span>"+esc(x)+"</span>").join("")+"</div>"+hint("Quan hệ vĩ mô → ngành là diễn giải định tính. Chưa định lượng lợi nhuận hoặc mức giá từ những chỉ tiêu này."))+"</div>"+
 card("Tin kinh tế vĩ mô · RSS",newsCards(d.macro_news)+hint("Tin RSS là bối cảnh định tính, không phải số liệu GDP/CPI có thể dùng trực tiếp."))+
 card("Tin theo ngành "+d.sector.label,newsCards(d.sector_news)+hint("Liên quan theo từ khóa ngành; cần đọc nguồn gốc để xác minh."))+
 card("Nguồn chỉ tiêu vĩ mô chính thức",d.macro.length?d.macro.map(r=>'<div class="source-item">'+esc(r.label)+" · "+link(r.source_url,"Mở nguồn")+"</div>").join(""):empty("Chưa có số liệu vĩ mô từ nguồn chính thức."));
}
function market(d){const m=d.market;return '<div class="grid">'+metric("Giá cuối phiên",money(m.close),m.date||"")+metric("MA20",money(m.ma20),"Trung bình 20 phiên")+metric("MA50",money(m.ma50),"Trung bình 50 phiên")+metric("Biến động năm hóa",pct(m.volatility),"Lợi suất ngày × căn 252")+"</div>"+
 card("Lịch sử giá",lineChart(d.prices),"Đơn vị: nghìn đồng / cổ phiếu")+
 card("Khối lượng giao dịch",lineChart(d.prices,"volume"),"Đơn vị: triệu cổ phiếu")+
 card("Hiệu suất và phương pháp",table(["Thước đo","Kết quả"],[["20 phiên",pct(m.return_20)],["Chênh lệch với VN-Index (điểm %)",pct(m.relative_20)],["Sụt giảm lớn nhất trong khoảng đã lưu",pct(m.drawdown)],["Khối lượng trung bình tối đa 20 phiên",number(m.volume_20,0)],["Số phiên được lưu",m.rows],["Cơ sở giá",m.price_basis==="kbs_provider"?"Theo nguồn KBS; chưa xác minh điều chỉnh":m.price_basis||"Chưa có"]])+hint("Giá lịch sử / EOD; không phải realtime. Nguồn có thể điều chỉnh lại lịch sử khi có sự kiện cổ phiếu. Không cộng cổ tức tiền mặt vào lợi suất."));
}
function financials(d){const rows=d.financials,bank=d.sector.key==="bank";if(!rows.length)return quarterlyView(d)+empty("Chưa có dữ liệu BCTC năm.");
 const fields=[["assets","Tổng tài sản",billion],["equity","Vốn chủ sở hữu",billion],[bank?"operating_income":"revenue",bank?"Thu nhập hoạt động":"Doanh thu thuần",billion],["net_income","Lợi nhuận sau thuế",billion],["roe","ROE",pct],["roa","ROA",pct],["revenue_growth","Tăng doanh thu / TOI",pct],["profit_growth","Tăng LNST",pct],...(bank?[["cir","CIR",pct]]:[["net_margin","Biên lợi nhuận ròng",pct],["cfo","Dòng tiền kinh doanh",billion],["current_ratio","Thanh toán hiện hành (lần)",number]]),["debt_assets","Nợ phải trả / tài sản",pct]];
 return quarterlyView(d)+card("Tài chính theo năm",table(["Chỉ tiêu",...rows.map(r=>r.period)],fields.map(([key,label,fn])=>[label,...rows.map(r=>fn(r[key]))]))+hint("Số tiền: tỷ đồng. ROA/ROE dùng bình quân đầu-cuối năm. Thiếu dữ liệu là “Chưa có”, không thay bằng 0."))+
 card("Doanh thu và lợi nhuận",financialChart(rows),"Tỷ đồng · xem bảng số liệu để phân biệt dữ liệu thiếu")+
 (d.research?.quality_warnings?.length?card("Cảnh báo dữ liệu cần đối soát",list(d.research.quality_warnings)):"")+
 card("Diễn giải kết quả tài chính theo quy tắc",list(d.research?.financial||[]))+
 card("Lưu ý về dữ liệu nguồn","<p>BCTC năm được lấy từ bộ Parquet tham khảo hoặc file đã nhập. Phạm vi hợp nhất/riêng lẻ chưa được đối soát bản kiểm toán. Cần cập nhật quý hiện tại, xác minh đơn vị và sự kiện cổ phiếu trước khi sử dụng trong định giá.</p>"+list(d.methodology.slice(0,3)));
}
function industry(d){
 const ps=d.peer_summary||{}, choose=d.peer_selection||{};
 const peerRows=(d.peers||[]).map(r=>[
    r.symbol+(r.symbol===d.symbol?" (đang phân tích)":""),r.period||"Chưa có",
    billion(r.revenue),billion(r.net_income),pct(r.profit_growth),pct(r.roe),pct(r.roa),
    r.financial_available?"Có BCTC":"Thiếu BCTC"]);
 const summary=ps.period
  ? "So sánh cùng kỳ "+esc(ps.period)+": "+number(ps.peers_with_financials,0)+"/"+number(ps.peer_count,0)+" mã đối chiếu có BCTC. Nguồn phân ngành: "+esc(ps.source||"cấu hình tham khảo")+"."
  : "Chưa đủ BCTC của mã đang phân tích để lập bảng cùng kỳ.";
 const groupHint=esc(choose.note||"Các đối thủ là ứng viên theo phân ngành, chưa chứng minh mô hình kinh doanh tương đồng.");
 const tablePeers=peerRows.length?table(["Mã","Năm","Doanh thu / TOI (tỷ)","LNST (tỷ)","Tăng LN","ROE","ROA","BCTC"],peerRows):empty("Chưa xác định được doanh nghiệp cùng ngành hoặc thiếu BCTC.");
 const median=(ps.medians||{});
 const medianPanel=ps.period?table(["Chỉ tiêu","Trung vị các đối thủ có dữ liệu"],
   [["ROE",pct(median.roe)],["ROA",pct(median.roa)],["Tăng trưởng lợi nhuận",pct(median.profit_growth)],["P/B, P/E","Chưa đủ dữ liệu tin cậy"]]):"";
 return (d.review?card("Ngành ngân hàng → VCB",list(d.review.bank_to_company)):"")+
 card("Nhóm đối chiếu tự động",'<p>'+summary+'</p>'+groupHint+hint("Các mã cùng ngành được đề xuất từ danh mục ICB đã lưu, hồ sơ hoặc ánh xạ tham khảo. Không tự lấy tin RSS làm căn cứ phân ngành."))+
 card("Doanh nghiệp so sánh",tablePeers+hint("Số liệu cùng năm. Ô thiếu được giữ trống. P/E, P/B chỉ được tính khi có số cổ phiếu cùng thời điểm, kiểm tra sự kiện cổ phiếu."))+
 card("Trung vị nhóm và nhận định",medianPanel+list(d.research?.industry||d.peer_analysis||[]))+
 card("Luận điểm từ nguồn tin đã chọn",(d.research?.news_theses||[]).length?(d.research.news_theses.map(x=>'<article class="news-item"><h3>'+esc(x.heading)+'</h3><p>'+esc(x.text)+'</p></article>').join("")+hint("Nguồn đánh số và trạng thái kiểm chứng nằm bên dưới.")):empty("Chưa có thông tin đủ liên quan để lập luận điểm."))+
 (d.research?.references?.length?card("Nguồn dẫn trong luận điểm",d.research.references.map(x=>'<div class="source-item">['+esc(x.id)+'] '+link(x.url,x.title)+' · '+esc(x.published_at)+' · '+esc(contentStatus(x.status))+'</div>').join("")):"")+
 card("Tin riêng về "+d.symbol,newsCards(d.company_news))+
 card("Tin cùng ngành",newsCards(d.sector_news));
}
function valuationView(d){
 const c=d.valuation?.inputs||{};
 const rows=[
  ["Giá đóng cửa · "+(c.price_date||"Chưa có"),money(c.price)],
  ["EPS năm "+(c.year||"Chưa có")+" (VND/cổ phiếu)",money(c.historical_eps)],
  ["P/E lịch sử (cần kiểm tra chia tách)",c.historical_pe==null?"Chưa có":number(c.historical_pe,2)+" lần"],
  ["P/E trung vị đối thủ (tham khảo)",c.peer_pe_median_indicative==null?"Chưa đủ dữ liệu":number(c.peer_pe_median_indicative,2)+" lần · "+number(c.peer_pe_count,0)+" mã"]
 ];
 const historical=card("Chỉ số P/E lịch sử tham khảo",table(["Chỉ tiêu","Giá trị"],rows)+list(c.warnings||[])+hint("Các số liệu này chỉ mô tả lịch sử, không phải giá mục tiêu hoặc khuyến nghị mua/bán. Phải đối soát EPS, cơ sở điều chỉnh giá và sự kiện cổ phiếu trước khi sử dụng."));
 return historical+'<div class="two-col">'+card("Điểm thuận lợi",list(d.opportunity.positives))+card("Rủi ro và giới hạn",list(d.opportunity.risks))+'</div>'+card("Trước khi đưa ra kết luận",'<div class="checklist">'+d.opportunity.next_checks.map(x=>"<span>"+esc(x)+"</span>").join("")+'</div>');
}
function manualGuide(){return card("Nạp dữ liệu bằng CMD",'<p>Mở các file sau trong thư mục dự án. Khi xem hoặc xuất báo cáo, hệ thống chỉ đọc dữ liệu đã lưu.</p>'+table(["File CMD","Mục đích"],[["01-Cai-Bo-Nap.cmd","Cài thư viện nạp · chạy một lần"],["00-Nap-Danh-Muc-Thi-Truong.cmd","Danh mục HOSE, HNX, UPCoM"],["02-Nap-Lich-Su-Toan-Thi-Truong.cmd","Tùy chọn nâng cao · không cần cho bài nộp"],["03-Cap-Nhat-Gia-Toan-Thi-Truong.cmd","Cập nhật giá toàn danh mục sau phiên"],["02-Nap-Lich-Su-Gia.cmd","Nạp nhóm watchlist / --symbols"],["03-Cap-Nhat-Gia.cmd","Cập nhật giá sau phiên"],["04-Nap-BCTC.cmd","BCTC năm từ cache Tumiqa, BCTC quý từ KBS"],["08-Chuan-Bi-Kho-BCTC-Tumiqa.cmd","Tùy chọn tải sẵn 6 file BCTC năm HSX/HNX"],["05-Nap-Vi-Mo-Tin-Tuc.cmd","Vĩ mô, tỷ giá và tin theo nguồn cấu hình"],["06-Kiem-Tra-Du-Lieu.cmd","Kiểm tra bộ dữ liệu đã lưu"]])+hint("Sửa danh sách mã trong config/watchlist.json; nguồn vĩ mô và bài IR trong config/sources.json. Sau khi CMD hoàn tất, bấm Xem phân tích.")+'<button id="checkData" class="secondary">Kiểm tra dữ liệu đã lưu</button><div id="dataStatus"></div>');}
function quarterlyView(d){const rows=d.quarterly_financials||[];if(!rows.length)return card("BCTC quý","<p>Chưa có dữ liệu quý. Chạy 04-Nap-BCTC.cmd để bổ sung.</p>");const fields=[["assets","Tổng tài sản"],["equity","Vốn chủ sở hữu"],["liabilities","Nợ phải trả"],[d.sector.key==="bank"?"operating_income":"revenue",d.sector.key==="bank"?"Thu nhập hoạt động":"Doanh thu thuần"],["net_income","LNST"],["cfo","Dòng tiền kinh doanh"]];return card("BCTC quý theo nguồn",table(["Chỉ tiêu",...rows.map(r=>r.period)],fields.map(([k,label])=>[label,...rows.map(r=>billion(r.fields[k]?.value))]))+hint("Tỷ đồng. "+rows[0].note));}
function dataView(d){return manualGuide()+card("Mức độ đầy đủ",coverage(d))+card("Nhập dữ liệu đã đối soát",'<div class="upload"><label>Loại dữ liệu<select id="uploadKind"><option value="financials">BCTC năm · CSV</option><option value="macro">Vĩ mô · CSV</option><option value="news">Tin tức · JSON</option></select></label><input type="file" id="uploadFile" accept=".csv,.json"><button id="upload" class="primary">Nhập file đã chọn</button></div><p><a href="/api/template/financials.csv">Mẫu BCTC</a> · <a href="/api/template/macro.csv">Mẫu vĩ mô</a> · <a href="/api/template/news.json">Mẫu tin tức</a></p>')+card("Nguồn dữ liệu",d.sources.filter(r=>r.file!=="valuations.json").map(r=>'<div class="source-item"><strong>'+esc(r.source||r.file)+'</strong><br>'+esc(r.file)+' · '+esc(r.as_of||"Xem kỳ từng dòng")+' · '+link(r.source_url,"Nguồn")+'</div>').join(""))+card("Phương pháp",list(d.methodology));}
function render(){if(!dataset)return;$("content").innerHTML=hero(dataset)+({overview,macro,market,financials,industry,valuation:valuationView,data:dataView}[active])(dataset);bindData();}
function filterTickers(previous=$("ticker").value){
 const term=$("tickerSearch").value.trim().toLocaleLowerCase("vi");
 const rows=catalogue.filter(r=>(r.symbol+" "+r.name).toLocaleLowerCase("vi").includes(term));
 $("ticker").innerHTML=rows.map(r=>'<option value="'+esc(r.symbol)+'">'+esc(r.symbol+" · "+r.name+(r.exchange?" · "+r.exchange:"")+(r.has_data===false?" · chưa nạp dữ liệu":""))+"</option>").join("");
 if(rows.some(r=>r.symbol===previous))$("ticker").value=previous;
 else if(rows.some(r=>r.symbol==="VCB"))$("ticker").value="VCB";
}
async function loadStatus(){const s=await api("/api/status?mode="+$("mode").value);catalogue=s.symbols;filterTickers();$("verified").textContent=s.symbols.length+" mã trong danh mục";$("verified").className="badge";return s;}
async function load(){const version=++loadVersion;dataset=null;notice("");$("loading").hidden=false;$("content").hidden=true;$("pdf").disabled=true;try{if(!$("ticker").value){$("loading").textContent="Không có mã phù hợp. Xóa ô tìm kiếm hoặc nạp danh mục thị trường.";$("content").innerHTML=manualGuide();$("content").hidden=false;bindData();return;}const selected=catalogue.find(r=>r.symbol===$("ticker").value);if(selected?.has_data===false){$("content").innerHTML=card("Chưa nạp dữ liệu cho "+selected.symbol,"<p>Mã đã có trong danh mục. Nhập mã vào ô Nạp dữ liệu theo mã phía trên rồi bấm nạp; hoặc dùng CMD bên dưới.</p>"+table(["Lệnh CMD","Dữ liệu"],[["02-Nap-Lich-Su-Gia.cmd --symbols "+selected.symbol,"Giá lịch sử"],["04-Nap-BCTC.cmd --symbols "+selected.symbol,"BCTC theo nguồn hỗ trợ"]]))+manualGuide();$("content").hidden=false;bindData();return;}const result=await api("/api/analysis/"+$("ticker").value+"?mode="+$("mode").value);if(version!==loadVersion)return;dataset=result;render();$("content").hidden=false;$("pdf").disabled=false;}catch(e){notice(e.message);}finally{if(version===loadVersion)$("loading").hidden=true;}}
function bindData(){if($("checkData"))$("checkData").onclick=async()=>{try{const r=await api("/api/readiness?mode="+$("mode").value);$("dataStatus").innerHTML=table(["Mã","Phiên giá","Ngày giá cuối","BCTC năm","BCTC quý","Tin"],r.symbols.map(x=>[x.symbol,x.price_rows,x.price_end||"Chưa có",x.annual_periods.join(", ")||"Chưa có",x.quarter_periods.join(", ")||"Chưa có",x.news_count]))+hint("Quét giá gần nhất: "+(r.history.status||"chưa chạy")+" · Nạp khác: "+(r.collection.status||"chưa chạy"));}catch(e){notice(e.message);}};if($("seed"))$("seed").onclick=async()=>{try{const r=await api("/api/seed-local",{method:"POST"});$("mode").value="local";await loadStatus();await load();notice(r.message);}catch(e){notice(e.message);}};
 if($("upload"))$("upload").onclick=async()=>{const file=$("uploadFile").files[0];if(!file)return notice("Chọn file cần nhập.");try{const r=await api("/api/import",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({kind:$("uploadKind").value,content:await file.text()})});$("mode").value="local";await loadStatus();await load();notice(r.message);}catch(e){notice(e.message);}};}
document.querySelectorAll("#nav button").forEach(b=>b.onclick=()=>{active=b.dataset.view;document.querySelectorAll("#nav button").forEach(x=>x.classList.toggle("active",x===b));render();});
$("tickerSearch").oninput=()=>{filterTickers();load();};
$("refresh").onclick=async()=>{try{await loadStatus();await load();}catch(e){notice(e.message);}};$("ticker").onchange=load;$("mode").onchange=async()=>{try{await loadStatus();await load();}catch(e){notice(e.message);}};
$("pdf").onclick=async()=>{const b=$("pdf");b.disabled=true;b.textContent="Đang tạo PDF…";try{const r=await fetch("/api/report/"+$("ticker").value+"?mode="+$("mode").value);if(!r.ok){const e=await r.json();throw Error(e.detail||"Không tạo được PDF.");}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=$("ticker").value+"_"+$("mode").value+".pdf";a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}catch(e){notice(e.message);}finally{b.disabled=false;b.textContent="Xuất báo cáo PDF ↗";}};
(async()=>{try{await api("/api/initialize-local",{method:"POST"});await loadStatus();await load();}catch(e){notice("Không thể chuẩn bị bộ dữ liệu chung: "+e.message);$("loading").hidden=true;}})();

let loadPollTimer=null, completedJob=null;
async function pollLoad(){
 try{
  const {job}=await api("/api/load-status");
  if(!job)return;
  const running=job.status==="running";
  $("loadTickerButton").disabled=running;
  $("loadNewsButton").disabled=running;
  const labels={running:"Đang nạp",complete:"Hoàn tất các bước đã chọn",partial:"Nạp được một phần",failed:"Chưa hoàn tất"};
  let html="<p><strong>"+esc(job.symbol)+" · "+esc(labels[job.status]||job.status)+"</strong> · "+esc(job.message)+"</p>";
  if(job.result){
   html+=table(["Bước","Trạng thái"],job.result.steps.map(r=>[r.name,r.status]));
   html+=list(job.result.failed.map(r=>r.step+": "+r.error));
   html+=table(["Mã","Phiên giá","Ngày cuối","BCTC năm","BCTC quý","Tin"],job.result.coverage.map(r=>[r.symbol,r.price_rows,r.price_end||"Chưa có",r.annual_periods.join(", ")||"Chưa có",r.quarter_periods.join(", ")||"Chưa có",r.news_count]));
   html+=hint("Chỉ tiêu vĩ mô đã lưu: "+job.result.macro_count+". "+job.result.note);
  }
  $("loadProgress").innerHTML=html;
  if(running){loadPollTimer=setTimeout(pollLoad,1500);}
  else if(completedJob!==job.id){
   completedJob=job.id;
   if(job.result){$("mode").value="local";$("tickerSearch").value="";await loadStatus();if(catalogue.some(r=>r.symbol===job.symbol))$("ticker").value=job.symbol;await load();}
  }
 }catch(e){$("loadProgress").textContent="Không đọc được tiến độ: "+e.message+". Bấm Xem phân tích khi kết nối lại."; $("loadTickerButton").disabled=false;$("loadNewsButton").disabled=false;}
}
$("loadTickerButton").onclick=async()=>{
 const ticker=($("loadTicker").value.trim()||$("ticker").value).toUpperCase();
 if(!/^[A-Z][A-Z0-9]{2}$/.test(ticker))return notice("Nhập mã cổ phiếu gồm 3 ký tự.");
 $("loadTickerButton").disabled=true;
 try{
  await api("/api/load/"+encodeURIComponent(ticker),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({extended:$("loadExtended").checked})});
  clearTimeout(loadPollTimer); await pollLoad();
 }catch(e){notice(e.message);$("loadTickerButton").disabled=false;}
};
$("loadNewsButton").onclick=async()=>{
 const ticker=($("loadTicker").value.trim()||$("ticker").value).toUpperCase();
 if(!/^[A-Z][A-Z0-9]{2}$/.test(ticker))return notice("Nhập mã cổ phiếu gồm 3 ký tự.");
 $("loadNewsButton").disabled=true;
 try{
  await api("/api/load/"+encodeURIComponent(ticker),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({news_only:true})});
  clearTimeout(loadPollTimer);await pollLoad();
 }catch(e){notice(e.message);$("loadNewsButton").disabled=false;}
};
pollLoad();
