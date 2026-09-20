# 한걸음 · 一句一步

通过短对话学习韩语的轻量网站。手机和电脑使用同一个 ChatGPT 账号登录，以服务器中的进度继续学习。

## 当前实际内容

- 36 关，6 个主题阶段，从生活对话过渡到社会和学术论证。
- 216 条对话（216 个去重独立句）、472 个核心词条。词条包含单词、助词及常用搭配，按原形文字去重，并非 472 个纯词汇词元。
- 729 个固定 `ko-KR-SunHiNeural` 音频文件，句子、词条和拼读示例都有音频；0.8 倍速播放保持音高。
- 一句一学、句中词条释义、两句理解检查、过关解锁和到期对话复习。
- 登录账号下的对话位置、学过词句、完成关卡、复习时间与高级关卡书面回复保存在 D1。
- 不使用 localStorage 作为学习进度来源。服务端保存失败时不推进学习步骤，保留当前内容以便重试。

**这是首批体验课程，完整半年课程尚未完成。** 本项目不会把闯关、词句接触次数当成 TOPIK 等级认证。

## 半年课程的设计目标

按每天 4 小时以上规划，累计内容目标为 6,000 个核心词条和 8,000 个独立句。该数量是项目设计目标，不是 TOPIK 官方词汇门槛，也不代表现在已经收录。

| 月份 | 内容重点 | 累计词条目标 | 累计句子目标 |
| --- | --- | ---: | ---: |
| 1 | 拼读、基本句式、生活表达 | 800 | 1,000 |
| 2 | 日常情境、连接与时态 | 1,800 | 2,200 |
| 3 | 经历、比较、解释理由 | 3,000 | 3,800 |
| 4 | 社会话题、转述、长句 | 4,200 | 5,200 |
| 5 | 观点、论证、阅读 | 5,200 | 6,600 |
| 6 | 综合运用、写作、模考 | 6,000 | 8,000 |

每月必须以听力、阅读、写作测评调整学习计划。TOPIK II 纸笔 6 级为 230–300 分；机考采用不同尺度。当前不含完整模考、自动作文批改或独立教师审校。

## 内容质量边界

韩中对话为原创内容，并完成作者本轮语义自查。结构、计数、重复、翻译字段、音频引用和文件可解码性可通过脚本检查；这些检查不证明每一条翻译或发音绝对正确。独立双语审校、729 段逐条人工听审、手机真机及线上两设备验收尚未完成。

- `content/course.json` 是实际发布的课程源。
- `content/audio-manifest.json` 记录合成音色、文本、路径和文件大小。
- `docs/content-audit.json` 记录内容检查范围。
- `docs/progress-tests.json` 记录本地接口验证结果；不代表线上端到端验证。

参考：[NIIED 官方考试说明](https://www.niied.go.kr/web/NIIED/contents/niiedEng/eng_topikOverview)、[国立国语院韩中词典](https://krdict.korean.go.kr/)、[Microsoft 语音列表](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts)。

## 开发与部署

需要 Node.js 22.13 或更高版本；使用 npm 锁文件安装。

```sh
npm ci
npm run dev
npm run build
```

本地开发的登录页模拟测试账号；生产身份由 Sites 登录层提供。`.openai/hosting.json` 只存站点 ID 和逻辑数据库绑定，不存凭据。

数据库结构由 `db/schema.ts` 和不可变的 Drizzle 迁移管理。新数据库先运行构建，再依照模板说明把迁移应用到本地 `.wrangler/state`。生产迁移由 Sites 发布流程执行。

```sh
npm run db:generate
node --import ./scripts/sites-env.mjs node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_brave_vertigo.sql
npm start -- --port 8787
python3 scripts/test-progress.py
```

`test-progress.py` 只连接 `127.0.0.1:8787`，用独立测试身份检查用户隔离、续学、重复请求、并发复习及书面回复冲突，不访问生产数据。

生成音频需要 Python 的 `edge-tts`。固定资产无需在访客浏览器请求 TTS 服务；网站运行时不需要语音 API 密钥。

```sh
python3 scripts/generate-audio.py
python3 scripts/validate-course.py
```

音频完整性脚本使用 macOS `afinfo`；它检查可解码性和时长，不替代人工听审。网站暴露一个可选的只读 WebMCP 进度工具，普通浏览器不支持时会正常跳过。
