"""Testes de regras de negócio com dados sintéticos, sem dados pessoais."""
import unittest
import pandas as pd
from pipeline import transform, wilson

class BusinessRules(unittest.TestCase):
    def test_grain_deadline_missing_dates_and_reviews(self):
        ids=[f'{i:032x}' for i in range(1,5)]
        o=pd.DataFrame({'order_id':ids,'customer_id':ids,'order_status':['delivered']*3+['canceled'],
          'order_purchase_timestamp':['2018-01-01 10:00:00']*4,
          'order_approved_at':['2018-01-01 11:00:00']*4,
          'order_delivered_carrier_date':['2018-01-02 10:00:00']*4,
          'order_delivered_customer_date':['2018-01-05 23:59:59','2018-01-06 00:00:00',None,None],
          'order_estimated_delivery_date':['2018-01-05 00:00:00']*4})
        c=pd.DataFrame({'customer_id':ids,'customer_state':['SP']*4})
        r=pd.DataFrame({'review_id':[ids[0],ids[1]],'order_id':[ids[0],ids[0]],'review_score':['1','5'],
           'review_creation_date':['2018-01-06','2018-01-07'],'review_answer_timestamp':['2018-01-06','2018-01-07']})
        _,tables,audit=transform({'pedidos':o,'clientes':c,'avaliacoes':r})
        f=tables['fato_pedido'].set_index('order_id')
        self.assertEqual(len(f),4)
        self.assertEqual(f.loc[ids[0],'atrasado'],0) # mesmo dia, quase meia-noite
        self.assertEqual(f.loc[ids[1],'atraso_dias'],1)
        self.assertTrue(pd.isna(f.loc[ids[2],'atrasado'])) # ausência não equivale a pontualidade
        self.assertTrue(pd.isna(f.loc[ids[3],'atrasado']))
        self.assertEqual(f.loc[ids[0],'review_score'],5) # última avaliação, sem multiplicar pedido
        self.assertEqual(audit['avaliacoes_excedentes_por_pedido'],1)
        self.assertEqual(audit['pedidos_elegiveis'],2)
        valid=f[f.elegivel_etapas]
        delta=valid[['aprovacao_dias','preparacao_dias','transporte_dias']].sum(axis=1)-valid.prazo_total_dias
        self.assertTrue(delta.abs().lt(1e-10).all())

    def test_wilson_boundaries(self):
        lo,hi=wilson(0,100); self.assertAlmostEqual(lo,0); self.assertGreater(hi,0)
        lo,hi=wilson(100,100); self.assertAlmostEqual(hi,1); self.assertLess(lo,1)
        lo,hi=wilson(50,100); self.assertAlmostEqual(lo,1-hi)

if __name__=='__main__': unittest.main()
