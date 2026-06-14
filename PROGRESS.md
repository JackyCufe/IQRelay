# Agents League Hackathon — 进度报告
> 更新时间：2026年6月11日 00:30
> 项目：/Users/jacky/build/hackathon/Microsoft/agents-league-project

---

## 一、比赛信息

###当前状态（2026年6月11日凌晨）

**代码：全部完成 ✅ | 测试：12/12通过 ✅ | 待做：Teams Sideload + TC1-TC5验证 + 录Demo**
- 6 Agent Pipeline 完整交互（S1→S2a→S2b→S3→S4→S5a→S5b→S5c→S6）
- Adaptiv Cards v1.5 + 可编辑表单 + S3/S4审批下拉- Stage4硬门禁 +3轮info_needed强制拒绝 +自学习闭环- 返工计数器 +回退链 +统一知识库Schema- Teams App Package已打包待Sideload

---## 一、比赛信息

|项目 |内容 |
|---|---|
|赛道 |🧠 Reasoning Agents — Build with Microsoft Foundry |
|Microsoft IQ |Foundry IQ (Azure AI Search) |
|截止时间 |6月14日11:59 PM PT（北京时间6月15日约15:00）|
|项目名称 |AI需求链Agent — Requirements Pipeline Agent |

---

## 二、技术架构

```
Teams Bot (Bot Framework SDK)
 ↓
6-Agent Pipeline (DeepSeek API via OpenAI SDK)
 ├─ 01 Gatekeeper — 需求守门+四问提取
 ├─ 02 Value Transform — 结构化验收标准
 ├─ 03 Scenario Test — 客户视角测试用例
 ├─ 04 Release Review — 规则判定发版
 ├─ 05 Feedback Analysis — 客户反馈AI分析（向外看）
 └─ 06 Process Analysis — 团队协作瓶颈分析+写回Foundry IQ（向内看）
 ↓
Foundry IQ (Azure AI Search)
 — 10条Mock数据（6条Pipeline经验 +4条Reference Doc）
 — 制造业场景：汽车零部件供应商IT部门
```

---

## 三、Microsoft技术使用

|技术 |状态 |详情 |
|---|---|---|
|Azure AI Search (Foundry IQ) |✅已创建 |`agents-league`服务运行中，Index已建 |
|Azure AI Foundry项目 |✅已创建 |`agents-league-proj`，未部署模型（订阅限制） |
|Bot Framework SDK |✅已连接 |Emulator本地测试通过 |
|Azure Bot Service |⏳进行中 |`agents-league-bot`刚创建，待配ngrok |
|Adaptive Cards |✅已完成 |7张卡片已写，真实Teams原生支持 |
|Azure Storage |❌未创建 |可选，JSON归档 |

---

## 四、项目文件清单

```
agents-league-project/
├── .env # API密钥（已填DeepSeek+AI Search）
├── .env.template # 配置模板
├── requirements.txt # Python依赖
├── demo.py # 本地命令行演示
├── bot.py # Teams Bot入口
├── test_connectivity.py # 连通性测试
├── schemas.md # 6个Schema数据契约
├── agents/
│ ├──01-gatekeeper.md # 全英文
│ ├──02-value-transform.md
│ ├──03-scenario-test.md
│ ├──04-release-review.md
│ ├──05-feedback-collect.md # Feedback Analysis (outward)
│ └──06-retrospective.md # Process Analysis (inward)
├── pipeline/
│ ├── __init__.py
│ ├── agent_runner.py # OpenAI SDK + DeepSeek
│ ├── schema_builder.py # Schema组装+校验
│ ├── foundry_iq.py # AI Search集成
│ ├── pipeline.py # 6-Agent主流程
│ └── cards.py # Adaptive Cards（真实Teams渲染）
├── config/
│ ├── __init__.py
│ ├── config.py # 集中配置
│ └── pipeline_config.yaml # 流程配置
└── docs/
 ├── architecture.md # 架构文档（⚠️需更新）
 └── sprint-plan.md # 进度追踪（已更新）
```

---

## 五、Foundry IQ 数据（10条）

### Pipeline经验（6条）
|ID |需求 |类型 |
|---|---|---|
|`mfg-req-001` |产线质检拍照自动分类缺陷| customer_reported|
|`mfg-req-002` |库存同步30秒延迟修复 | internal_improvement|
|`mfg-req-003` |ISO9001三年追溯审计日志| compliance |
|`mfg-req-004` |博世EDI对接 | competitive|
|`mfg-req-005` |AI需求预测降低库存 | customer_reported|
|`mfg-req-006` |工具间扫码借还系统 | customer_reported|

### Reference Doc（4条）
|ID |文档 |
|---|---|
|`ref-edi-001` |EDI850对接Bosch指南 |
|`ref-qc-001` |质检SOP v4.2缺陷分类标准|
|`ref-iot-001` |Azure IoT设备接入手册|
|`ref-supplier-001` |供应商15步入网清单|

---

## 六、⚠️ 进行中任务

|任务 |状态 |下一步 |
|---|---|---|
|**配置Teams Bot** |⏳ |(1)ngrok注册→获得authtoken→`ngrok config add-authtoken` (2)Azure Bot Configuration→Manage Password→创建Client Secret (3)把ngrok URL填入Messaging Endpoint (4)把App ID+Password填入.env |
|**下载Teams App** |⏳ |`brew install --cask microsoft-teams`（需Mac密码） |
|**跑通真实Teams** |⏳ |启动bot.py +ngrok→Teams里发消息测试 |

---

## 七、❌ 待做任务

|优先级 |任务 |说明 |
|---|---|---|
|🔴 P0 |**录制Demo视频**（≤5分钟） |最重要！CLI+Teams双场景 |
|🔴 P0 |**GitHub仓库公开** |含完整源码+README |
|🔴 P0 |**架构图** |更新`docs/architecture.md`|
|🟡 P1 |**README.md** |项目描述、使用说明、技术栈 |
|🟡 P1 |**Azure Storage** |可选，JSON全链路归档 |
|🟢 P2 |**Adaptive Card调优** |真实Teams上验证渲染效果 |

---

## 八、Demo视频脚本建议（5分钟）

|时间 |内容 |工具 |
|---|---|---|
|0:00-0:30 |开场：AI需求链问题背景 |旁白 |
|0:30-1:30 |**Foundry IQ知识查询**：新人问 `?how to set up EDI with Bosch`→混合检索（文档+历史教训） |Teams/CLI |
|1:30-3:30 |**完整Pipeline演示**：QC inspection需求→6个Agent接力→Foundry IQ自动沉淀 |CLI |
|3:30-4:30 |**闭环验证**：再查 `?scratch defect classification`→上次Pipeline经验已在知识库 |Teams |
|4:30-5:00 |总结：Self-improving organizational knowledge |旁白 |

---

## 九、成本估算

|项目 |数量 |
|---|---|
|单次完整Pipeline token |~37,600 tokens |
|单次Pipeline费用 |~$0.022（人民币0.16元） |
|Foundry IQ容量 |50MB（够存~25,000条记录） |
|Azure Bot |Free Tier（0费用） |
|DeepSeek余额 |已充值 |

---

## 十、关键账号

|服务 |资源名 |位置 |
|---|---|---|
|Azure订阅 |Hackathon |中国大陆（受限） |
|Azure AI Search |`agents-league` |Central US |
|Foundry项目 |`agents-league-proj` |East US |
|Azure Bot |`agents-league-bot` |East US |
|资源组 |`agents-league-hackathon` |- |
|AI Search Index |`foundry-iq-index` |- |
