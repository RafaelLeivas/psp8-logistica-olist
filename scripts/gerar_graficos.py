from pathlib import Path
import json
import pandas as pd
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderPDF
import pypdfium2 as pdfium
root = Path(__file__).resolve().parents[1]
out = root / 'resultados'
tmp = root / 'work' / 'graficos'
tmp.mkdir(parents=True, exist_ok=True)
uf = pd.read_csv(out / 'por_uf.csv')
month = pd.read_csv(out / 'por_mes.csv')
stages = pd.read_csv(out / 'etapas.csv')
rv = pd.read_csv(out / 'avaliacoes.csv')
# Gráficos estáticos produzidos com o módulo de gráficos do ReportLab.
def save_chart(d,name):
    pdf=tmp/f'{name}.pdf'; renderPDF.drawToFile(d,str(pdf))
    doc=pdfium.PdfDocument(str(pdf)); img=doc[0].render(scale=2).to_pil(); img.save(out/f'{name}.png'); doc.close()
def bar(labels,values,title,unit,name,maximum=None):
    d=Drawing(640,320); d.add(String(18,296,title,fontName='Helvetica-Bold',fontSize=14,fillColor=colors.HexColor('#15334c')))
    bc=HorizontalBarChart(); bc.x=100;bc.y=48;bc.width=475;bc.height=225
    bc.data=[list(reversed(values))];bc.categoryAxis.categoryNames=list(reversed(labels))
    bc.categoryAxis.labels.fontSize=10;bc.valueAxis.valueMin=0;bc.valueAxis.valueMax=maximum or max(values)*1.2
    bc.bars[0].fillColor=colors.HexColor('#168797');bc.bars[0].strokeColor=None
    bc.barLabelFormat='%.2f';bc.barLabels.fontSize=9;bc.barLabels.nudge=7
    d.add(bc); d.add(String(100,18,unit,fontSize=9,fillColor=colors.HexColor('#526777')));save_chart(d,name)

toprate=uf.query('pedidos>=100').sort_values('taxa_atraso',ascending=False).head(8)
bar(toprate.customer_state.tolist(),(toprate.taxa_atraso*100).tolist(),'Maior taxa de atraso por destino','Taxa (%) | grupos com n >= 100 | intervalos e amostras na tabela','01_taxas_uf',30)
bar(uf.head(6).customer_state.tolist(),uf.head(6).atrasos.tolist(),'Maior volume absoluto de atrasos','Número de pedidos atrasados | todos os pedidos elegíveis','02_volume_uf')
bar(['Aprovação','Preparação / expedição','Transporte final'],stages.media_dias.iloc[:3].tolist(),'Onde está o tempo de entrega?','Dias médios | mesmos 95.082 pedidos em todas as etapas','04_etapas',12)
bar(['No prazo','Atrasados'],(rv.proporcao_baixa*100).tolist(),'Avaliações baixas são mais frequentes nos atrasos','Notas 1 ou 2 (%) | associação observacional, sem interpretação causal','05_avaliacoes',75)
m=month.query('pedidos>=100'); d=Drawing(640,320)
d.add(String(18,296,'Evolução dos atrasos por mês de compra',fontName='Helvetica-Bold',fontSize=14,fillColor=colors.HexColor('#15334c')))
lp=LinePlot();lp.x=55;lp.y=70;lp.width=550;lp.height=205;lp.data=[list(enumerate((m.taxa_atraso*100).tolist()))]
lp.xValueAxis.valueMin=0;lp.xValueAxis.valueMax=len(m)-1;lp.xValueAxis.valueSteps=list(range(0,len(m),2));lp.xValueAxis.labelTextFormat=lambda v: m.mes_compra.iloc[int(v)]
lp.xValueAxis.labels.angle=45;lp.xValueAxis.labels.fontSize=8;lp.yValueAxis.valueMin=0;lp.yValueAxis.valueMax=22;lp.yValueAxis.valueSteps=[0,5,10,15,20]
lp.lines[0].strokeColor=colors.HexColor('#168797');lp.lines[0].strokeWidth=2;d.add(lp)
d.add(String(55,16,'Taxa (%) | coortes com >= 100 pedidos elegíveis; cobertura disponível no CSV',fontSize=9));save_chart(d,'03_evolucao')

