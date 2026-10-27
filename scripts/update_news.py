"""Daily industrial digitalization news aggregation, stdlib only.
Optional OPENAI_API_KEY enables Chinese headline/summary synthesis. No private data is sent.
"""
import datetime as dt, email.utils, html, json, os, re, time
import urllib.parse, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/news.json'
FALLBACKS={'工业 AI': 'assets/ai.svg', '设备监测': 'assets/monitor.svg', '数据与软件': 'assets/data.svg', '机器人': 'assets/robot.svg', '能源与效率': 'assets/energy.svg', '创业信号': 'assets/startup.svg'}
QUERIES=[
 ('工业 AI','industrial artificial intelligence manufacturing factory'),
 ('设备监测','industrial predictive maintenance condition monitoring sensors'),
 ('数据与软件','industrial IoT MES SCADA manufacturing software digital transformation'),
 ('机器人','factory robotics automation industrial inspection'),
 ('能源与效率','industrial energy efficiency monitoring manufacturing'),
 ('创业信号','industrial AI startup manufacturing SaaS funding'),
]
UA='IndustrialFrontierNewsReader/1.0 (+public RSS aggregation)'

def get(url,timeout=12):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml,application/xml,text/html,*/*'})
 with urllib.request.urlopen(req,timeout=timeout) as f:return f.read(550000)

def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s or ''))).strip()
def summarize(text,n=170):
 text=clean(text)
 return text[:n].rstrip(' ,.')+('…' if len(text)>n else '')

def iso(s):
 try:return email.utils.parsedate_to_datetime(s).astimezone(dt.timezone.utc).isoformat()
 except:return dt.datetime.now(dt.timezone.utc).isoformat()

def rss_items(query,category):
 query=query+' when:14d'
 rss='https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl=en-US&gl=US&ceid=US:en'
 root=ET.fromstring(get(rss))
 result=[]
 for item in root.findall('./channel/item')[:13]:
  name=clean(item.findtext('title'))
  link=clean(item.findtext('link'))
  desc=clean(item.findtext('description'))
  source=clean(item.findtext('source')) or 'Industry News'
  if not name or not link:continue
  title=re.sub(r'\s+-\s+'+re.escape(source)+r'$', '', name).strip()
  image=''
  # Prefer image URLs actually supplied by the syndication feed.
  for child in item:
   tag=child.tag.rsplit('}',1)[-1].lower()
   if tag in ('thumbnail','content') and child.attrib.get('url','').startswith('https://'):
    image=child.attrib['url'];break
  if not image:
   match=re.search(r'<img[^>]+src=[\"\'](https://[^\"\']+)',item.findtext('description') or '',re.I)
   if match:image=html.unescape(match.group(1))
  result.append(dict(title=title,summary=desc or title,source=source,url=link,category=category,date=iso(item.findtext('pubDate')),image=image,opportunity=''))
 return result

def company_url_from_google(link):
 # Google News links should remain linked to the source through Google's redirect.
 return link

def enrich_openai(items):
 key=os.environ.get('OPENAI_API_KEY','').strip()
 if not key:return items
 from urllib.error import HTTPError
 model=os.environ.get('OPENAI_MODEL','gpt-4.1-mini')
 payload={'model':model,'temperature':0.2,'response_format':{'type':'json_object'},'messages':[
 {'role':'system','content':'你是严谨的工业数字化情报编辑。仅根据输入标题与简述编写中文，不增加未证实的事实、数值、客户和商业成果。创业启发必须标明推测性质，不宣称市场验证。返回JSON对象 {"items":[{"id":0,"title":"...","summary":"...","opportunity":"..."}]}。每条标题≤42个汉字，summary≤110字，opportunity≤80字。'},
 {'role':'user','content':json.dumps([{'id':i,'title':a['title'],'summary':a['summary'],'category':a['category']} for i,a in enumerate(items)],ensure_ascii=False)}]}
 req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=90) as resp:res=json.load(resp)
  data=json.loads(res['choices'][0]['message']['content'])
  for r in data.get('items',[]):
   i=r.get('id')
   if isinstance(i,int) and 0<=i<len(items):
    for f,lim in [('title',100),('summary',350),('opportunity',250)]:
     if isinstance(r.get(f),str) and r[f].strip():items[i][f]=r[f].strip()[:lim]
 except Exception as e:print('AI enhancement skipped:',str(e)[:180])
 return items

def find_image(url):
 # Fetch images from publisher pages only, no generic / random stock images.
 try:
  data=get(url,timeout=7).decode('utf-8','ignore')
  for pattern in [r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)']:
   m=re.search(pattern,data,re.I)
   if m:
    link=urllib.parse.urljoin(url,html.unescape(m.group(1)))
    if link.startswith('https://'):return link
 except Exception:pass
 return ''

def run():
 now=dt.datetime.now(dt.timezone.utc)
 old=[]
 if OUT.exists():
  try:old=json.loads(OUT.read_text('utf-8')).get('articles',[])
  except:pass
 collected=[]
 for cat,q in QUERIES:
  try:
   items=rss_items(q,cat);print(cat,len(items));collected.extend(items)
  except Exception as e:print('RSS error',cat,str(e)[:120])
  time.sleep(.25)
 seen=set();new=[]
 for a in sorted(collected,key=lambda a:a['date'],reverse=True):
  key=re.sub(r'[^a-z0-9]','',a['title'].lower())[:70]
  if key in seen:continue
  seen.add(key);new.append(a)
  if len(new)==24:break
 if not new:
  print('No RSS response; preserve existing feed');return
 # Attach publisher OG image only if URL is already direct; Google News RSS links are redirects and often block crawlers.
 # Reuse existing curated article images on matching headline. Unknown images become graceful graphic fallbacks.
 previous={a.get('url'):a for a in old}
 for a in new:
  matched=previous.get(a['url'],{})
  a['image']=a.get('image') or (matched.get('image','') if not str(matched.get('image','')).startswith('assets/') else '') or FALLBACKS.get(a['category'],'assets/ai.svg')
  a['image_alt']='新闻来源图片或'+a['category']+'类别备用插画（非新闻现场照片）'
  a['opportunity']=matched.get('opportunity','')
  if not a['opportunity']:
   a['opportunity']={'设备监测':'可探索单类设备的异常预警、维护工单和月费服务。','数据与软件':'可验证工厂数据连接、自动报表和系统间集成需求。','工业 AI':'可从有明确 ROI 的单点 AI 工作流试点切入。','机器人':'可探索软件集成、视觉检测或维护服务，而非自研机器人。','能源与效率':'可从能耗可视化与异常分析切入，验证节能收益。','创业信号':'关注其首批客户、收费模式及部署成本，而不只看融资新闻。'}.get(a['category'],'验证细分客户真实需求。')
  a['summary']=summarize(a['summary'])
  a['analysis']=matched.get('analysis') or {'pain':'根据原文核实客户实际痛点，需进一步访谈','entry':'从可量化的单场景试点切入，验证需求','money':'可探索项目实施费与持续服务费，尚未验证','difficulty':'待调研现场数据接入、业务责任及部署成本'}
 # Use AI in small batches to limit request size and isolate failures.
 if os.environ.get('OPENAI_API_KEY'):
  for i in range(0,len(new),8):enrich_openai(new[i:i+8])
 else:print('No OPENAI_API_KEY: original-language titles are preserved; no fake Chinese translation')
 OUT.write_text(json.dumps({'updated_at':now.strftime('%Y-%m-%dT%H:%M:%SZ'),'articles':new},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Updated',len(new),'items')

if __name__=='__main__':run()
