# Rebuild of QHBREIT DCF per reports/_drafts/QHBREIT_valuation.md §2 (monthly, effective-annual discounting)
import sys
from datetime import date
UNITS=797.0; NETCASH=1547.9
SHARE={'lum':0.7485,'wave':0.1948,'pc':0.0567}
END={'lum':date(2035,12,31),'wave':date(2030,10,1),'pc':date(2036,12,7)}
def months(t0):
    y,m=t0.year,t0.month
    # first flow = end of current month (partial ignored -> whole months from next month)
    out=[]; i=0; first=True
    while True:
        if not first:
            m+=1
            if m>12: m=1;y+=1
        first=False
        d=date(y,m,1)
        if d>date(2037,1,1): break
        i+=1; out.append((i,d))
    return out
def land(d):
    if d.year==2026: return 61.85/12
    if 2027<=d.year<=2030: return 451.465/4/12
    if 2031<=d.year<=2036: return 74.375/6/12
    return 0
def run(t0,base,g,r,netcash=NETCASH):
    pv=0;und=0
    for i,d in months(t0):
        cf=0
        for b,s in SHARE.items():
            if d<=END[b]: cf+=base*s/12*(1+g)**(i/12)
        cf-=land(d)
        und+=cf; pv+=cf/(1+r)**(i/12)
    return pv/UNITS, (pv+netcash)/UNITS, und/UNITS
def irr(t0,base,g,price,mode):
    lo,hi=-0.5,2.0
    for _ in range(100):
        r=(lo+hi)/2
        pv=0; ms=months(t0); n=len([1 for i,d in ms if d<=END['lum']])
        for i,d in ms:
            cf=0
            for b,s in SHARE.items():
                if d<=END[b]: cf+=base*s/12*(1+g)**(i/12)
            cf-=land(d)
            if mode=='spread' and d<=END['lum']: cf+=NETCASH/n
            if mode=='end' and d==date(2035,12,1): cf+=NETCASH
            pv+=cf/(1+r)**(i/12)
        if pv/UNITS>price: lo=r
        else: hi=r
    return r
if __name__=='__main__':
    t0=date(2026,11,4)
    for r in (0.06,0.08,0.10):
        a,t,u=run(t0,648.8,-0.01,r); print('CHECK old base',r,round(a,2),round(t,2),'undisc',round(u,2))
    for g in (-0.03,0,0.02): print('CHECK g',g,[round(run(t0,648.8,g,r)[1],2) for r in (0.06,0.08,0.10)])
    print('CHECK irr',round(irr(t0,648.8,-0.01,3.68,'spread'),3),round(irr(t0,648.8,-0.01,3.68,'end'),3))
