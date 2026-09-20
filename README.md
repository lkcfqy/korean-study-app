# 한걸음 · 一句一步

通过对话句子学习韩语的轻量网站。所有月份、日期和关卡均可自由选择。访客可以试学；登录同一个 ChatGPT 账号后，手机和电脑从云端读取各自账号的进度。

## 站内实际课程

- 4,006 关，8,154 个去重独立句，6,150 个去重核心词条。
- 180 天，每天 240 分钟，共 720 小时；新课日按实际新增词汇均衡为 34–59 个词条，每五天复习，每月阶段检验。每天列出实际课程 ID，词句总量不计入任何站外材料或重复复习。
- 44,985 个可点击词块，点词后显示原形、词义参考、助词和语尾，并可听原形或句中读音；不提供整句展开面板。词典词条可直接核对国语院来源。
- 14,325 段固定 ko-KR-SunHiNeural 音频；句子、词条、拼读示例都有音频。提供保持音高的 0.8 倍速。
- 原始 MP3 保存在 `content/audio/`，完整音频通过站点 R2 存储提供；基础课程的 729 段同时保留为静态缓存。迁移只复制原文件，不转码或降低音质，页面更新无需重新打包全部音频。
- 课程按关加载，避免把整个正文词库放进首页脚本。目录按月份、日期显示当天对话。

词条按原形文字去重，包含词典词汇、依存名词以及基础课中的常用表达，并非全部都是单一词汇词元。句子去掉空格和标点后去重。学过的数量是接触记录，不是熟练度证明。

| 月份 | 内容重点 | 累计站内词条 | 累计站内独立句 |
| --- | --- | ---: | ---: |
| 1 | 拼读、基础句式与生活表达 | 1,083 | 1,000 |
| 2 | 熟悉日常对话，稳固 TOPIK I 基础 | 2,023 | 2,200 |
| 3 | 经历、理由与长句，进入 TOPIK II | 3,102 | 3,798 |
| 4 | 社会情境、信息核实与概括 | 3,985 | 5,198 |
| 5 | 抽象观点、让步与论证 | 4,884 | 6,598 |
| 6 | 综合运用、限时训练与 TOPIK 6 检验 | 6,150 | 8,154 |

TOPIK 6 是冲刺目标，课程量或学习时长不保证考试结果。阶段测评需要实际听力、阅读和写作成绩；写作需要有依据的反馈。当前不提供完整题库或自动教师批改。详见 [180 天日程](docs/180-day-plan.md)。

## 内容来源与审校

新增对话取自韩国国立国语院韩国语—汉语学习词典的 2023-09-01 文本快照，保留原词条及义项 ID。词典中文词义来自原资料；整句中文经过翻译及 Codex AI 对照原韩文逐句审校，并修正 627 对发布对话。旧的 36 关 / 216 句作为基础课程保留，其 ID 与保存的用户进度兼容。

所有发布对话均有完整韩中审校记录。新增拆解使用 Kiwi 形态分析、官方词典义项和语法说明；非目标多义词列出词典参考义，未声称全部都是本句唯一义。没有把改词套模板计为新对话。

文本署名国立国语院；使用及改编的文本以 CC BY-SA 2.0 KR 提供，保留来源和修改说明。详细出处、数据 SHA256、修改内容见 [provenance.json](content/provenance.json) 和站内 [来源说明](public/content-sources.html)。未使用原词典录音，音频为 SunHi 重新合成。

全部音频检查解码、静音和削波。8,156 段完整句子经过不提供原文提示的 Whisper 转写检查；低匹配片段单独复核，核对数字、单位和同音转写，22 对仍有疑点的对话已排除。信号、转写检查不等同于母语者对读音和语调的逐条听审，也不构成零错误保证。没有独立教师对全库的认证。

## 云端与校验

D1 按账号保存对话位置、已读词句、完成状态、复习时间与高级关卡的书面回复。失败时不推进学习步骤。并发复习不会重复延后复习日程，书面回复使用版本检测防止旧设备覆盖新内容。访客记录不持久化。

- `docs/content-audit.json`：实际内容、释义、音频引用、日程与审校覆盖校验。
- `docs/audio-signal-tests.json`：全部音频的 PCM 解码、时长、静音和削波结果。
- `docs/audio-transcription-tests.json`：整句自动语音复核及检查边界。
- `docs/audio-storage-tests.json`：对象存储读取、分段播放、缓存及导入保护检查。
- `docs/audio-cloud-import.json`：全部云端音频写入后读回的 SHA-256 核对结果。
- `docs/progress-tests.json`：本地生产 Worker 与 D1 的账号隔离、续学、并发与版本冲突验证。
- `docs/browser-qa.json`：当前版浏览器交互和手机尺寸验证，不冒充手机真机验收。

## 开发

需要 Node.js 22.13+。构建直接使用已经审校、提交的课程产物，不要求运行翻译模型。

```sh
npm ci
npm run dev
npm run build
```

完整课程正文按关提交在 `public/course/`，排序和去重索引在 `content/course-index.json`；整库合并文件只作为本地编译缓存，避免单文件过大。

课程生成顺序：`compile-curriculum.py` → `build-course-index.py` → `build-study-plan.py` → `generate-audio.py` → `build-audio-storage-index.py` → `build-content-notice.py` → `validate-course.py`。前者使用忽略提交的原始词典与翻译缓存，以及已提交的审校修正；站点构建无需这些缓存。`compile-breakdowns.py` 只编译旧基础课程，之后须重新编译完整课程。

新增音频先通过 `scripts/import-course-audio.py` 导入站点 R2，再发布引用它的课程。维护接口默认关闭；仅在 Sites 配置短期 `COURSE_AUDIO_IMPORT_KEY` secret 与 `COURSE_AUDIO_IMPORT_EXPIRES` 毫秒时间戳后可用，完成后删除两项并重新发布。脚本从标准输入读取密钥，不保存密钥。服务端只接受已提交清单中的文件和 SHA-256，每条写入后读回验证，重复上传保持幂等。它不修改学习进度，也不代替 Sites 的版本发布接口。

新增词典筛选与拆解需要 Python/kiwipiepy；TTS 需要 edge-tts；语音复核使用 mlx-whisper、numpy、scipy 与 macOS afconvert。依赖、原始数据与模型放在忽略的 `.sites-runtime`。语言审校记录不能由运行测试替代。

本地测试：

```sh
node --import ./scripts/sites-env.mjs node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_brave_vertigo.sql
npm start -- --port 8787
python3 scripts/test-progress.py
python3 scripts/validate-course.py
```

`test-progress.py` 只连接 127.0.0.1:8787，并使用独立测试身份，不访问生产学习记录。生产身份由 Sites 登录层提供。数据库迁移保持不变，生产发布由 Sites 管理。
