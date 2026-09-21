"""Publish attribution and a precise description of the editorial work."""
from course_data import load_course
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
course = load_course()
index = json.loads((ROOT/'content/course-index.json').read_text())
audio = json.loads((ROOT/'content/audio-manifest.json').read_text())
added = [l for l in course if l.get('source')]
source = json.loads((ROOT/'.sites-runtime/corpus/nikl-source.json').read_text())
source.update({
    'author': 'National Institute of Korean Language (국립국어원)',
    'copyrightPolicy': 'https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo',
    'courseModifications': 'Selection and ordering; Chinese sentence translation and AI editorial correction; morphological annotations; 180-day allocation; comprehension questions.',
    'sourceAudioUsed': False,
    'courseTextLicense': 'CC BY-SA 2.0 KR',
    'sentenceTranslationIsOfficial': False,
})
(ROOT/'content/provenance.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
body=f'''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>来源与审校 · 一句一步</title>
<style>body{{font-family:system-ui,-apple-system,sans-serif;background:#f8faf8;color:#23372e;line-height:1.85;margin:0}}main{{max-width:780px;margin:auto;padding:40px 22px 64px}}h1{{font-size:30px}}h2{{font-size:21px;margin-top:32px}}a{{color:#206647;text-underline-offset:4px}}.numbers{{padding:20px;background:#eaf3ec;border-radius:16px;font-weight:650}}p{{overflow-wrap:anywhere}}small{{color:#627168}}</style>
<main><a href="/">← 返回学习</a><h1>来源与审校说明</h1>
<p class="numbers">{len(course):,} 关 · {index['totalWords']:,} 个去重词条 · {index['totalSentences']:,} 条去重对话<br>180 天 · 每天 4 小时</p>
<h2>这些数字对应什么</h2>
<p>全部词句均收录在站内。对话文本忽略空格和标点后去重，包含短回答及一句以上的发言，不等于同等数量的独立句型；复习不计为新增。动词、形容词尽量按词典原形统计。词条包含单词、依存名词及基础课中的常用表达，不是 TOPIK 官方词汇门槛。学过的数量表示接触记录，掌握程度仍需回忆和测评验证。</p>
<h2>韩语、中文与点词注释</h2>
<p>新增的 {len(added):,} 段对话取自韩国国立国语院的<a href="https://krdict.korean.go.kr/chn">韩国语—汉语学习词典</a>，每关保留词条来源链接。词典中文义主要沿用原资料，并修正已发现的明显错字；整句中文由本课程翻译，经过完整韩中对照的 AI 逐句审校，不是国语院官方整句译文。保留的 36 段基础对话为本课程编写。</p>
<p>点击词语后显示本句采用的词义和必要的助词、语尾说明，不展开整句拆解。新增内容先还原词形，再结合完整韩中对话从词典候选义项中选择；常用语法与惯用搭配单独编写。词形修正、具体义项及编辑覆盖记录可追溯。原词典快照未收录的常用词使用课程补充释义，不伪装成国语院词条。</p>
<p>这一轮逐句审校检查了人物关系、否定、时间、金额、语气和惯用表达，并修正发现的误译，剔除原句书写有误或语音复核仍有疑点的对话。语境选择包含自动模型检查，另有对未匹配、形态歧义及已知误译的编辑复核；尚未取得独立韩语教师对全部译文和点词注释的逐条认证。</p>
<p>2026-09-21 的定向复核进一步检查了 402 处本动词与助动词义项疑点，以及全部 82 处 어떤 用法，共修正 398 处义项。构建会拦截尚未编辑确认的本动词词性与助动词义项冲突。这是针对已识别风险的 AI 编辑复核，未宣称全部词义零错误。</p>
<h2>180 天如何安排</h2>
<p>两个月一组，按词典目标词的初、中、高级顺序安排；这不是国语院对整段对话的等级认证。首周每天新增词条不超过 24 个，第二周不超过 36 个，第一月不超过 48 个，之后不超过 60 个。每组四关，一天的内容可以分多天完成。学习日同时安排隔天、一周、一个月的回忆复习，240 分钟只是参考投入；最后一个月内容的一月后复习需要延续到第 210 天。全部关卡随时可选。</p>
<h2>听力检查与巩固</h2>
<p>每关检查两句：默认不显示韩文，听完后才显示中文选项；也可以主动查看韩文提示继续练习。首次答错、未听完或看过提示，不计为首次独立听懂。登录后，这类关卡会进入待巩固列表，并在一天内再练；这不等于整关掌握率。36 个基础关卡的 72 道题，以及 4 道已发现问题的扩展题，使用逐题编写的对比选项；其余扩展题保留原有选项，尚未全部完成难度与歧义复核。</p>
<h2>固定 SunHi 读音</h2>
<p>句子、词条和拼读示例使用 {len(audio['entries']):,} 段固定的 ko-KR-SunHiNeural 合成音频，正常语速生成；慢速播放保留音高。句子整段合成，保留连读和语调，不拼接单词音频。</p>
<p>此前发布前做过音频解码、静音和削波检查，完整句子还经过不提供原文提示的自动转写复核，低匹配项单独复核。随后注释改进中新增的原形、独立词块和一条更正拼写的句子，有单独的信号检查，但未计入该基准转写报告。本次义项、听力流程和日程改进没有新增或改写音频；完整校验核对文件哈希与引用。自动转写与信号检查不能代替母语者逐条听审，尚未完成全部音频的人工听审。</p>
<h2>署名与许可</h2>
<p>原作者：韩国国立国语院（국립국어원）。原始文本快照日期：{html.escape(source['sourceDate'])}；<a href="{html.escape(source['mirror'])}">文本数据镜像</a>。选择、排序、整句中文翻译、点词注释、练习及日程是本课程所作的编译改动。</p>
<p>依据<a href="{source['copyrightPolicy']}">原资料版权政策</a>，课程中使用与改编的词典文本及本课程文本改编以<a href="{source['license']}">知识共享署名—相同方式共享 2.0 韩国许可（CC BY-SA 2.0 KR）</a>提供。转载这些文本请保留署名、来源、改动说明和相同许可。未使用词典网站的录音或其他多媒体素材；SunHi 音频为本项目重新合成，不是国语院录音。</p>
<h2>半年目标如何检验</h2>
<p>半年从零冲刺 TOPIK 6 是高强度目标。每月安排听力、阅读和写作检验；词句数量与投入时长不构成分数保证。测评尺度见<a href="https://www.niied.go.kr/web/NIIED/contents/niiedEng/eng_topikOverview">NIIED 官方 TOPIK 说明</a>。</p>
<small>课程与审校说明更新：2026-09-21</small></main></html>'''
(ROOT/'public/content-sources.html').write_text(body+'\n')
print('Published content notice and provenance')
