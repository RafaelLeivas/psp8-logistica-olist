"""PSP8 | Rafael Leivas Bisi. Pipeline local; notebook adiciona persistência Delta.
Uso: python scripts/pipeline.py --zip caminho/olist.zip --out resultados
Sem --zip, baixa o arquivo oficial do Kaggle. Não requer chave de API.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import urllib.request
import zipfile
import io
from datetime import datetime, timezone
import pandas as pd
import numpy as np

SOURCE = 'https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce'
DOWNLOAD = 'https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce'
FILES = {'pedidos': 'olist_orders_dataset.csv', 'clientes': 'olist_customers_dataset.csv', 'avaliacoes': 'olist_order_reviews_dataset.csv'}
PROJECTION = {'pedidos': None, 'clientes': ['customer_id', 'customer_state'], 'avaliacoes': ['review_id','order_id','review_score','review_creation_date','review_answer_timestamp']}
DATES = ['order_purchase_timestamp','order_approved_at','order_delivered_carrier_date','order_delivered_customer_date','order_estimated_delivery_date','review_creation_date','review_answer_timestamp']
STATES = 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split()
STATUS = ['created','approved','invoiced','processing','shipped','delivered','unavailable','canceled']

def wilson(k, n, z=1.959963984540054):
    if not n:
        return (float('nan'), float('nan'))
    p=k/n; den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return center-half, center+half

def collect(zip_path=None):
    if zip_path:
        payload=Path(zip_path).read_bytes()
    else:
        req=urllib.request.Request(DOWNLOAD, headers={'User-Agent':'PSP8-academic-project/1.0'})
        with urllib.request.urlopen(req, timeout=180) as response:
            payload=response.read()
    z=zipfile.ZipFile(io.BytesIO(payload))
    raw={name:pd.read_csv(io.BytesIO(z.read(file)), dtype='string') for name,file in FILES.items()}
    manifest={'fonte':SOURCE,'download':DOWNLOAD,'licenca':'CC BY-NC-SA 4.0',
              'processado_em_utc':datetime.now(timezone.utc).isoformat(),
              'modo':'arquivo_local' if zip_path else 'download_oficial',
              'arquivo_local_modificado_em_utc':datetime.fromtimestamp(Path(zip_path).stat().st_mtime,timezone.utc).isoformat() if zip_path else None,
              'sha256_zip':hashlib.sha256(payload).hexdigest(),'bytes_zip':len(payload),
              'arquivos':[{ 'arquivo':file,'linhas':len(raw[name]),'bytes':z.getinfo(file).file_size,'sha256':hashlib.sha256(z.read(file)).hexdigest()} for name,file in FILES.items()]}
    return raw,manifest

def quality(frames, layer):
    rows=[]
    for table,df in frames.items():
        for col in df:
            s=df[col]; non=s.dropna(); bad=0; rule='sem domínio fechado; ver catálogo'
            if col in DATES:
                val=pd.to_datetime(s,errors='coerce'); bad=int((s.notna() & val.isna()).sum()); rule='timestamp parseável'
            elif col.endswith('_id'):
                bad=int((~non.astype(str).str.fullmatch('[a-f0-9]{32}')).sum()); rule='identificador hexadecimal de 32 caracteres'
            elif col=='customer_state':
                bad=int((~non.isin(STATES)).sum()); rule='UF brasileira'
            elif col=='order_status':
                bad=int((~non.isin(STATUS)).sum()); rule='status documentado'
            elif col=='review_score':
                val=pd.to_numeric(s,errors='coerce'); bad=int((s.notna() & (~val.isin(range(1,6)))).sum()); rule='inteiro de 1 a 5'
            elif col=='customer_zip_code_prefix':
                bad=int((~non.str.fullmatch(r'\d{1,5}')).sum()); rule='prefixo de CEP com 1 a 5 dígitos no CSV'
            rows.append({'camada':layer,'tabela':table,'atributo':col,'linhas':len(s),'nulos':int(s.isna().sum()),'nulos_pct':float(s.isna().mean()*100),'distintos':int(s.nunique()),'violacoes_dominio':bad,'regra':rule})
    return pd.DataFrame(rows)

def transform(raw):
    bronze={k:v.copy() if PROJECTION[k] is None else v[PROJECTION[k]].copy() for k,v in raw.items()}
    o=bronze['pedidos'].copy(); c=bronze['clientes'].copy(); r=bronze['avaliacoes'].copy()
    # PK duplicada é erro de integridade; não resolver descartando dados silenciosamente.
    for df,key in [(o,'order_id'),(c,'customer_id')]:
        assert df[key].notna().all() and df[key].is_unique, f'Chave inválida: {key}'
    for col in DATES:
        if col in o: o[col]=pd.to_datetime(o[col],errors='coerce')
        if col in r: r[col]=pd.to_datetime(r[col],errors='coerce')
    r['review_score']=pd.to_numeric(r['review_score'],errors='coerce')
    r.loc[~r.review_score.isin(range(1,6)),'review_score']=np.nan
    review_duplicate_orders=int(r.duplicated('order_id').sum())
    r=r.sort_values(['order_id','review_answer_timestamp','review_creation_date','review_id','review_score'],na_position='first',kind='stable').drop_duplicates('order_id',keep='last')
    f=o.merge(c,on='customer_id',how='left',validate='many_to_one',indicator=True)
    missing_customers=int(f['_merge'].ne('both').sum())
    f=f.drop(columns=['_merge']).merge(r[['order_id','review_score']],on='order_id',how='left',validate='one_to_one')
    assert len(f)==len(o) and f.order_id.is_unique
    p=f.order_purchase_timestamp; a=f.order_approved_at; carrier=f.order_delivered_carrier_date; d=f.order_delivered_customer_date; est=f.order_estimated_delivery_date
    valid=(f.order_status.eq('delivered') & p.notna() & d.notna() & est.notna() & d.ge(p) & est.dt.normalize().ge(p.dt.normalize()))
    f['elegivel_pontualidade']=valid
    f['atraso_dias']=(d.dt.normalize()-est.dt.normalize()).dt.days.where(valid)
    f['atrasado']=(f.atraso_dias>0).astype('Int64').where(valid)
    f['prazo_total_dias']=((d-p).dt.total_seconds()/86400).where(valid)
    seq=valid & a.notna() & carrier.notna() & a.ge(p) & carrier.ge(a) & d.ge(carrier)
    f['elegivel_etapas']=seq
    for col,start,end in [('aprovacao_dias',p,a),('preparacao_dias',a,carrier),('transporte_dias',carrier,d)]:
        f[col]=((end-start).dt.total_seconds()/86400).where(seq)
    f['avaliacao_baixa']=(f.review_score<=2).astype('Int64').where(f.review_score.notna())
    f['data_compra']=p.dt.strftime('%Y-%m-%d')
    f['mes_compra']=p.dt.strftime('%Y-%m')
    f['customer_state']=f.customer_state.where(f.customer_state.isin(STATES),'ND')
    # Identificador do cliente não é necessário na tabela analítica final.
    f=f.drop(columns='customer_id')
    dates=pd.date_range(p.min().normalize(),p.max().normalize())
    dim_date=pd.DataFrame({'data_compra':dates.strftime('%Y-%m-%d'),'ano':dates.year,'mes':dates.month,'dia':dates.day,'dia_semana':dates.dayofweek+1})
    reg={uf:region for region,ufs in {'Norte':'AC AP AM PA RO RR TO','Nordeste':'AL BA CE MA PB PE PI RN SE','Centro-Oeste':'DF GO MT MS','Sudeste':'ES MG RJ SP','Sul':'PR RS SC','Não informado':'ND'}.items() for uf in ufs.split()}
    dim_uf=pd.DataFrame({'customer_state':STATES+['ND']}); dim_uf['regiao']=dim_uf.customer_state.map(reg)
    dim_status=pd.DataFrame({'order_status':STATUS})
    audit={'pedidos_total':len(f),'pedidos_elegiveis':int(valid.sum()),'pedidos_excluidos_pontualidade':int((~valid).sum()),'pedidos_entregues_nao_elegiveis':int((f.order_status.eq('delivered') & ~valid).sum()),'pedidos_com_etapas_validas':int(seq.sum()),'avaliacoes_excedentes_por_pedido':review_duplicate_orders,'clientes_sem_correspondencia':missing_customers,'pedidos_sem_avaliacao':int(f.review_score.isna().sum()),'pedidos_entregues_sem_sequencia_valida':int((valid & ~seq).sum()),'periodo_inicio':str(p.min()),'periodo_fim':str(p.max())}
    return bronze,{'fato_pedido':f,'dim_data':dim_date,'dim_destino':dim_uf,'dim_status':dim_status},audit

def group_stats(df,key):
    rows=[]
    for value,g in df.groupby(key,dropna=False):
        n=len(g); k=int(g.atrasado.sum()); lo,hi=wilson(k,n)
        rows.append({key:value,'pedidos':n,'atrasos':k,'taxa_atraso':k/n,'ic95_inferior':lo,'ic95_superior':hi,'prazo_mediano_dias':g.prazo_total_dias.median(),'prazo_p90_dias':g.prazo_total_dias.quantile(.9)})
    return pd.DataFrame(rows)

def analyze(tables,audit):
    f=tables['fato_pedido']; x=f[f.elegivel_pontualidade].copy(); late=x[x.atrasado.eq(1)]
    n=len(x); k=int(x.atrasado.sum()); lo,hi=wilson(k,n)
    summary={**audit,'atrasos':k,'taxa_atraso':k/n,'ic95_atraso':[lo,hi],'atraso_mediano_dias':float(late.atraso_dias.median()),'atraso_p90_dias':float(late.atraso_dias.quantile(.9)),'prazo_mediano_dias':float(x.prazo_total_dias.median()),'prazo_p90_dias':float(x.prazo_total_dias.quantile(.9))}
    uf=group_stats(x,'customer_state').sort_values('atrasos',ascending=False)
    month=group_stats(x,'mes_compra').sort_values('mes_compra')
    # Exibe cobertura dos desfechos por coorte de compra para avaliar censura.
    cohort=f.groupby('mes_compra').agg(total=('order_id','size'),elegiveis=('elegivel_pontualidade','sum')).reset_index()
    month=month.merge(cohort,on='mes_compra',validate='one_to_one'); month['cobertura']=month.elegiveis/month.total
    stages=f[f.elegivel_etapas][['aprovacao_dias','preparacao_dias','transporte_dias','prazo_total_dias']].agg(['count','mean','median',lambda s:s.quantile(.9)]).T.reset_index()
    stages.columns=['etapa','n','media_dias','mediana_dias','p90_dias']
    reviewed=x[x.review_score.notna()]; review_rows=[]
    for value,g in reviewed.groupby('atrasado'):
        rn=len(g); rk=int(g.avaliacao_baixa.sum()); rlo,rhi=wilson(rk,rn)
        review_rows.append({'atrasado':int(value),'pedidos_com_avaliacao':rn,'avaliacoes_baixas':rk,'proporcao_baixa':rk/rn,'ic95_inferior':rlo,'ic95_superior':rhi,'nota_media':float(g.review_score.mean())})
    reviews=pd.DataFrame(review_rows).sort_values('atrasado')
    b0=reviews[reviews.atrasado.eq(0)].iloc[0]; b1=reviews[reviews.atrasado.eq(1)].iloc[0]
    diff=b1.proporcao_baixa-b0.proporcao_baixa
    dlo=diff-math.sqrt((b1.proporcao_baixa-b1.ic95_inferior)**2+(b0.ic95_superior-b0.proporcao_baixa)**2)
    dhi=diff+math.sqrt((b1.ic95_superior-b1.proporcao_baixa)**2+(b0.proporcao_baixa-b0.ic95_inferior)**2)
    summary.update({'cobertura_avaliacoes_elegiveis':len(reviewed)/n,'diferenca_avaliacao_baixa':float(diff),'ic95_diferenca_newcombe':[dlo,dhi]})
    counts=f.groupby('order_status').agg(pedidos=('order_id','size'),elegiveis=('elegivel_pontualidade','sum')).reset_index()
    return summary,{'por_uf':uf,'por_mes':month,'etapas':stages,'avaliacoes':reviews,'por_status':counts}

def save_results(out,manifest,summary,stats,profiles):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    for name,obj in [('manifesto_coleta',manifest),('resumo',summary)]:
        (out/f'{name}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    for name,df in {**stats,'qualidade_atributos':profiles}.items():
        df.to_csv(out/f'{name}.csv',index=False,encoding='utf-8')

def run(zip_path=None,out='resultados'):
    raw,manifest=collect(zip_path)
    profiles=quality(raw,'origem')
    bronze,tables,audit=transform(raw)
    summary,stats=analyze(tables,audit)
    save_results(out,manifest,summary,stats,profiles)
    return bronze,tables,summary,stats,profiles,manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--zip'); parser.add_argument('--out',default='resultados'); args=parser.parse_args()
    *_,summary,stats,profiles,manifest=run(args.zip,args.out)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
