import io, zipfile, requests, pandas as pd, numpy as np
from pathlib import Path

BASE='https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m'
OUT=Path(__file__).parent/'output'; OUT.mkdir(exist_ok=True)
COLS=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore']

def load_2025():
    parts=[]
    for m in range(1,13):
        url=f'{BASE}/BTCUSDT-1m-2025-{m:02d}.zip'
        print('download',url)
        r=requests.get(url,timeout=120); r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            with z.open(z.namelist()[0]) as f:
                x=pd.read_csv(f,header=None,names=COLS)
        # Some Binance Vision monthly archives contain a header row while older ones do not.
        # Keep only rows with a numeric timestamp so both archive formats are handled safely.
        x['open_time']=pd.to_numeric(x['open_time'],errors='coerce')
        x=x[x['open_time'].notna()].copy()
        parts.append(x)
    d=pd.concat(parts,ignore_index=True)
    # Binance Vision timestamps may be milliseconds or microseconds depending on archive vintage.
    unit='us' if d.open_time.median()>1e14 else 'ms'
    d['time']=pd.to_datetime(d.open_time,unit=unit,utc=True,errors='coerce')
    d=d[d['time'].notna()].copy()
    for c in ['open','high','low','close','volume','taker_buy_base']: d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['open','high','low','close','volume'])
    return d.set_index('time').sort_index()

def ema(s,n): return s.ewm(span=n,adjust=False).mean()
def rsi(s,n=14):
    q=s.diff(); up=q.clip(lower=0); dn=-q.clip(upper=0)
    rs=up.ewm(alpha=1/n,adjust=False).mean()/dn.ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+rs)
def cci(h,l,c,n=20):
    tp=(h+l+c)/3; ma=tp.rolling(n).mean(); md=(tp-ma).abs().rolling(n).mean()
    return (tp-ma)/(0.015*md)
def indicators(x):
    x=x.copy(); c=x.close
    x['ema50']=ema(c,50); x['rsi14']=rsi(c)
    x['cci']=cci(x.high,x.low,c)
    x['vwap']=(x.close*x.volume).cumsum()/x.volume.cumsum()
    x['taker_buy_ratio']=x.taker_buy_base/x.volume.replace(0,np.nan)
    return x

def resample(d,rule):
    a=d.resample(rule,label='right',closed='right').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum','taker_buy_base':'sum'}).dropna()
    return indicators(a)

def main():
    d=load_2025(); m1=indicators(d); m5=resample(d,'5min'); h1=resample(d,'1h')
    # Reverse-engineered from the supplied observation CSV. These are hypotheses, not the original proprietary formula.
    f=pd.DataFrame(index=d.index)
    f['price']=d.close
    f['1m_ema50']=m1.ema50
    f['5m_minus_placeholder']=np.nan
    f['5m_taker_buy_ratio']=m5.taker_buy_ratio.reindex(f.index,method='ffill')
    f['1h_cci']=h1.cci.reindex(f.index,method='ffill')
    f['1h_vwap']=h1.vwap.reindex(f.index,method='ffill')
    # Conservative core rules from strongest splits; avoids price-level overfit where possible.
    f['short_on']=f['1h_cci']>30.33
    f['long_on']=f['1h_vwap']<=f['price']  # relative proxy; absolute 78219 split is sample-specific
    for side in ['long','short']:
        on=f[f'{side}_on'].fillna(False)
        starts=on & ~on.shift(1,fill_value=False)
        rows=[]
        for t in f.index[starts]:
            p=f.at[t,'price']; pos=f.index.get_loc(t)
            row={'time':t,'side':side,'entry':p}
            for mins in [5,15,30,60,240]:
                j=min(pos+mins,len(f)-1); q=f.iloc[j].price
                row[f'ret_{mins}m_pct']=(q/p-1)*100*(1 if side=='long' else -1)
            rows.append(row)
        pd.DataFrame(rows).to_csv(OUT/f'{side}_events.csv',index=False)
    allx=[]
    for side in ['long','short']:
        p=OUT/f'{side}_events.csv'
        if p.exists() and p.stat().st_size: allx.append(pd.read_csv(p))
    ev=pd.concat(allx,ignore_index=True) if allx else pd.DataFrame()
    if len(ev):
        summary=[]
        for side,g in ev.groupby('side'):
            z={'side':side,'signals':len(g)}
            for mins in [5,15,30,60,240]:
                c=f'ret_{mins}m_pct'; z[f'win_{mins}m_pct']=(g[c]>0).mean()*100; z[f'avg_{mins}m_pct']=g[c].mean()
            summary.append(z)
        pd.DataFrame(summary).to_csv(OUT/'summary.csv',index=False)
        print(pd.DataFrame(summary).to_string(index=False))
if __name__=='__main__': main()
