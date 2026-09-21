# 한걸음 · 一句一步

通过对话句子学习韩语的轻量网站。所有月份、日期和关卡均可自由选择。访客可以试学；登录同一个 ChatGPT 账号后，手机和电脑从云端读取各自账号的进度。

## 站内实际课程

- 4,006 关，8,154 条去重对话文本，6,351 个去重词条。
- 180 天，每天 240 分钟，共 720 小时；新课日按实际新增词汇安排为 19–54 个词条，首周最多 24 个、第二周最多 36 个、第一月最多 48 个，每五天复习，每月阶段检验。每天列出实际课程 ID，词句总量不计入任何站外材料或重复复习。
- 44,985 个可点击词块，点词后显示原形、本句词义、助词和语尾，并可听原形或整句读音；不提供整句展开面板。词典词条可直接核对国语院来源。
- 15,117 段固定 ko-KR-SunHiNeural 音频（含保留的旧文本音频）；句子、词条、拼读示例都有音频。提供保持音高的 0.8 倍速。
- 原始 MP3 保存在本地 `content/audio/`，生产音频通过站点 R2 提供；基础音频及本轮新增的词语音频保留在 `public/audio/`。本地原文件保留，源代码构建不再重复包含整套音频；原始 14,325 段还可从 v6 源码提交 `ba4c81c8d0402bddb3a30f85c744f682081da5ff` 恢复。静态文件均直接复制原文件，不转码。
- 课程按关加载，浏览器只接收精简目录；去重词句统计由服务端返回，完整统计索引不进入首页脚本。日程的重复说明与关卡引用压缩存储，并逐日校验还原结果。目录按月份、日期显示当天对话。日程每组四关，可以分多天完成。
- 每关听力检查先隐藏韩文，听完后再选中文；首次错误、未听完或使用提示会进入待巩固，登录后安排一天内再练。36 个基础关卡的 72 道题及 4 道扩展题采用逐题编写的对比选项，其余扩展题保持原选项。

词条按原形文字去重，包含词典词汇、依存名词以及基础课中的常用表达，并非全部都是单一词汇词元。句子去掉空格和标点后去重。学过的数量是接触记录，不是熟练度证明。

| 月份 | 内容重点 | 累计站内词条 | 累计去重对话 |
| --- | --- | ---: | ---: |
| 1 | 拼读、基础句式与生活表达 | 895 | 792 |
| 2 | 熟悉日常对话，稳固 TOPIK I 基础 | 2,160 | 2,244 |
| 3 | 经历、理由与长句，进入 TOPIK II | 3,124 | 3,807 |
| 4 | 社会情境、信息核实与概括 | 4,158 | 5,187 |
| 5 | 抽象观点、让步与论证 | 5,215 | 6,854 |
| 6 | 综合运用、限时训练与 TOPIK 6 检验 | 6,351 | 8,154 |

TOPIK 6 是冲刺目标，课程量或学习时长不保证考试结果。阶段测评需要实际听力、阅读和写作成绩；写作需要有依据的反馈。当前不提供完整题库或自动教师批改。详见 [180 天日程](docs/180-day-plan.md)。

## 内容来源与审校

新增对话取自韩国国立国语院韩国语—汉语学习词典的 2023-09-01 文本快照，保留原词条及义项 ID。词典中文词义来自原资料；整句中文经过翻译及 Codex AI 对照原韩文逐句审校，并修正 627 对发布对话。旧的 36 关 / 216 句作为基础课程保留，其 ID 与保存的用户进度兼容。

发布对话的整句韩中对照有 AI 编辑审校记录。点词注释使用 Kiwi 形态分析、来源约束的语境义项选择、单独编写的语法说明及可追踪的编辑修正。词典例句目标词只出现一次时采用该例句所属的来源义项；重复出现时分别判断。常用词在快照中缺失时使用明确标注的课程补充释义。未匹配义项、不明专名及未经编辑确认的本动词词性与助动词义项冲突会阻止正式生成；局部草稿不能通过发布检查。没有把替换单词套模板算成新的对话。2026-09-21 定向复核 402 处本动词/助动词疑点及全部 82 处 어떤，修正 398 处义项，详见 `docs/context-safety-review.json`；这是 AI 编辑复核，不是独立教师认证。

文本署名国立国语院；使用及改编的文本以 CC BY-SA 2.0 KR 提供，保留来源和修改说明。详细出处、数据 SHA256、修改内容见 [provenance.json](content/provenance.json) 和站内 [来源说明](public/content-sources.html)。未使用原词典录音，音频为 SunHi 重新合成。

音频检查解码、静音和削波；旧文件仅在 SHA-256 与通过检查的基准版本一致时复用结果。基准版本的 8,156 条句子记录经过不提供原文提示的 Whisper 转写检查；低匹配片段单独复核，核对数字、单位和同音转写，22 对仍有疑点的对话已排除。先前注释改进新增的词语、词块及一条更正拼写的句子未计入旧的转写覆盖；本次 90 分改进没有新增或改写音频。信号、转写检查不等同于母语者对读音和语调的逐条听审，也不构成零错误保证。尚未获得独立教师对全库的认证；自动选择通过并不证明每处语言表达绝对无误。

## 云端与校验

D1 按账号保存对话位置、已读词句、完成状态、复习时间与高级关卡的书面回复。失败时不推进学习步骤。并发复习不会重复延后复习日程，书面回复使用版本检测防止旧设备覆盖新内容。访客记录不持久化。

- `docs/content-audit.json`：实际内容、释义、音频引用、日程与审校覆盖校验。
- `docs/context-editorial-review.json`：本轮编辑覆盖、词形修正和语境抽样复核范围。
- `docs/context-audio-delivery-tests.json`：792 段新增音频通过本地生产 Worker 的字节一致性验证。
- `docs/context-annotation-coverage.json`：每个词语采用的具体义项、来源与选择方式。
- `content/context-senses.json`：可重放的语境选择记录；`context-editorial.json`、`context-morphology.json` 与 `context-lexicon.json` 保存编辑、词形及补充释义。
- `docs/course-compatibility.json`：与本轮修改前提交比对全部关卡、句子 ID、顺序和答案位置；此次不改整句韩中正文，维持已有进度兼容。
- `docs/schedule-quality.json`：按初、中、高级目标词安排的实际每日负荷。
- `docs/audio-signal-tests.json`：全部音频的 PCM 解码、时长、静音和削波结果。
- `docs/audio-transcription-tests.json`：整句自动语音复核及检查边界。
- `docs/audio-storage-tests.json`：对象存储读取、分段播放、缓存及导入保护检查。
- `docs/audio-cloud-import.json`：全部云端音频写入后读回的 SHA-256 核对结果。
- `docs/progress-tests.json`：24 项本地生产 Worker 与 D1 的账号隔离、续学、首次答错/提示、短间隔巩固、并发、版本冲突及完整学习历史统计验证。
- `docs/client-payload.json`：正式构建中的目录、日程脚本体积和全库统计索引隔离检查，不代表真实网络速度测量。
- `docs/quality-90-browser.json`：本轮听力检查和分组日程的实际浏览器验证。
- `docs/browser-qa.json`：当前版浏览器交互和手机尺寸验证，不冒充手机真机验收。

## 开发

需要 Node.js 22.13+。构建直接使用已经审校、提交的课程产物，不要求运行翻译模型。

```sh
npm ci
npm run dev
npm run build
```

完整课程正文按关提交在 `public/course/`，排序和去重索引在 `content/course-index.json`；整库合并文件只作为本地编译缓存，避免单文件过大。

课程生成顺序：`compile-curriculum.py` → `contextual_senses.py` → `apply-context.py` → `schedule-course.py` → `build-course-index.py` → `build-study-plan.py` → `generate-audio.py` → `build-audio-storage-index.py` → `build-content-notice.py` → `validate-course.py`。词形与翻译编译读取忽略提交的来源快照和翻译缓存；已发布的选择决定保存在 `content/context-senses.json`，未改动的输入可直接重放。新输入由本机 Ollama 的 `qwen3.6:35b` 从给定义项中选择，疑点需要编辑处理。`apply-context.py --partial` 只供本地校对，不可用于发布。站点构建只使用已提交的课程产物，不运行模型。

新增音频必须先作为 `public/audio/` 的原文件随站点发布，或通过 `scripts/import-course-audio.py` 导入站点 R2，再发布引用它的课程。维护接口默认关闭；仅在 Sites 配置短期 `COURSE_AUDIO_IMPORT_KEY` secret 与 `COURSE_AUDIO_IMPORT_EXPIRES` 毫秒时间戳后可用，完成后删除两项并重新发布。脚本从标准输入读取密钥，不保存密钥。服务端只接受已提交清单中的文件和 SHA-256，每条写入后读回验证，重复上传保持幂等。它不修改学习进度，也不代替 Sites 的版本发布接口。

新增词典筛选与词形处理需要 Python/kiwipiepy；TTS 需要 edge-tts；信号验证使用 numpy 与 macOS afconvert。既有整句转写检查使用 mlx-whisper 与 scipy，本轮未新增全库转写或人工听审。依赖、原始数据与模型放在忽略的 `.sites-runtime`。语言审校记录不能由运行测试替代。

本地测试：

```sh
node --import ./scripts/sites-env.mjs node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_brave_vertigo.sql
npm start -- --port 8787
python3 scripts/test-progress.py
python3 scripts/validate-course.py
python3 scripts/check-client-payload.py
```

`question-overrides.json` 保存已逐题复核的干扰项。重新生成时保留其余已发布题目，新增题目必须提供编辑选项，避免自动改写制造多个正确答案。

`test-progress.py` 只连接 127.0.0.1:8787，并使用独立测试身份，不访问生产学习记录。生产身份由 Sites 登录层提供。数据库迁移保持不变，生产发布由 Sites 管理。
