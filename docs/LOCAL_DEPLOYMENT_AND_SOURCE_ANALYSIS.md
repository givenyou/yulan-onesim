# YuLan-OneSim 本地部署与源码调研报告

**调研日期：** 2026-10-28  
**项目：** YuLan-OneSim（玉兰-万象）  
**范围：** 官方网站工作台的公开介绍、仓库中的部署配置和主要源码结构

## 1. 结论摘要

**YuLan-OneSim 开源仓库支持在本地或自有服务器部署。**项目提供 Docker 部署方式，也提供从源码安装、单机 CLI 运行及单独启动前后端的开发方式。

需要区分“本地部署开源版”和“复制官网在线服务”：

- 本地部署指运行仓库里的仿真引擎、API 和前端，并连接用户自己选择的模型服务。
- `yulan-onesim.cn` 上的工作台是在线服务。其项目数据、账号体系、云端服务端代码和具体配额不一定包含在公开仓库里。仓库可用于本地运行和二次开发，但不能据此认定本地版与官网的全部功能、数据和服务实现完全相同。
- 使用云端模型时，仿真程序可以在本机运行，但模型请求仍会发往对应的云服务；只有模型推理服务也部署在本机或内网，才可实现模型推理本地化。

**建议入门方案：** Docker + 小规模仿真 + 可用的云端聊天模型和 embedding 模型。该方式不要求本机有 GPU。若目标是完全离线运行，需要另外准备并运行兼容的模型服务，硬件要求取决于所选模型。

## 2. 平台可以实现什么

YuLan-OneSim 是面向社会科学与群体行为研究的 LLM 多智能体模拟框架。它可以：

1. 选择预置场景，或设计、扩展自定义场景。
2. 定义不同类型的 Agent、角色画像、规划策略、记忆策略与交互流程。
3. 让 Agent 调用 LLM 产生决策，并通过事件、动作及环境状态推进仿真。
4. 运行仿真并记录事件、指标、Agent 状态或训练数据，供查看和后续分析。
5. 通过 Web UI 操作，或通过 CLI 自动化运行。
6. 使用分布式 master/worker 架构扩展运行；项目仓库也包含 AI 社会研究员及模型微调相关代码。

项目首页介绍了 50 多个预置场景，源码中实际有 50 个 `src/envs/` 场景目录。场景包括劳动市场、投票、舆论、传染病、法庭模拟、社会理论等。场景和仿真结果适合用于研究探索与假设检验；LLM 生成结果存在随机性、偏差或错误，不能自动视为现实事实或准确预测。

官网工作台公开介绍的功能包括：用自然语言可视化设计场景、生成 Agent 类型及交互工作流、运行 LLM Agent、实时查看 Agent/事件/系统指标，并导出模拟数据和行为轨迹。调研时页面显示需要登录，因此本报告不能验证该链接中特定项目的实际权限、数据内容或当前可用功能。

## 3. 本地部署条件

### 3.1 推荐：Docker 方式

项目 [Dockerfile](../Dockerfile) 会构建 Vue 前端，并在 Python 3.10 镜像中安装后端；容器内由 Nginx 提供静态页面、由 Supervisor 管理 Nginx 和 FastAPI 服务。公开安装说明要求 Docker，启动后访问 `http://localhost:8000`。

所需条件：

- Windows、macOS 或 Linux 主机；Windows/macOS 可使用 Docker Desktop。
- Docker 正常运行，且有网络拉取镜像或构建依赖。
- 本地配置目录，按说明挂载 `config/`。
- 一种可用的聊天模型服务和 embedding 服务，并配置对应服务地址/凭据。
- 存放镜像、依赖和仿真输出的磁盘空间。

仓库文档给出的硬件建议是 CPU 4 核以上、内存 8 GB 起、较大规模推荐 16 GB 以上、磁盘预留 10 GB；但同一要求文档也标注这些规模建议仍是占位说明。因此这些数字适合作为粗略参考，并非经验证的最低规格或运行保证。仿真 Agent 数、并发、模型调用和场景复杂度都会影响资源消耗。

示例命令（在仓库根目录执行）：

```bash
docker pull ptss/yulan-onesim:latest
docker run -d --name yulan-onesim -p 8000:80 -v ./config:/app/config ptss/yulan-onesim:latest
```

仓库提供的 [Makefile](../Makefile) 也可用于构建和启动镜像。只打算本机访问时，可将端口绑定到回环地址，例如 `-p 127.0.0.1:8000:80`，避免默认映射将服务暴露到其他网络接口。首次部署建议检查容器日志和 `/health` 状态。

### 3.2 从源码运行

适合修改引擎、场景或前端的用户：

- Python：仓库的 [setup.py](../setup.py) 限定为 `>=3.10,<3.11`，即 Python 3.10；README 的徽章虽然写着 3.10+，安装元数据的范围更窄，应优先遵循 `setup.py`。
- Node.js/npm：用于安装、开发和构建前端；Dockerfile 使用 Node 18 构建前端。
- 安装 Python 依赖及 `src/frontend/` 的 npm 依赖。
- 单独启动后端和前端开发服务器；README 示例地址分别为 `http://localhost:8000` 和 `http://localhost:5173`。
- 配置模型服务，并使前端的 API 地址与后端地址一致。

从源码安装方式和命令见 [README.md](../README.md) 与 [前端 README](../src/frontend/README.md)。对于只想运行而不改代码的用户，Docker 一般更省事。

### 3.3 模型服务及 GPU

模型配置位于 [config/model_config.json](../config/model_config.json)。当前示例包括 OpenAI 聊天模型、vLLM 聊天服务和 vLLM embedding 服务；配置文件中的 `sk-xxx` 是占位文本，不是可用密钥。仿真配置 [config/config.json](../config/config.json) 使用向量长期记忆和 embedding 配置，因此不能只准备聊天模型而忽略 embedding 依赖。

可选择：

- **云端模型：** 配置可访问的 API、有效凭据和可用网络。仿真服务本身不要求本地 GPU，但模型调用可能收费，且输入内容会发送至模型服务提供方；敏感数据应先评估服务条款和组织政策。
- **本地模型：** 配置并启动兼容的推理服务（例如 vLLM），再把 `base_url` 指向该服务。此时需要满足该模型及推理框架自身的操作系统、显存、内存和磁盘要求。仓库没有给出对所有模型通用的 GPU 最低配置，不能仅凭默认配置推断具体显存需求。

Docker 运行时若模型服务在宿主机上，容器中的 `localhost` 指容器本身，不是宿主机。需按操作系统和 Docker 网络方式将模型 URL 配置为容器可达的宿主机地址，或把模型服务加入同一 Docker 网络。

数据库和分布式组件不是入门运行的必需条件：默认配置中数据库与分布式开关为关闭。启用数据库功能时再准备 PostgreSQL；启用分布式运行时还需要配置 master/worker 地址、端口和节点。

## 4. 源码架构分析

### 4.1 CLI 与仿真运行链路

[src/main.py](../src/main.py) 是命令行仿真入口，支持配置文件、场景名、运行模式和 master/worker 参数。其核心工作流程是：

1. 解析命令行参数，调用 `onesim.init()` 加载模型和组件。
2. 载入仿真配置，按场景名从 `src/envs/` 动态加载 `场景.code.SimEnv`。
3. 从场景目录读取 `actions.json`、`events.json`，构建工作流图。
4. 创建 Agent 工厂与 Agent，建立环境和事件总线。
5. 运行环境及 Agent 任务，按配置记录数据。
6. 在场景的 `runs/` 目录下建立带时间戳的输出目录。

因此，场景不是仅靠前端静态模板构成：实际行为还依赖场景 Python 代码、动作/事件定义、画像及 schema。

### 4.2 核心仿真框架：`src/onesim/`

- `agent/`：通用 Agent 与代码、画像、指标、ODD、工作流等用途的 Agent。
- `planning/`：BDI、CoT、ToM 等规划策略。
- `memory/`：记忆项、管理器、短期/长期策略、列表/向量存储及评分指标。
- `models/`：统一模型接口、模型管理、负载均衡、响应解析及不同 provider 的适配。
- `events/`：事件类型、事件总线和调度器。
- `simulator/`：环境执行和 Agent 创建等运行时功能；`sim_env.py` 定义基础仿真环境。
- `profile/`：Agent 画像及其数据 schema。
- `relationship/`：Agent 关系管理。
- `monitor/`：监控指标和辅助功能。
- `distribution/`：master/worker、连接、Agent 分配和 gRPC 协议。
- `data/`：数据库持久化接口与实体管理；具体是否启用取决于配置。
- `config.py`：框架配置解析和组件管理；`utils/` 放置日志、工作流等通用工具。

### 4.3 场景库：`src/envs/`

每个场景子目录通常包含 `code/SimEnv.py`、Agent 代码、`actions.json`、`events.json`、场景信息、profile 数据和 schema。各场景具体文件并不完全一致；阅读场景时应以该场景的实际文件为准。它们由同一 `onesim` 引擎加载，而不是彼此独立的完整平台。

### 4.4 Web 层与外围工具

- `src/backend/`：FastAPI 应用和按 Agent、配置、场景、仿真、监控、反馈等功能划分的路由、请求模型及工具函数。
- `src/app.py`：后端服务启动入口，读取默认配置并使用 Uvicorn 启动。
- `src/frontend/`：Vue 3 + Vite 前端。包含视图、路由、Pinia 状态、API 数据服务、仿真面板及城市地图渲染资源。
- `src/researcher/`：AI 社会研究员相关的场景设计、分析、提纲、报告审阅和报告生成流程。
- `src/llm_tuning/`：微调数据处理和模型训练代码；它是可选扩展，不是运行普通仿真的必要条件。
- `config/`：仿真和模型服务配置。
- `scripts/`：单机、分布式和 vLLM 服务的脚本。
- `docker/`：Nginx、Supervisor 与容器启动配置。
- `docs/website/`：Docusaurus 文档网站源码；它是项目文档站，不是运行仿真服务本身。

## 5. 在线工作台与本地源码版的边界

| 项目 | 官网在线工作台 | 本地部署仓库 |
|---|---|---|
| 使用方式 | 登录网站后使用托管服务 | 自己启动 Docker 或前后端服务 |
| 运维 | 由服务方管理网站侧运行环境 | 用户管理依赖、模型、日志、备份和升级 |
| 定制能力 | 受网站功能及账号权限限制 | 可改公开源码、配置自有场景和服务 |
| 数据位置 | 需依据网站隐私政策及实际服务确认 | 应用数据和输出可留在自有主机；但接入云模型仍会外发请求 |
| 功能等同性 | 在线服务可能包含独立功能、账号和云端组件 | 仓库公开的本地 UI/API/引擎，不保证与在线服务同版本或同能力 |

公开代码包含本地 Web UI，并不等于官网完整工作台后端也在仓库中。特别是账号、云端项目管理、在线存储、市场及服务端配额等能力，应以在线平台实际说明为准。

## 6. 主要限制与风险

1. **模型费用和可用性：** 云模型可能按 token 或请求收费；模型服务不可达时，仿真也无法正常生成决策。
2. **硬件不确定：** CPU 仿真开销通常随 Agent 数和交互次数上升；本地模型的显存需求取决于模型规模、量化、上下文及并发。
3. **并非严格科学验证：** LLM Agent 输出会受到提示、模型版本和随机性的影响；应做重复实验、敏感性分析，并用外部数据验证。
4. **配置安全：** 不要把 API 密钥、真实数据库密码或敏感研究数据提交到公开仓库；首次运行建议只在本机或可信网络开放端口。
5. **默认示例不等于开箱即用：** 配置中有占位密钥和本地模型地址。部署前必须替换为可用的聊天及 embedding 配置。
6. **规模宣传不能作为单机保证：** 项目介绍中的大规模/分布式能力不表示普通电脑可以直接运行同等规模；需要实测并逐步增加 Agent 数。

## 7. 建议部署路径

1. 先确认目标：只是使用已有场景、开发自定义场景，还是必须离线运行模型。
2. 安装 Docker，克隆仓库，备份并编辑 `config/config.json` 与 `config/model_config.json`。
3. 先接入可用的聊天模型和 embedding 模型；若使用本地模型，先独立确认推理服务地址可从仿真容器访问。
4. 使用默认的劳动市场场景或小规模场景试跑，确认网页、API、模型调用和输出目录正常。
5. 再逐步提高 Agent 数、步数和并发；观察响应时间、模型费用、内存及输出数据。
6. 只有在确实需要时再启用 PostgreSQL、分布式节点或微调流程。

## 8. 调研依据

- 官方网站：[YuLan-OneSim](https://www.yulan-onesim.cn/)；工作台页面公开介绍及登录状态以调研时网站为准。
- 项目 README：[README.md](../README.md)
- 安装与硬件要求：[installation.md](website/docs/getting-started/installation.md)、[requirements.md](website/docs/getting-started/requirements.md)
- Web 界面说明：[web-interface.md](website/docs/getting-started/web-interface.md)
- 架构说明：[overview.md](website/docs/architecture/overview.md)
- 模型配置说明：[model-config.md](website/docs/configuration/model-config.md)
- 代码入口及配置：[src/main.py](../src/main.py)、[setup.py](../setup.py)、[Dockerfile](../Dockerfile)、[config/config.json](../config/config.json)、[config/model_config.json](../config/model_config.json)

