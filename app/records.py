"""Local history and PDF exports. Session IDs, never titles, determine paths."""
import json
import time
import uuid
import os
import sys
import subprocess
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

def open_folder(folder):
    if sys.platform=='win32':os.startfile(str(folder))
    elif sys.platform=='darwin':subprocess.Popen(['open',str(folder)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:raise ValueError('Open folder supports Windows and macOS.')

def atomic_text(path, text):
    path=Path(path)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temp.write_text(text,encoding='utf-8')
        for attempt in range(6):
            try:
                temp.replace(path)
                return
            except PermissionError:
                if attempt==5:raise
                time.sleep(.05*(attempt+1))
    finally:
        temp.unlink(missing_ok=True)

def read_record(data, sid):
    if not sid or not all(c.isascii() and (c.isalnum() or c=='-') for c in sid):
        raise ValueError('无效的录音编号。')
    record=json.loads((Path(data)/sid/'session.json').read_text(encoding='utf-8'))
    if not isinstance(record,dict) or record.get('id')!=sid or not isinstance(record.get('segments'),list):
        raise ValueError('录音编号不匹配。')
    return record

def history(data):
    result=[]
    for file in Path(data).glob('*/session.json'):
        try:
            s=read_record(data,file.parent.name)
            result.append({k:s.get(k) for k in ('id','title','createdAt','samples','summaryStatus','status')})
        except (ValueError,OSError,TypeError):
            continue
    return sorted(result,key=lambda s:s.get('createdAt') or 0,reverse=True)

def pdf_bytes(record, kind):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    style=ParagraphStyle('body',fontName='STSong-Light',fontSize=11,leading=18,wordWrap='CJK')
    heading=ParagraphStyle('title',parent=style,fontSize=18,leading=26,spaceAfter=16)
    section=ParagraphStyle('section',parent=style,fontSize=14,leading=21,spaceBefore=12,spaceAfter=6)
    stream=BytesIO()
    title=record.get('title') or record['id']
    story=[Paragraph(escape(title),heading)]
    if kind=='summary':
        lines=(record.get('summary') or '总结尚未生成 / Summary not available.').splitlines()
    else:
        lines=[]
        for row in record['segments']:
            lines.append(f"[{int(row['start']//60):02}:{int(row['start']%60):02}] {row['text']}")
            if row.get('translation'):lines.append(row['translation'])
    table=[]
    def flush_table():
        if not table:return
        count=max(map(len,table))
        cells=[[Paragraph(escape(cell.replace('**','')),style) for cell in row+['']*(count-len(row))] for row in table]
        block=Table(cells,colWidths=[499/count]*count,repeatRows=1,hAlign='LEFT')
        block.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf3ef')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.extend([block,Spacer(1,10)]);table.clear()
    for line in lines:
        if line.strip().startswith('|'):
            row=line.strip().strip('|').split('|')
            if not all(set(cell.strip())<=set('-: ') for cell in row):table.append([cell.strip() for cell in row])
            continue
        flush_table()
        if line.startswith('# ' ) and line[2:].strip()==title:continue
        is_heading=line.startswith('#')
        text=(line.lstrip('#').strip() if is_heading else line).replace('**','')
        story.extend([Paragraph(escape(text) or ' ',section if is_heading else style),Spacer(1,6)])
    flush_table()
    SimpleDocTemplate(stream,title=title,author='CodexRecorder',leftMargin=48,rightMargin=48,topMargin=48,bottomMargin=48).build(story)
    return stream.getvalue()
