from __future__ import annotations
import math
def ema(values,period):
    v=list(values)
    if not v:return []
    a=2/(period+1);out=[float(v[0])]
    for x in v[1:]:out.append(float(x)*a+out[-1]*(1-a))
    return out
def sma(values,period):
    v=list(values);return [sum(v[max(0,i-period+1):i+1])/len(v[max(0,i-period+1):i+1]) for i in range(len(v))]
def rsi(values,period=14):
    v=list(values)
    if len(v)<2:return 50.0
    gains=[];losses=[]
    for a,b in zip(v[:-1],v[1:]): gains.append(max(0,b-a));losses.append(max(0,a-b))
    g=sum(gains[-period:])/max(1,min(period,len(gains)));l=sum(losses[-period:])/max(1,min(period,len(losses)))
    return 100.0 if l==0 and g>0 else 0.0 if g==0 else 100-100/(1+g/l)
def atr(high,low,close,period=14):
    if not close:return 0.0
    tr=[max(h-l,abs(h-c0),abs(l-c0)) for h,l,c0 in zip(high,low,[close[0]]+list(close[:-1]))]
    return sum(tr[-period:])/max(1,min(period,len(tr)))
def zscore(values):
    v=list(values)
    if len(v)<2:return 0.0
    m=sum(v)/len(v);sd=(sum((x-m)**2 for x in v)/len(v))**.5
    return 0.0 if sd==0 else (v[-1]-m)/sd
def clamp(x,a=0,b=1):return max(a,min(b,float(x)))
def bs_d1(s,k,t,r,sigma):
    if min(s,k,t,sigma)<=0:return 0
    return (math.log(s/k)+(r+sigma*sigma/2)*t)/(sigma*math.sqrt(t))
