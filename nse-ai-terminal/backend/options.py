"""Option-chain model (Black-Scholes) used in SIM mode."""
import math
import time
import zlib

STEP={"NIFTY50":50,"BANKNIFTY":100,"FINNIFTY":50,"MIDCPNIFTY":25,"SENSEX":100}
LOT={"NIFTY50":75,"BANKNIFTY":30,"FINNIFTY":65,"MIDCPNIFTY":120,"SENSEX":20}

def _ncdf(x):return 0.5*(1+math.erf(x/math.sqrt(2)))
def _npdf(x):return math.exp(-0.5*x*x)/math.sqrt(2*math.pi)

def bs(spot,strike,t,iv,is_call,r=0.065):
    t=max(t,1e-6);sd=iv*math.sqrt(t);d1=(math.log(spot/strike)+(r+0.5*iv*iv)*t)/sd;d2=d1-sd;disc=math.exp(-r*t)
    if is_call:
        price=spot*_ncdf(d1)-strike*disc*_ncdf(d2);delta=_ncdf(d1)
        theta=-(spot*_npdf(d1)*iv)/(2*math.sqrt(t))-r*strike*disc*_ncdf(d2)
    else:
        price=strike*disc*_ncdf(-d2)-spot*_ncdf(-d1);delta=_ncdf(d1)-1
        theta=-(spot*_npdf(d1)*iv)/(2*math.sqrt(t))+r*strike*disc*_ncdf(-d2)
    return {"price":price,"delta":delta,"gamma":_npdf(d1)/(spot*sd),
            "vega":spot*_npdf(d1)*math.sqrt(t)/100,"theta":theta/365}

def _rng(*parts):return (zlib.crc32("|".join(map(str,parts)).encode())%10000)/10000.0
def smile_iv(spot,strike,base=0.13):
    m=math.log(strike/spot);return base+2.4*m*m+(-0.25*m if m<0 else 0.0)

def build_chain(symbol,spot,expiry_days=4.0,width=8):
    step=STEP.get(symbol,50);atm=round(spot/step)*step;t=expiry_days/365.0;bucket=int(time.time()//30)
    rows=[];tot_ce=tot_pe=0
    for k in range(-width,width+1):
        strike=atm+k*step;iv=smile_iv(spot,strike);ce,pe=bs(spot,strike,t,iv,True),bs(spot,strike,t,iv,False)
        shape=math.exp(-((k/5.0)**2));base=4000000*shape*(0.6+_rng(symbol,strike))
        ce_oi=base*(1.25 if k>0 else 0.8);pe_oi=base*(1.25 if k<0 else 0.8)
        d_ce=(_rng(symbol,strike,bucket,"c")-0.45)*0.12;d_pe=(_rng(symbol,strike,bucket,"p")-0.45)*0.12
        vol_ce=ce_oi*(0.2+_rng(symbol,strike,bucket,"vc")*0.6);vol_pe=pe_oi*(0.2+_rng(symbol,strike,bucket,"vp")*0.6)
        rows.append({"strike":strike,"atm":k==0,
            "ce":{"ltp":round(ce["price"],2),"oi":int(ce_oi),"oi_chg":round(d_ce*100,1),"vol":int(vol_ce),"iv":round(iv*100,1),"delta":round(ce["delta"],3),"gamma":round(ce["gamma"],5),"theta":round(ce["theta"],2),"vega":round(ce["vega"],2)},
            "pe":{"ltp":round(pe["price"],2),"oi":int(pe_oi),"oi_chg":round(d_pe*100,1),"vol":int(vol_pe),"iv":round(iv*100,1),"delta":round(pe["delta"],3),"gamma":round(pe["gamma"],5),"theta":round(pe["theta"],2),"vega":round(pe["vega"],2)}})
        tot_ce+=ce_oi;tot_pe+=pe_oi
    res=max(rows,key=lambda r:r["ce"]["oi"])["strike"];sup=max(rows,key=lambda r:r["pe"]["oi"])["strike"]
    return {"symbol":symbol,"spot":round(spot,2),"atm":atm,"expiry_days":expiry_days,"lot":LOT.get(symbol,50),
            "pcr":round(tot_pe/max(tot_ce,1),2),"support":sup,"resistance":res,"rows":rows,"simulated":True}