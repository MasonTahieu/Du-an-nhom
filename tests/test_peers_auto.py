"""New peer-discovery and comparable metrics tests (work offline)."""
from pathlib import Path
import pandas as pd
from vnresearch.peers import normalize_industry, refresh_industry_catalog, suggest, compare, explain
from vnresearch.storage import Store
from vnresearch.analysis import financial_rows


def test_curated_securities_peers_are_deterministic(tmp_path):
    store=Store('local',tmp_path)
    got=suggest(store,'SSI')
    assert got['sector']=='securities'
    assert got['peers']==['HCM','VND','VCI','BSI','VIX']
    assert 'SSI' not in got['peers']
    assert suggest(store,'SSI')==got
    assert suggest(store,'VND')['peers']


def test_unknown_stock_does_not_invent_peers(tmp_path):
    assert suggest(Store('local',tmp_path),'ZZZ')['peers']==[]


def test_icb_more_specific_than_broad_curated_group(tmp_path):
    store=Store('local',tmp_path)
    store.write_json('industry_catalog.json',{'retrieved_at':'2026-10-09T00:00:00+00:00','symbols':{
        'ABC': {'industry_code':'8773','industry_name':'Công ty chứng khoán','industry_level':4},
        'DEF': {'industry_code':'8773','industry_name':'Công ty chứng khoán','industry_level':4},
        'GHI': {'industry_code':'8774','industry_name':'Ngân hàng','industry_level':4}
    }},{})
    got=suggest(store,'ABC')
    assert got['peers']==['DEF']
    assert 'GHI' not in got['peers']


def test_icb_normalization_keeps_most_specific_record():
    raw=pd.DataFrame([
        {'symbol':'ABC','icb_code':'8000','icb_name':'Tài chính','icb_level':1},
        {'symbol':'ABC','icb_code':'8773','icb_name':'Dịch vụ chứng khoán','icb_level':4},
        {'symbol':'DEF','icb_code':'8773','icb_name':'Dịch vụ chứng khoán','icb_level':4},
    ])
    result=normalize_industry(raw)
    assert result['ABC']['industry_code']=='8773'
    assert result['DEF']['industry_level']==4


def test_icb_fetch_cached_no_repeat(tmp_path):
    store=Store('local',tmp_path)
    calls=[]
    def fetch():
        calls.append(1)
        return pd.DataFrame([{'symbol':t,'icb_code':'8773','icb_name':'Chứng khoán','icb_level':4} for t in ('SSI','VND','HCM')])
    x=refresh_industry_catalog(store,fetch=fetch)
    y=refresh_industry_catalog(store,fetch=fetch)
    assert x['status']=='complete' and not x['cached']
    assert y['cached'] and len(calls)==1


def test_icb_failure_preserves_existing(tmp_path):
    store=Store('local',tmp_path)
    store.write_json('industry_catalog.json',{'symbols':{'SSI':{'industry_code':'8773'}},'retrieved_at':'2020-01-01T00:00:00+00:00'}, {})
    r=refresh_industry_catalog(store,fetch=lambda: (_ for _ in ()).throw(RuntimeError('blocked')))
    assert r['status']=='partial'
    assert store.read_json('industry_catalog.json')['symbols']['SSI']['industry_code']=='8773'


def test_compare_medians_same_year_and_missing_peers_explicit(tmp_path):
    d=[]
    for t,year,earn,equity,asset in [
      ('SSI','2024',10,80,150),('SSI','2025',20,120,200),
      ('HCM','2024',8,60,120),('HCM','2025',12,80,160),
      ('VND','2024',5,50,120),('VND','2025',5,60,140),
      ('VCI','2024',5,20,75),('VCI','2025',8,40,95)
    ]:
        for key,val in {'net_income':earn,'equity':equity,'assets':asset,'revenue':earn*5}.items():
            d.append({'symbol':t,'period':year,'item_code':key,'value':val})
    frame=pd.DataFrame(d)
    sel={'peers':['HCM','VND','VCI','BSI'],'candidates':[], 'note':'test','sector_source':'verified'}
    rows,summary=compare(frame,pd.DataFrame(),'SSI',sel,'2025',financial_rows,'securities')
    assert len(rows)==5
    assert summary['peers_with_financials']==3
    assert rows[-1]['symbol']=='BSI' and rows[-1]['roe'] is None
    assert rows[0]['roe']==.2
    assert summary['medians']['roe'] is not None
    assert all(r['pb'] is None and r['pe'] is None for r in rows)
    notes=explain(rows,summary,'SSI',lambda val,kind='number':f'{val:.2f}')
    assert any('trung vị' in n for n in notes)


def test_news_view_limits_ten_and_preserves_files():
    # Static check guards against accidentally rendering 35 links again.
    script=(Path(__file__).resolve().parents[1]/'static/app.js').read_text(encoding='utf-8')
    part=script.split('function newsCards(rows){',1)[1].split('function macro(d)',1)[0]
    assert '.slice(0,10)' in part
    assert 'seen.has(n.url)' in part


def test_integration_analyze_and_pdf_with_missing_peers(tmp_path, monkeypatch):
    from vnresearch import analysis, storage
    from vnresearch.report import build_pdf
    import json
    store=Store('local',tmp_path)
    store.write_json('companies.json',{'SSI':{'name':'SSI Securities','sector':'securities','peers':[]}}, {})
    raw=[]
    for ticker in ('SSI','HCM','VND'):
        for period in ('2024','2025'):
            values={'assets':200.0,'equity':100.0,'net_income':10.0 if period=='2024' else 15.0,'revenue':60.0}
            raw.extend({'symbol':ticker,'period':period,'item_code':k,'value':v} for k,v in values.items())
    facts=pd.DataFrame(raw)
    prices=pd.DataFrame([{'symbol':'SSI','date':f'2026-01-{i:02d}','close':20000+i,'volume':1000,'price_basis':'kbs_provider'} for i in range(1,24)])
    def fake_read(self,name):
        return {'financials.parquet':facts,'prices.parquet':prices}.get(name,pd.DataFrame())
    monkeypatch.setattr(storage.Store,'read',fake_read)
    result=analysis.analyze(store,'SSI')
    assert result['peer_summary']['peer_count']==5
    assert result['peer_summary']['peers_with_financials']==2
    assert [x['symbol'] for x in result['peers']][:3]==['SSI','HCM','VND']
    assert all(x['pb'] is None for x in result['peers'])
    json.dumps(result,ensure_ascii=False,allow_nan=False)
    out=tmp_path/'example.pdf'
    build_pdf(result,out)
    assert out.exists() and out.stat().st_size>5000
