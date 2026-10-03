"""Five strategies. Each returns a signal in [-1, 1]."""
import numpy as np

def ema(x,n):
    a=2/(n+1);out=np.empty(len(x),dtype=float);out[0]=x[0]
    for i in range(1,len(x)):out[i]=a*x[i]+(1-a)*out[i-1]
    return out
def rsi(c,n=14):
    d=np.diff(c[-(n+1):]);g=d[d>0].sum()/n;l=-d[d<0].sum()/n
    return 100.0 if l==0 else 100-100/(1+g/l)
def atr(h,l,c,n=14):
    pc=c[:-1];tr=np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-pc),abs(l[1:]-pc)));return float(tr[-n:].mean())
def ema_trend(o,h,l,c,v):return float(np.tanh((ema(c,9)[-1]-ema(c,21)[-1])/max(atr(h,l,c),1e-9)*1.5))
def rsi_reversion(o,h,l,c,v):
    r=rsi(c)
    if abs(r-50)<15:return 0.0
    return float(np.clip((50-r)/25,-1,1))
def donchian_breakout(o,h,l,c,v):
    hi,lo=h[-21:-1].max(),l[-21:-1].min()
    if c[-1]>hi:return 1.0
    if c[-1]<lo:return -1.0
    return 0.0
def vwap_reversion(o,h,l,c,v):
    w=30;cc,vv=c[-w:],v[-w:];vwap=(cc*vv).sum()/max(vv.sum(),1e-9);sd=cc.std() or 1e-9
    return float(np.clip(-(c[-1]-vwap)/sd/2.5,-1,1))
def momentum(o,h,l,c,v):
    r=np.diff(np.log(c[-61:]));sd=r.std() or 1e-9
    return float(np.tanh(np.log(c[-1]/c[-11])/(sd*3.2)))
STRATEGIES={"EMA Trend":ema_trend,"RSI Reversion":rsi_reversion,"Donchian Breakout":donchian_breakout,"VWAP Reversion":vwap_reversion,"Momentum":momentum}