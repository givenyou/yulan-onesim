# 多边气候合作协议圆桌谈判：原始生成版本全流程

本文以 `git_a43ad03` 原始备份为源码依据，以 `20261111_012653` 为实际运行证据。当前工作区同名场景后来改用统一代表类，本文按备份中的四个角色类解释。末尾逐项展开动作配置、工作流事件边、生成画像、关系记录和环境初值。

## 1. 从研究描述到可执行场景

1. **确认仿真协议。** ODD 是 Overview、Design Concepts、Details 的首字母，分别表示概述、设计概念和实现细节。用户通过自然语言描述研究问题，平台的 `ODDAgent` 整理目标、角色、交互、决策、约束和结束条件，确认后写入 `scene_info.json`。本场景研究减排力度与资金承诺怎样影响多边气候合作协议，主持人是协调与裁定者，三位代表按国家授权提出立场。协议规定先分发草案，再并行审阅。其并行提案描述同时要求第二位代表考虑第一位代表、第三位代表综合前两位，实际处理函数通过等待同伴输入实现这种依赖。协议定义的两个结束状态是达成共识与记录僵局。
2. **确认智能体类型。** 智能体是拥有身份、状态、事件处理能力的仿真参与者。平台把文字描述提取成 `Chairperson`、`Delegate1`、`Delegate2`、`Delegate3` 四种类型，写入 `scene_info.json` 的 `agent_types`。其中 `portrait` 给出各类型默认启用数量，每类一位。类型是角色，画像是某一角色的具体人物，实例标识符（代码中写作 `id`）是运行时消息的投递地址。
3. **构造行为图。** `WorkflowAgent` 把动作写进 `actions.json`，把触发关系和载荷写进 `events.json`。行为图的节点是动作，边是发送者动作到接收者动作的事件。动作编号 `0` 表示环境启动，目标动作编号 `-1` 表示图中的结束位置。事件编号 `-1` 则是启动边，两套编号分别解释。`workflow.html` 展示图。`system_data_model.json` 汇总环境及各角色的数据字段、类型和默认值。字段类型用于生成与配置，运行时校验取决于实际处理代码。
4. **生成 Python 与监控计算。** `CodeAgent` 从行为图生成四个角色文件、`events.py` 和 `SimEnv.py`。`code_structure.json` 保存生成代码和动作元数据供平台展示或编辑，运行时调用 Python 类。指标生成在代码生成任务中运行，产物是 `scene_info.json` 的指标定义与 `code/metrics/metrics.py`。论文把自动构建归纳为四个阶段，本地架构文档另外单列指标阶段，这里按本地界面生成任务归并为五步。JSON 是 JavaScript Object Notation，这里用作存储配置、数据和结构化模型回答的文本格式。
5. **生成数据。** `profile/schema/Chairperson.json`、三个代表的同名模式文件和 `Relationship.json` 描述画像及关系字段。`profile/data/` 的四份人物文件各有五条，共二十条候选画像，另有 `Relationship.csv` 保存关系。CSV 是逗号分隔值文件，每条记录包含来源、目标和方向。`env_data.json` 保存初始草案与议程。数据模式中为空的字段，在实例数据里可以被填入具体值，原版将若干运行期间本应产生的字段也预填了。场景目录和代码目录里的 `__init__.py` 是 Python 包入口文件。

原草案要求 Article 3 在 2030 年前较 2005 年减排 45%；Article 7 规定发达方每年合计提供 1,000 亿美元，适应和减缓各占一半；Article 12 规定每两年审查履约并要求违规方提交纠正计划。第四项议程另谈发达方和发展中方的法律定义。画像原文中的 UNFCCC 指《联合国气候变化框架公约》，COP 指缔约方大会。画像中的姓名、国家、职务、外交风格和初始立场属于生成的仿真数据。

## 2. 平台如何启动并传递消息

后端根据场景的工作流找到起始类型和终止事件，实例化仿真人物并注册结束事件，再创建环境。场景类 `SimEnv` 继承平台环境基类 `BasicSimEnv`，只覆盖 `_create_start_event`。它取环境数据里的 `id`，缺省为 `ENV`，向指定的起始实例构造 `StartEvent`。本场景的起始类型为主席。原版环境没有自己实现重新起草或续轮协商的逻辑。

每个角色类继承 `GeneralAgent`，在构造时调用 `register_event`，建立“事件类型名称 → 处理函数”的对应关系。事件总线 `EventBus` 是负责消息投递的框架组件，它通过 `to_agent_id` 找实例，接收角色再按事件类型调用处理函数。事件中的 `from_agent_id` 表示发送实例。只有部分动作还检查载荷内的 `recipient_id`。处理函数返回的事件列表由框架继续派发，空列表表示本次处理不产生后续事件。角色通过画像保存自身状态，通过 `get_env_data` 读取环境值，通过事件交换本场谈判数据。关系管理器提供可见的关系上下文，关系文件本身不执行事件投递。


`generate_reaction` 是框架提供的决策调用入口。角色将任务要求和观察交给它，运行记录中的提示还包含画像、记忆和关系。大语言模型（Large Language Model）生成自然语言或结构化回答，角色再提取字段、更新画像并构造事件。生成的模型回答、程序真正派发的消息，以及接收者真正进入的动作，是三个可以分别核对的环节。

## 3. 十一个动作在原始 Python 中怎样执行

### 动作 1：主席设置议程并分发草案

`set_agenda_and_distribute_draft` 收到 `StartEvent` 后读取草案和议程，先把 `draft_distributed`、`agenda_set` 设为真。随后让模型生成三位代表的 `target_ids` 与开场 `message`。非列表地址被包成单元素列表，然后逐个创建 `DraftDistributedEvent`。事件只携带草案、议程和收件人，开场措辞没有写进该事件。代码没有校验名单是否恰好覆盖三个正确的代表实例，因此画像标志可以先于实际投递成功被置真。

### 动作 6、8、10：三位代表审阅草案并形成立场

- **动作 6，第一位代表。** `review_draft_and_form_position` 校验草案、议程和收件人。如果画像的 `clause_positions` 非空，立即结束。否则依据国家利益要求模型按议程形成立场，并输出国家利益背景。代码校验字典和文本类型，写入画像，以自己的真实实例地址发出 `PositionFormedEvent`。
- **动作 8，第二位代表。** 同样校验草案、议程、收件人和已有立场。调用模型后要求立场为字典，补齐缺少的议程项，并对不合法的立场值作默认处理。下一条 `PositionFormedEvent` 使用模型的 `target_ids`，字段缺省时使用自己。
- **动作 10，第三位代表。** 校验草案为非空文本、议程为非空列表。保存草案发送者为 `chairperson_id`。即使画像已经有立场，代码仍继续调用模型。保存模型返回的立场和利益背景，再发出 `PositionFormedEvent`；模型没有给出有效地址列表内容时，代码回退到自己。

### 动作 7、9、11：修正案、背书和让步

- **动作 7，第一位代表。** `propose_amendment_or_concession` 收到本人的 `PositionFormedEvent`。如果画像已有修正案，或缺少立场与国家利益背景，就退出。否则让模型给出目标条款、修正文字和理由，三项都通过检查才写入画像。代码尝试通过关系管理器查找第二位代表、第三位代表和主席，缺少地址时再向模型询问。找到的地址分别收到第一位代表的两条同伴修正案事件和一条给主席的正式提案，正式提案的背书标志为假。
- **动作 9，第二位代表。** 自己的立场事件和第一位代表的修正案事件都进入此函数，分别存入本方立场和同伴提案。两项非空时才调用模型，让它在背书第一位代表、提出反案或提供让步之间选择，并输出条款、文本、理由、背书标志和对象。代码保存提案后按模型给出的地址构造事件。包含 `Delegate3` 的地址生成发往第三位代表的专用事件，包含 `Chairperson` 或落入默认分支的地址生成正式提案事件。它把字符串原样用于投递，存在“角色名不是实例地址”以及“第三位代表的数字地址被配成错误事件类型”两种风险。画像里的预置立场也可能提前满足本方输入条件。
- **动作 11，第三位代表。** 自己的立场、第一位和第二位代表的修正案都可触发处理。处理函数按事件种类写入相应画像字段，只有三项均非空才综合评估红线、背书或折中。调用模型前先把 `amendment_proposed` 设为真，随后保存提案字段，向先前记录的主席地址发送 `AmendmentProposedEvent`。地址缺失会退出；模型未返回有效结果时，已写入的去重标志也会阻断后续尝试。

### 动作 2、3：主席收集并裁定

第一位代表调用的 `get_agent_ids_by_type` 在当前工作区的框架源码中未找到定义。若运行框架也没有这个方法，调用会被该动作的异常处理捕获，然后进入额外的模型询址。第二位代表对缺失或非法立场统一填入 `Conditional Support`，即条件支持。其它两个合法文本是 `Support`（支持）和 `Oppose`（反对）。

- **动作 2，`collect_positions_and_divergences`。** 每收到一条 `AmendmentProposedEvent`，按载荷的 `delegate_id` 在 `received_amendments` 中保存条款、提案、理由和背书，重复身份直接退出。字典未收满三个不同身份时返回空列表。收齐后，主席让模型从提案理由推断三方逐条立场和分歧。它保存模型给出的 `all_positions`、`identified_divergences`，以及实际收集到的 `all_amendments`，并向模型返回的地址发送 `PositionsCollectedEvent`，缺省地址为自己。实际收集以不同身份数量为门槛；代码没有逐一验证是否为本桌三位合法代表。事件也没有携带代表独立确认的完整立场表。
- **动作 3，`determine_outcome`。** 如果已裁定、事件类型不对、立场不是非空字典或分歧不是列表，则退出。主席从提交行为推导 `concession_willingness`，有修正案的身份记为真，其他已知身份记为假。随后让模型判断共识或僵局，读取已对齐条款、未决条款、接受立场与让步状态。代码先写入裁定状态和 `outcome_determined`，然后仅在状态精确等于 `Consensus` 或 `Impasse` 时发出对应事件。默认裁定值为 `Impasse`，目标地址缺省为自己。提交反案也会被视为有让步意愿，且此处没有对同一版协议逐条征求三方接受。

### 动作 4、5：生成最终记录并通知环境

- **动作 4，`issue_agreed_text`。** 验证 `ConsensusReachedEvent` 和非空已对齐条款，向模型请求综合文本。写入 `final_agreed_text` 和共识状态，强制把 `AgreementFinalizedEvent` 发给 `ENV`。
- **动作 5，`declare_impasse`。** 已记录僵局时退出。验证 `ImpasseDeclaredEvent` 和非空未决条款，读取主席汇总立场以及事件中的让步状态，要求模型整理僵局记录。写入 `impasse_record` 和僵局状态，按模型给出的地址发送 `ImpasseRecordedEvent`，缺省地址为 `ENV`。

这两种末端事件由后端依据工作流注册给环境。场景的完成消息和框架广播的 `EndEvent` 属于不同层级，后者由平台用于终止。图内没有从裁定返回分发或提案的边，所以平台运行步数增加，并不会自动实现协议中的实质性多轮协商。

## 4. 监控与这一次的实际轨迹

`Negotiation_Outcome_Distribution` 读取主席的 `outcome_status`，去掉空值、统计并归一化，缺数据时返回未知。`Clause_Alignment_vs_Divergence` 计算主席的 `aligned_clauses` 和 `divergent_clauses` 的数量。`Delegate_Concession_Willingness` 期望从主席收集到“代表标识符 → 让步意愿”的字典，布尔值变成 0 或 1，缺失或类型不合时返回空图。三个计算函数通过 `get_metric_function` 按名称获取。仪表盘快照与模型决策快照可以在同一运行步内多次保存，因此不能把每个快照文件当成独立实验。

运行目录是 `src/envs/multilateral_climate_agreement_roundtable_negotiation/runs/20261111_012653`。最终画像显示主席 1，三位代表分别是 6、11、16。最终决策文件只有三条记录。

1. 平台步骤 1，主席执行动作 1，模型给出的地址是 6、11、1。第三个地址是主席本人。累计模型调用 1 次，计数事件 3 个，累计 1,723 个词元。词元是模型计费与统计时对输入输出文本切分后的单位。
2. 平台步骤 2，主席再次执行动作 1，地址仍是 6、11、1。累计模型调用 2 次，计数事件 6 个，累计 3,450 个词元。
3. 平台步骤 3，主席第三次执行动作 1，地址是 6、11、12。12 属于候选画像库中的另一位第二类代表，在本次最终运行画像中没有启用。累计模型调用 3 次，计数事件 9 个，累计 5,174 个词元。

三次输出都漏掉代表 16。画像 6 和 11 一开始已有立场，即使分发事件到达，其审阅函数也会因已有立场直接返回。决策记录中没有三位代表调用模型、提交修正案或主席作出裁定的证据。最终的 `in_progress` 是谈判进行中状态。图中的对齐和分歧各一条来自主席画像里的 `Preamble` 和字符串 `None`，让步输入则是初始列表，故图为空。可在运行快照中核对模型输出、画像和计数；工作区中未找到该次运行的逐事件日志，无法逐条确认实际投递结果及每一步具体如何结束。

## 5. 来源与附录说明

- 原始场景位于 `.scenario_backups/multilateral_climate_agreement_roundtable_negotiation_git_a43ad03/src/envs/multilateral_climate_agreement_roundtable_negotiation/`。
- 平台入口在 `src/backend/routers/odd.py`、`pipeline.py` 和 `simulation.py`，环境与事件总线分别在 `src/onesim/simulator/sim_env.py` 与 `src/onesim/events/eventbus.py`。
- 运行依据为 `datasets/decisions_20261111_013008.json` 和 `metrics_plots/step_3/` 中的最终统计、画像与场景指标。
- 动作附录中的 `OR` 表示任一已配置的输入事件可以触发动作，`AND` 表示动作依赖多项输入。触发动作后仍须满足函数内的条件。字段来源 `env` 是环境，`agent` 是角色画像，`event` 是事件载荷。配置类型 `str`、`bool`、`list`、`dict` 分别是字符串、布尔值、列表和字典。附录保留生成原文及代码字段名以便逐项搜索。


## 附录一：全部动作的配置字段

### 动作 1：`set_agenda_and_distribute_draft`

- 描述。Initiates the negotiation by setting the formal agenda, defining the scope of discussion (emission reduction and financial commitments), and distributing the draft multilateral climate cooperation agreement to all delegates for review.
- 触发类型为 `OR`。配置条件为 无附加条件。
- 输入。`draft_content`（`str`，`env`）The full text of the draft multilateral climate cooperation agreement to be distributed.；`agenda_items`（`list[str]`，`env`）The list of specific agenda items or clauses to be discussed, such as 'Emission Reduction Intensity' and 'Financial Commitments'.
- 声明更新。`draft_distributed`（`bool`，`agent`）A flag indicating whether the draft has been successfully distributed to all delegates.；`agenda_set`（`bool`，`agent`）A flag indicating whether the agenda has been formally set and announced.

### 动作 2：`collect_positions_and_divergences`

- 描述。Aggregates the positions, amendments, and concessions proposed by all three delegates. Identifies areas of agreement and divergence across the core clauses of the agreement.
- 触发类型为 `AND`。配置条件为 Requires receipt of position and amendment proposals from all three delegates。
- 输入。`delegate1_amendment`（`dict`，`event`）The amendment or concession proposal from Delegate1, including target clauses, text, and rationale.；`delegate2_amendment`（`dict`，`event`）The amendment or concession proposal from Delegate2, including target clauses, text, and rationale.；`delegate3_amendment`（`dict`，`event`）The amendment or concession proposal from Delegate3, including target clauses, text, and rationale.
- 声明更新。`all_positions`（`dict[str, dict[str, str]]`，`agent`）A mapping of delegate IDs to their specific clause positions (Support, Conditional Support, Oppose).；`all_amendments`（`list[dict]`，`agent`）A consolidated list of all amendment proposals received from the delegates.；`identified_divergences`（`list[str]`，`agent`）A list of clause identifiers where significant divergences in position were identified among the delegates.

### 动作 3：`determine_outcome`

- 描述。Analyzes the aggregated positions and identified divergences to determine if a consensus is possible. Applies the coordination strategy to judge if core clause positions align or if an impasse is inevitable.
- 触发类型为 `OR`。配置条件为 Requires aggregated positions and divergence analysis。
- 输入。`all_positions`（`dict[str, dict[str, str]]`，`agent`）The aggregated mapping of delegate positions on each clause.；`identified_divergences`（`list[str]`，`agent`）The list of clauses with significant divergences.；`concession_willingness`（`dict[str, bool]`，`agent`）A mapping of delegate IDs to their willingness to make further concessions, derived from their proposals.
- 声明更新。`outcome_status`（`str`，`agent`）The determined outcome status: 'Consensus' or 'Impasse'.；`aligned_clauses`（`list[str]`，`agent`）If consensus, the list of core clauses where positions aligned.；`divergent_clauses`（`list[str]`，`agent`）If impasse, the list of core clauses where divergences remain unresolved.

### 动作 4：`issue_agreed_text`

- 描述。Generates and issues the final agreed text of the multilateral climate cooperation agreement, integrating the final accepted positions and modifications from the consensus.
- 触发类型为 `OR`。配置条件为 Consensus reached on core clauses。
- 输入。`aligned_clauses`（`list[str]`，`agent`）The list of core clauses where positions aligned to form consensus.；`final_accepted_positions`（`dict[str, str]`，`agent`）The final agreed-upon stance for each core clause.；`draft_content`（`str`，`env`）The original draft text to be modified with the agreed positions.
- 声明更新。`final_agreed_text`（`str`，`agent`）The complete text of the final agreed multilateral climate cooperation agreement.；`simulation_status`（`str`，`agent`）The terminal state of the simulation, set to 'Consensus'.

### 动作 5：`declare_impasse`

- 描述。Declares an impasse in the negotiation and records the final result, including the position distribution for each clause, as no further concessions are willing.
- 触发类型为 `OR`。配置条件为 Impasse declared due to unresolvable divergences。
- 输入。`divergent_clauses`（`list[str]`，`agent`）The list of core clauses where divergences remain unresolved.；`concession_willingness_status`（`dict[str, bool]`，`agent`）A mapping of delegate IDs to whether they expressed willingness to make further concessions.；`all_positions`（`dict[str, dict[str, str]]`，`agent`）The final positions of all delegates on each clause.
- 声明更新。`impasse_record`（`str`，`agent`）A formal record detailing the impasse, including the final position distribution for each clause.；`simulation_status`（`str`，`agent`）The terminal state of the simulation, set to 'Impasse'.

### 动作 6：`review_draft_and_form_position`

- 描述。Reviews the distributed draft agreement and forms an initial position on each clause based on national interests in emission reduction intensity and financial commitments.
- 触发类型为 `OR`。配置条件为 Requires draft agreement and agenda。
- 输入。`draft_content`（`str`，`event`）The full text of the draft multilateral climate cooperation agreement.；`agenda_items`（`list[str]`，`event`）The list of specific agenda items or clauses to be discussed.；`national_interests`（`str`，`agent`）The delegate's national interests regarding emission reduction and funding.
- 声明更新。`clause_positions`（`dict[str, str]`，`agent`）A mapping of clause identifiers to the delegate's stance ('Support', 'Conditional Support', 'Oppose').；`national_interests_context`（`str`，`agent`）A brief summary of the national interests influencing this position.

### 动作 7：`propose_amendment_or_concession`

- 描述。Proposes specific amendments or concessions on the most concerned clauses based on the formed position, providing diplomatic or legal justification.
- 触发类型为 `OR`。配置条件为 Requires formed position on draft clauses。
- 输入。`clause_positions`（`dict[str, str]`，`agent`）The delegate's stance on each clause.；`national_interests_context`（`str`，`agent`）The context of national interests influencing the proposal.
- 声明更新。`target_clauses`（`list[str]`，`agent`）The list of clause identifiers that the amendment targets.；`amendment_text`（`str`，`agent`）The specific text of the proposed amendment or concession.；`rationale`（`str`，`agent`）The diplomatic or legal justification for the proposed amendment.

### 动作 8：`review_draft_and_form_position`

- 描述。Reviews the draft agreement and considers Delegate1's potential influence, forming a position based on national interests and the impact of Delegate1's suggestions.
- 触发类型为 `OR`。配置条件为 Requires draft agreement and agenda。
- 输入。`draft_content`（`str`，`event`）The full text of the draft multilateral climate cooperation agreement.；`agenda_items`（`list[str]`，`event`）The list of specific agenda items or clauses to be discussed.；`national_interests`（`str`，`agent`）The delegate's national interests regarding emission reduction and funding.
- 声明更新。`clause_positions`（`dict[str, str]`，`agent`）A mapping of clause identifiers to the delegate's stance ('Support', 'Conditional Support', 'Oppose').；`national_interests_context`（`str`，`agent`）A brief summary of the national interests influencing this position.

### 动作 9：`propose_amendment_or_concession`

- 描述。Decides to endorse Delegate1's suggestion or propose an alternative amendment, expressing position on other clauses based on national interests.
- 触发类型为 `OR`。配置条件为 Requires formed position and evaluation of Delegate1's stance。
- 输入。`clause_positions`（`dict[str, str]`，`agent`）The delegate's stance on each clause.；`delegate1_amendment`（`dict`，`event`）The amendment or concession proposal from Delegate1 to evaluate for endorsement.；`national_interests_context`（`str`，`agent`）The context of national interests influencing the proposal.
- 声明更新。`target_clauses`（`list[str]`，`agent`）The list of clause identifiers that the amendment targets.；`amendment_text`（`str`，`agent`）The specific text of the proposed amendment or concession.；`rationale`（`str`，`agent`）The diplomatic or legal justification for the proposed amendment.；`is_endorsement`（`bool`，`agent`）True if this proposal is an endorsement of Delegate1's proposal, False if it is a new/alternative proposal.；`endorsed_delegate_id`（`str`，`agent`）If is_endorsement is true, the ID of the delegate whose proposal is being endorsed.

### 动作 10：`review_draft_and_form_position`

- 描述。Reviews the draft agreement and synthesizes inputs from Delegate1 and Delegate2, judging if movements touch national bottom lines.
- 触发类型为 `OR`。配置条件为 Requires draft agreement and agenda。
- 输入。`draft_content`（`str`，`event`）The full text of the draft multilateral climate cooperation agreement.；`agenda_items`（`list[str]`，`event`）The list of specific agenda items or clauses to be discussed.；`national_interests`（`str`，`agent`）The delegate's national interests regarding emission reduction and funding.
- 声明更新。`clause_positions`（`dict[str, str]`，`agent`）A mapping of clause identifiers to the delegate's stance ('Support', 'Conditional Support', 'Oppose').；`national_interests_context`（`str`，`agent`）A brief summary of the national interests influencing this position.

### 动作 11：`propose_amendment_or_concession`

- 描述。Decides to propose a new amendment or make a concession on key clauses to push the negotiation forward, based on synthesized inputs from previous delegates.
- 触发类型为 `OR`。配置条件为 Requires formed position and synthesis of previous delegates' inputs。
- 输入。`clause_positions`（`dict[str, str]`，`agent`）The delegate's stance on each clause.；`delegate1_amendment`（`dict`，`event`）The amendment or concession proposal from Delegate1.；`delegate2_amendment`（`dict`，`event`）The amendment or concession proposal from Delegate2.；`national_interests_context`（`str`，`agent`）The context of national interests influencing the proposal.
- 声明更新。`target_clauses`（`list[str]`，`agent`）The list of clause identifiers that the amendment targets.；`amendment_text`（`str`，`agent`）The specific text of the proposed amendment or concession.；`rationale`（`str`，`agent`）The diplomatic or legal justification for the proposed amendment.；`is_endorsement`（`bool`，`agent`）True if this proposal is an endorsement of a previous delegate's proposal, False if it is a new/alternative proposal.；`endorsed_delegate_id`（`str`，`agent`）If is_endorsement is true, the ID of the delegate whose proposal is being endorsed.

## 附录二：全部工作流事件边及载荷

图中共 18 条边，Python 共 12 种事件类。每条事件都有发送和接收实例地址，下面只展开场景专用载荷。

- **事件边 -1**。动作 0（`EnvAgent`）→ 动作 1（`Chairperson`）。事件类为 `StartEvent`。
- **事件边 1**。动作 1（`Chairperson`）→ 动作 6（`Delegate1`）。事件类为 `DraftDistributedEvent`。
  - `draft_content`，类型 `str`，图配置默认值 `""`。The full text of the draft multilateral climate cooperation agreement.
  - `agenda_items`，类型 `list[str]`，图配置默认值 `[]`。List of specific agenda items or clauses to be discussed (e.g., 'Emission Reduction Intensity', 'Financial Commitments').
  - `recipient_id`，类型 `str`，图配置默认值 `""`。The unique identifier of the delegate receiving the draft (Delegate1, Delegate2, or Delegate3).
- **事件边 2**。动作 1（`Chairperson`）→ 动作 8（`Delegate2`）。事件类为 `DraftDistributedEvent`。
  - `draft_content`，类型 `str`，图配置默认值 `""`。The full text of the draft multilateral climate cooperation agreement.
  - `agenda_items`，类型 `list[str]`，图配置默认值 `[]`。List of specific agenda items or clauses to be discussed (e.g., 'Emission Reduction Intensity', 'Financial Commitments').
  - `recipient_id`，类型 `str`，图配置默认值 `""`。The unique identifier of the delegate receiving the draft (Delegate1, Delegate2, or Delegate3).
- **事件边 3**。动作 1（`Chairperson`）→ 动作 10（`Delegate3`）。事件类为 `DraftDistributedEvent`。
  - `draft_content`，类型 `str`，图配置默认值 `""`。The full text of the draft multilateral climate cooperation agreement.
  - `agenda_items`，类型 `list[str]`，图配置默认值 `[]`。List of specific agenda items or clauses to be discussed (e.g., 'Emission Reduction Intensity', 'Financial Commitments').
  - `recipient_id`，类型 `str`，图配置默认值 `""`。The unique identifier of the delegate receiving the draft (Delegate1, Delegate2, or Delegate3).
- **事件边 4**。动作 2（`Chairperson`）→ 动作 3（`Chairperson`）。事件类为 `PositionsCollectedEvent`。
  - `all_positions`，类型 `dict[str, dict[str, str]]`，图配置默认值 `{}`。Aggregated mapping of delegate_id to their clause_positions.
  - `all_amendments`，类型 `list[dict]`，图配置默认值 `[]`。List of all amendment proposals received from delegates.
  - `identified_divergences`，类型 `list[str]`，图配置默认值 `[]`。List of clause identifiers where significant divergences in position were identified.
- **事件边 5**。动作 3（`Chairperson`）→ 动作 4（`Chairperson`）。事件类为 `ConsensusReachedEvent`。
  - `aligned_clauses`，类型 `list[str]`，图配置默认值 `[]`。List of core clause identifiers where positions aligned to form consensus.
  - `final_accepted_positions`，类型 `dict[str, str]`，图配置默认值 `{}`。The final agreed-upon stance for each core clause.
- **事件边 6**。动作 3（`Chairperson`）→ 动作 5（`Chairperson`）。事件类为 `ImpasseDeclaredEvent`。
  - `divergent_clauses`，类型 `list[str]`，图配置默认值 `[]`。List of core clause identifiers where divergences remain unresolved.
  - `concession_willingness_status`，类型 `dict[str, bool]`，图配置默认值 `{}`。Mapping of delegate_id to whether they expressed willingness to make further concessions.
- **事件边 7**。动作 4（`Chairperson`）→ 动作 -1（`EnvAgent`）。事件类为 `AgreementFinalizedEvent`。
  - `final_agreed_text`，类型 `str`，图配置默认值 `""`。The complete text of the final agreed multilateral climate cooperation agreement.
  - `simulation_status`，类型 `str`，图配置默认值 `"Consensus"`。Indicates the terminal state of the simulation.
- **事件边 8**。动作 5（`Chairperson`）→ 动作 -1（`EnvAgent`）。事件类为 `ImpasseRecordedEvent`。
  - `impasse_record`，类型 `str`，图配置默认值 `""`。A formal record detailing the impasse, including final position distribution for each clause.
  - `simulation_status`，类型 `str`，图配置默认值 `"Impasse"`。Indicates the terminal state of the simulation.
- **事件边 9**。动作 6（`Delegate1`）→ 动作 7（`Delegate1`）。事件类为 `PositionFormedEvent`。
  - `delegate_id`，类型 `str`，图配置默认值 `""`。The unique identifier of the delegate forming the position.
  - `clause_positions`，类型 `dict[str, str]`，图配置默认值 `{}`。Mapping of clause identifiers to the delegate's stance ('Support', 'Conditional Support', 'Oppose').
  - `national_interests_context`，类型 `str`，图配置默认值 `""`。Brief summary of the national interests (emission reduction/funding) influencing this position.
- **事件边 10**。动作 7（`Delegate1`）→ 动作 9（`Delegate2`）。事件类为 `Delegate1AmendmentToDelegate2Event`。
  - `delegate1_amendment`，类型 `dict`，图配置默认值 `{}`。The amendment or concession proposal from Delegate1, including target clauses, text, and rationale.
- **事件边 11**。动作 8（`Delegate2`）→ 动作 9（`Delegate2`）。事件类为 `PositionFormedEvent`。
  - `delegate_id`，类型 `str`，图配置默认值 `""`。The unique identifier of the delegate forming the position.
  - `clause_positions`，类型 `dict[str, str]`，图配置默认值 `{}`。Mapping of clause identifiers to the delegate's stance ('Support', 'Conditional Support', 'Oppose').
  - `national_interests_context`，类型 `str`，图配置默认值 `""`。Brief summary of the national interests (emission reduction/funding) influencing this position.
- **事件边 12**。动作 9（`Delegate2`）→ 动作 11（`Delegate3`）。事件类为 `Delegate2AmendmentToDelegate3Event`。
  - `delegate2_amendment`，类型 `dict`，图配置默认值 `{}`。The amendment or concession proposal from Delegate2, including target clauses, text, and rationale.
- **事件边 13**。动作 10（`Delegate3`）→ 动作 11（`Delegate3`）。事件类为 `PositionFormedEvent`。
  - `delegate_id`，类型 `str`，图配置默认值 `""`。The unique identifier of the delegate forming the position.
  - `clause_positions`，类型 `dict[str, str]`，图配置默认值 `{}`。Mapping of clause identifiers to the delegate's stance ('Support', 'Conditional Support', 'Oppose').
  - `national_interests_context`，类型 `str`，图配置默认值 `""`。Brief summary of the national interests (emission reduction/funding) influencing this position.
- **事件边 14**。动作 7（`Delegate1`）→ 动作 2（`Chairperson`）。事件类为 `AmendmentProposedEvent`。
  - `delegate_id`，类型 `str`，图配置默认值 `""`。The unique identifier of the delegate proposing the amendment.
  - `target_clauses`，类型 `list[str]`，图配置默认值 `[]`。List of clause identifiers that the amendment targets.
  - `amendment_text`，类型 `str`，图配置默认值 `""`。The specific text of the proposed amendment or concession.
  - `rationale`，类型 `str`，图配置默认值 `""`。Diplomatic or legal justification for the proposed amendment.
  - `is_endorsement`，类型 `bool`，图配置默认值 `false`。True if this proposal is an endorsement of a previous delegate's proposal, False if it is a new/alternative proposal.
  - `endorsed_delegate_id`，类型 `str`，图配置默认值 `""`。If is_endorsement is true, the ID of the delegate whose proposal is being endorsed.
- **事件边 15**。动作 9（`Delegate2`）→ 动作 2（`Chairperson`）。事件类为 `AmendmentProposedEvent`。
  - `delegate_id`，类型 `str`，图配置默认值 `""`。The unique identifier of the delegate proposing the amendment.
  - `target_clauses`，类型 `list[str]`，图配置默认值 `[]`。List of clause identifiers that the amendment targets.
  - `amendment_text`，类型 `str`，图配置默认值 `""`。The specific text of the proposed amendment or concession.
  - `rationale`，类型 `str`，图配置默认值 `""`。Diplomatic or legal justification for the proposed amendment.
  - `is_endorsement`，类型 `bool`，图配置默认值 `false`。True if this proposal is an endorsement of a previous delegate's proposal, False if it is a new/alternative proposal.
  - `endorsed_delegate_id`，类型 `str`，图配置默认值 `""`。If is_endorsement is true, the ID of the delegate whose proposal is being endorsed.
- **事件边 16**。动作 11（`Delegate3`）→ 动作 2（`Chairperson`）。事件类为 `AmendmentProposedEvent`。
  - `delegate_id`，类型 `str`，图配置默认值 `""`。The unique identifier of the delegate proposing the amendment.
  - `target_clauses`，类型 `list[str]`，图配置默认值 `[]`。List of clause identifiers that the amendment targets.
  - `amendment_text`，类型 `str`，图配置默认值 `""`。The specific text of the proposed amendment or concession.
  - `rationale`，类型 `str`，图配置默认值 `""`。Diplomatic or legal justification for the proposed amendment.
  - `is_endorsement`，类型 `bool`，图配置默认值 `false`。True if this proposal is an endorsement of a previous delegate's proposal, False if it is a new/alternative proposal.
  - `endorsed_delegate_id`，类型 `str`，图配置默认值 `""`。If is_endorsement is true, the ID of the delegate whose proposal is being endorsed.
- **事件边 17**。动作 7（`Delegate1`）→ 动作 11（`Delegate3`）。事件类为 `Delegate1AmendmentToDelegate3Event`。
  - `delegate1_amendment`，类型 `dict`，图配置默认值 `{}`。The amendment or concession proposal from Delegate1, including target clauses, text, and rationale.

## 附录三：全部候选画像原值

以下每条画像都来自生成备份。字段按文件原样列出，包含姓名、角色、国家利益、外交方式、预填的立场与修正案等。没有独立国家字段的画像保留原样。

### Chairperson

#### 画像 1：Elena Rodriguez，本次运行画像

```json
{
  "name": "Elena Rodriguez",
  "role_title": "Ambassador and Chairperson of the UNFCCC COP",
  "diplomatic_style": "Neutral and procedurally fair, emphasizing balanced dialogue and inclusive participation.",
  "agenda_set": "pending",
  "draft_distributed": "pending",
  "all_positions": [
    {
      "delegate": "Delegate1",
      "clause": "Emission Reduction Intensity",
      "position": "awaiting_input"
    }
  ],
  "all_amendments": [
    {
      "delegate": "Delegate1",
      "clause": "Financial Commitments",
      "proposal": "awaiting_input"
    }
  ],
  "identified_divergences": [
    "No divergences identified yet"
  ],
  "concession_willingness": [
    {
      "delegate": "Delegate1",
      "willingness": "unknown"
    }
  ],
  "aligned_clauses": [
    "Preamble"
  ],
  "divergent_clauses": [
    "None"
  ],
  "final_accepted_positions": [
    {
      "clause": "General Principles",
      "position": "pending"
    }
  ],
  "outcome_status": "in_progress",
  "final_agreed_text": "Draft text under negotiation...",
  "impasse_record": "No impasse recorded yet.",
  "simulation_status": "initializing",
  "concession_willingness_status": [
    {
      "delegate": "Delegate1",
      "status": "unknown"
    }
  ],
  "agent_type": "Chairperson",
  "coordination_strategy": "Facilitates structured side meetings and uses iterative drafting to bridge gaps between developed and developing nations.",
  "id": "1"
}
```

#### 画像 2：James O'Connor

```json
{
  "name": "James O'Connor",
  "role_title": "Senior Diplomat and Chair of the Climate Negotiations",
  "diplomatic_style": "Measured and impartial, focusing on clear procedural guidelines and transparent decision-making.",
  "agenda_set": "pending",
  "draft_distributed": "pending",
  "all_positions": [
    {
      "delegate": "Delegate1",
      "clause": "Emission Reduction Intensity",
      "position": "awaiting_input"
    }
  ],
  "all_amendments": [
    {
      "delegate": "Delegate1",
      "clause": "Financial Commitments",
      "proposal": "awaiting_input"
    }
  ],
  "identified_divergences": [
    "No divergences identified yet"
  ],
  "concession_willingness": [
    {
      "delegate": "Delegate1",
      "willingness": "unknown"
    }
  ],
  "aligned_clauses": [
    "Preamble"
  ],
  "divergent_clauses": [
    "None"
  ],
  "final_accepted_positions": [
    {
      "clause": "General Principles",
      "position": "pending"
    }
  ],
  "outcome_status": "in_progress",
  "final_agreed_text": "Draft text under negotiation...",
  "impasse_record": "No impasse recorded yet.",
  "simulation_status": "initializing",
  "concession_willingness_status": [
    {
      "delegate": "Delegate1",
      "status": "unknown"
    }
  ],
  "agent_type": "Chairperson",
  "coordination_strategy": "Employs consensus-building through small working groups and targeted mediation to resolve key sticking points.",
  "id": "2"
}
```

#### 画像 3：Aisha Patel

```json
{
  "name": "Aisha Patel",
  "role_title": "Ambassador and Presiding Officer of the Multilateral Climate Forum",
  "diplomatic_style": "Balanced and respectful, prioritizing equitable representation and open communication channels.",
  "agenda_set": "pending",
  "draft_distributed": "pending",
  "all_positions": [
    {
      "delegate": "Delegate1",
      "clause": "Emission Reduction Intensity",
      "position": "awaiting_input"
    }
  ],
  "all_amendments": [
    {
      "delegate": "Delegate1",
      "clause": "Financial Commitments",
      "proposal": "awaiting_input"
    }
  ],
  "identified_divergences": [
    "No divergences identified yet"
  ],
  "concession_willingness": [
    {
      "delegate": "Delegate1",
      "willingness": "unknown"
    }
  ],
  "aligned_clauses": [
    "Preamble"
  ],
  "divergent_clauses": [
    "None"
  ],
  "final_accepted_positions": [
    {
      "clause": "General Principles",
      "position": "pending"
    }
  ],
  "outcome_status": "in_progress",
  "final_agreed_text": "Draft text under negotiation...",
  "impasse_record": "No impasse recorded yet.",
  "simulation_status": "initializing",
  "concession_willingness_status": [
    {
      "delegate": "Delegate1",
      "status": "unknown"
    }
  ],
  "agent_type": "Chairperson",
  "coordination_strategy": "Utilizes phased negotiation tracks and regular progress reviews to align diverse national interests.",
  "id": "3"
}
```

#### 画像 4：Lars Nielsen

```json
{
  "name": "Lars Nielsen",
  "role_title": "Diplomatic Chairperson of the Global Climate Accord",
  "diplomatic_style": "Objective and process-oriented, ensuring all voices are heard while maintaining strict adherence to procedural rules.",
  "agenda_set": "pending",
  "draft_distributed": "pending",
  "all_positions": [
    {
      "delegate": "Delegate1",
      "clause": "Emission Reduction Intensity",
      "position": "awaiting_input"
    }
  ],
  "all_amendments": [
    {
      "delegate": "Delegate1",
      "clause": "Financial Commitments",
      "proposal": "awaiting_input"
    }
  ],
  "identified_divergences": [
    "No divergences identified yet"
  ],
  "concession_willingness": [
    {
      "delegate": "Delegate1",
      "willingness": "unknown"
    }
  ],
  "aligned_clauses": [
    "Preamble"
  ],
  "divergent_clauses": [
    "None"
  ],
  "final_accepted_positions": [
    {
      "clause": "General Principles",
      "position": "pending"
    }
  ],
  "outcome_status": "in_progress",
  "final_agreed_text": "Draft text under negotiation...",
  "impasse_record": "No impasse recorded yet.",
  "simulation_status": "initializing",
  "concession_willingness_status": [
    {
      "delegate": "Delegate1",
      "status": "unknown"
    }
  ],
  "agent_type": "Chairperson",
  "coordination_strategy": "Leverages technical expert panels and joint statements to build trust and advance shared commitments.",
  "id": "4"
}
```

#### 画像 5：Maria Santos

```json
{
  "name": "Maria Santos",
  "role_title": "Ambassador and Lead Negotiator for International Climate Cooperation",
  "diplomatic_style": "Fair and inclusive, with a strong emphasis on mutual respect and collaborative problem-solving.",
  "agenda_set": "pending",
  "draft_distributed": "pending",
  "all_positions": [
    {
      "delegate": "Delegate1",
      "clause": "Emission Reduction Intensity",
      "position": "awaiting_input"
    }
  ],
  "all_amendments": [
    {
      "delegate": "Delegate1",
      "clause": "Financial Commitments",
      "proposal": "awaiting_input"
    }
  ],
  "identified_divergences": [
    "No divergences identified yet"
  ],
  "concession_willingness": [
    {
      "delegate": "Delegate1",
      "willingness": "unknown"
    }
  ],
  "aligned_clauses": [
    "Preamble"
  ],
  "divergent_clauses": [
    "None"
  ],
  "final_accepted_positions": [
    {
      "clause": "General Principles",
      "position": "pending"
    }
  ],
  "outcome_status": "in_progress",
  "final_agreed_text": "Draft text under negotiation...",
  "impasse_record": "No impasse recorded yet.",
  "simulation_status": "initializing",
  "concession_willingness_status": [
    {
      "delegate": "Delegate1",
      "status": "unknown"
    }
  ],
  "agent_type": "Chairperson",
  "coordination_strategy": "Implements a dual-track approach combining high-level political dialogue with detailed technical negotiations to achieve consensus.",
  "id": "5"
}
```

### Delegate1

#### 画像 6：Ambassador Elena Rodriguez，本次运行画像

```json
{
  "name": "Ambassador Elena Rodriguez",
  "country": "Spain",
  "diplomatic_style": "Flexible and conciliatory",
  "clause_positions": [
    {
      "clause_id": "Article 3.1",
      "position": "conditional_support",
      "comment": "Acceptable if timeline is extended."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 3.1: Extend the compliance deadline from 2030 to 2035 for industrial sectors.",
  "rationale": "The current timeline is too aggressive for our industrial transition capabilities. We propose a phased approach to ensure economic stability while meeting climate goals.",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate1",
  "national_interests": "Spain aims to achieve a 55% reduction in greenhouse gas emissions by 2030 compared to 1990 levels, with a strong emphasis on renewable energy integration and sustainable tourism. Financially, Spain seeks substantial EU funding and international climate finance to support its transition, particularly in regions dependent on fossil fuels.",
  "national_interests_context": "Spain's strategy is driven by its vulnerability to climate change impacts, such as droughts and wildfires, which threaten its agricultural and tourism sectors. Politically, there is a strong public demand for aggressive climate action, and economically, the country is leveraging the EU's Green Deal to attract investment in clean technologies and create green jobs.",
  "emission_reduction_priority": 7,
  "financial_commitment_priority": 1,
  "target_clauses": [
    "Article 3.1",
    "Article 5.2"
  ],
  "concession_willingness": 0.6,
  "id": "6"
}
```

#### 画像 7：Minister Kenji Tanaka

```json
{
  "name": "Minister Kenji Tanaka",
  "country": "Japan",
  "diplomatic_style": "Aggressive and confrontational",
  "clause_positions": [
    {
      "clause_id": "Article 3.1",
      "position": "conditional_support",
      "comment": "Acceptable if timeline is extended."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 3.1: Extend the compliance deadline from 2030 to 2035 for industrial sectors.",
  "rationale": "The current timeline is too aggressive for our industrial transition capabilities. We propose a phased approach to ensure economic stability while meeting climate goals.",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate1",
  "national_interests": "Japan is committed to achieving carbon neutrality by 2050, with an interim target of a 46% reduction in emissions by 2030. The country prioritizes technological innovation, particularly in hydrogen energy and carbon capture, and seeks financial mechanisms that support R&D and the deployment of new technologies.",
  "national_interests_context": "Japan's approach is shaped by its status as a technology leader and its need to maintain industrial competitiveness. Economically, the country is balancing the costs of decarbonization with the benefits of leading in green tech markets. Socially, there is growing public awareness of climate risks, especially after recent natural disasters, which supports the government's long-term decarbonization goals.",
  "emission_reduction_priority": 10,
  "financial_commitment_priority": 9,
  "target_clauses": [
    "Article 3.1",
    "Article 5.2"
  ],
  "concession_willingness": 0.6,
  "id": "7"
}
```

#### 画像 8：Dr. Amina Diallo

```json
{
  "name": "Dr. Amina Diallo",
  "country": "Senegal",
  "diplomatic_style": "Aggressive and confrontational",
  "clause_positions": [
    {
      "clause_id": "Article 3.1",
      "position": "conditional_support",
      "comment": "Acceptable if timeline is extended."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 3.1: Extend the compliance deadline from 2030 to 2035 for industrial sectors.",
  "rationale": "The current timeline is too aggressive for our industrial transition capabilities. We propose a phased approach to ensure economic stability while meeting climate goals.",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate1",
  "national_interests": "Senegal focuses on adaptation and resilience, seeking significant financial support for climate-resilient infrastructure and sustainable agriculture. The country aims to reduce emissions intensity in its energy sector while prioritizing access to clean energy for its growing population, with a target of 50% renewable energy by 2030.",
  "national_interests_context": "As a developing nation, Senegal's strategy is heavily influenced by its vulnerability to climate change, including sea-level rise and desertification. Politically, there is a strong emphasis on climate justice, demanding that developed nations fulfill their financial commitments. Economically, the country is looking to leverage climate finance to drive sustainable development and reduce poverty.",
  "emission_reduction_priority": 7,
  "financial_commitment_priority": 2,
  "target_clauses": [
    "Article 3.1",
    "Article 5.2"
  ],
  "concession_willingness": 0.6,
  "id": "8"
}
```

#### 画像 9：Ambassador John Smith

```json
{
  "name": "Ambassador John Smith",
  "country": "United States",
  "diplomatic_style": "Assertive but collaborative",
  "clause_positions": [
    {
      "clause_id": "Article 3.1",
      "position": "conditional_support",
      "comment": "Acceptable if timeline is extended."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 3.1: Extend the compliance deadline from 2030 to 2035 for industrial sectors.",
  "rationale": "The current timeline is too aggressive for our industrial transition capabilities. We propose a phased approach to ensure economic stability while meeting climate goals.",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate1",
  "national_interests": "The United States aims to reduce net greenhouse gas emissions by 50-52% below 2005 levels by 2030, with a focus on electrification, renewable energy, and industrial decarbonization. Financially, the U.S. seeks to maintain its leadership in clean energy markets and is willing to contribute to international climate funds, but emphasizes the need for reciprocal commitments from other major emitters.",
  "national_interests_context": "U.S. policy is driven by a combination of environmental concerns, economic opportunities in the green economy, and geopolitical considerations. Politically, there is a bipartisan consensus on the need for climate action, though the pace and methods are debated. Economically, the country is investing heavily in domestic clean energy production to reduce reliance on foreign energy sources and create jobs.",
  "emission_reduction_priority": 1,
  "financial_commitment_priority": 7,
  "target_clauses": [
    "Article 3.1",
    "Article 5.2"
  ],
  "concession_willingness": 0.6,
  "id": "9"
}
```

#### 画像 10：Minister Priya Sharma

```json
{
  "name": "Minister Priya Sharma",
  "country": "India",
  "diplomatic_style": "Cautious and procedural",
  "clause_positions": [
    {
      "clause_id": "Article 3.1",
      "position": "conditional_support",
      "comment": "Acceptable if timeline is extended."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 3.1: Extend the compliance deadline from 2030 to 2035 for industrial sectors.",
  "rationale": "The current timeline is too aggressive for our industrial transition capabilities. We propose a phased approach to ensure economic stability while meeting climate goals.",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate1",
  "national_interests": "India is committed to achieving net-zero emissions by 2070, with a target of 50% of its installed power capacity from non-fossil fuel sources by 2030. The country emphasizes the principle of common but differentiated responsibilities, seeking substantial financial and technological support from developed nations to meet its climate goals while ensuring energy security and economic growth.",
  "national_interests_context": "India's strategy is shaped by its large population, rapid economic growth, and significant energy needs. Politically, there is a strong focus on balancing climate action with development priorities, and the country is advocating for a fair and equitable global climate framework. Economically, India is investing in renewable energy to reduce its carbon intensity and improve energy access, while also seeking to protect its industrial base from the costs of decarbonization.",
  "emission_reduction_priority": 1,
  "financial_commitment_priority": 10,
  "target_clauses": [
    "Article 3.1",
    "Article 5.2"
  ],
  "concession_willingness": 0.6,
  "id": "10"
}
```

### Delegate2

#### 画像 11：Ambassador Elena Rodriguez，本次运行画像

```json
{
  "name": "Ambassador Elena Rodriguez",
  "clause_positions": [
    {
      "clause": "Article 3",
      "position": "conditional_support",
      "reason": "Targets are too aggressive without adequate funding."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 5: Add a clause requiring 50% of funds to be allocated to technology transfer for developing nations.",
  "rationale": "This amendment ensures that the financial commitments are not just monetary but also facilitate the necessary technological shift for our industrial sector.",
  "is_endorsement": 0,
  "endorsed_delegate_id": "Delegate1",
  "diplomatic_tone": "neutral",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate2",
  "national_interests": "Prioritizes equitable financial support for climate adaptation and insists on a 45% emission reduction target by 2030, while demanding binding commitments from developed nations to fund green technology transfers.",
  "national_interests_context": "As a representative of a developing nation heavily reliant on agriculture and vulnerable to climate change impacts, Ambassador Rodriguez emphasizes the need for financial mechanisms that address historical emissions and ensure sustainable development without compromising economic growth.",
  "target_clauses": [
    "Article 5: Financial Mechanisms",
    "Article 7: Technology Transfer",
    "Article 12: Emission Reduction Targets"
  ],
  "concession_willingness": 0.424791194126963,
  "id": "11"
}
```

#### 画像 12：Minister Hans Mueller

```json
{
  "name": "Minister Hans Mueller",
  "clause_positions": [
    {
      "clause": "Article 3",
      "position": "conditional_support",
      "reason": "Targets are too aggressive without adequate funding."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 5: Add a clause requiring 50% of funds to be allocated to technology transfer for developing nations.",
  "rationale": "This amendment ensures that the financial commitments are not just monetary but also facilitate the necessary technological shift for our industrial sector.",
  "is_endorsement": 0,
  "endorsed_delegate_id": "Delegate1",
  "diplomatic_tone": "aggressive",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate2",
  "national_interests": "Advocates for a 55% emission reduction target by 2030, emphasizing the importance of carbon pricing mechanisms and industrial competitiveness in the transition to a low-carbon economy.",
  "national_interests_context": "Representing an industrialized European nation, Minister Mueller focuses on balancing stringent climate goals with economic stability, particularly in sectors like manufacturing and energy, while pushing for international cooperation on carbon border adjustments.",
  "target_clauses": [
    "Article 3: Carbon Pricing",
    "Article 9: Industrial Competitiveness",
    "Article 12: Emission Reduction Targets"
  ],
  "concession_willingness": 0.10443536221327165,
  "id": "12"
}
```

#### 画像 13：Dr. Aisha Khan

```json
{
  "name": "Dr. Aisha Khan",
  "clause_positions": [
    {
      "clause": "Article 3",
      "position": "conditional_support",
      "reason": "Targets are too aggressive without adequate funding."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 5: Add a clause requiring 50% of funds to be allocated to technology transfer for developing nations.",
  "rationale": "This amendment ensures that the financial commitments are not just monetary but also facilitate the necessary technological shift for our industrial sector.",
  "is_endorsement": 0,
  "endorsed_delegate_id": "Delegate1",
  "diplomatic_tone": "aggressive",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate2",
  "national_interests": "Seeks a 40% emission reduction target by 2030, with a strong focus on renewable energy subsidies and international cooperation to secure affordable clean energy technologies.",
  "national_interests_context": "As a delegate from a rapidly growing economy with significant energy demands, Dr. Khan highlights the need for balanced climate policies that support energy security and economic development, while advocating for global partnerships to accelerate the adoption of renewable energy.",
  "target_clauses": [
    "Article 6: Renewable Energy Subsidies",
    "Article 8: International Cooperation",
    "Article 12: Emission Reduction Targets"
  ],
  "concession_willingness": 0.33463180673415127,
  "id": "13"
}
```

#### 画像 14：Ambassador John Smith

```json
{
  "name": "Ambassador John Smith",
  "clause_positions": [
    {
      "clause": "Article 3",
      "position": "conditional_support",
      "reason": "Targets are too aggressive without adequate funding."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 5: Add a clause requiring 50% of funds to be allocated to technology transfer for developing nations.",
  "rationale": "This amendment ensures that the financial commitments are not just monetary but also facilitate the necessary technological shift for our industrial sector.",
  "is_endorsement": 0,
  "endorsed_delegate_id": "Delegate1",
  "diplomatic_tone": "firm_but_cooperative",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate2",
  "national_interests": "Supports a 50% emission reduction target by 2030, emphasizing the role of market-based mechanisms and voluntary national contributions to achieve climate goals.",
  "national_interests_context": "Representing a major developed nation, Ambassador Smith stresses the importance of flexibility in climate commitments, focusing on innovation-driven solutions and the need for a level playing field in international trade.",
  "target_clauses": [
    "Article 4: Market-Based Mechanisms",
    "Article 10: Voluntary Contributions",
    "Article 12: Emission Reduction Targets"
  ],
  "concession_willingness": 0.9632991842936045,
  "id": "14"
}
```

#### 画像 15：Minister Li Wei

```json
{
  "name": "Minister Li Wei",
  "clause_positions": [
    {
      "clause": "Article 3",
      "position": "conditional_support",
      "reason": "Targets are too aggressive without adequate funding."
    }
  ],
  "amendment_text": "Proposed Amendment to Article 5: Add a clause requiring 50% of funds to be allocated to technology transfer for developing nations.",
  "rationale": "This amendment ensures that the financial commitments are not just monetary but also facilitate the necessary technological shift for our industrial sector.",
  "is_endorsement": 0,
  "endorsed_delegate_id": "Delegate1",
  "diplomatic_tone": "neutral",
  "current_status": "reviewing_draft",
  "agent_type": "Delegate2",
  "national_interests": "Advocates for a 45% emission reduction target by 2030, with a focus on balancing economic growth and environmental sustainability through large-scale renewable energy investments.",
  "national_interests_context": "As a delegate from a leading global economy, Minister Li Wei emphasizes the importance of long-term planning and international collaboration to achieve climate neutrality, while ensuring that climate policies do not hinder industrial expansion.",
  "target_clauses": [
    "Article 6: Renewable Energy Investments",
    "Article 11: Long-Term Planning",
    "Article 12: Emission Reduction Targets"
  ],
  "concession_willingness": 0.7212983019732043,
  "id": "15"
}
```

### Delegate3

#### 画像 16：Dr. Elena Rodriguez，本次运行画像

```json
{
  "name": "Dr. Elena Rodriguez",
  "country": "Spain",
  "clause_positions": [
    {
      "clause_id": "mitigation_1",
      "position": "conditional_support",
      "rationale": "Acceptable if financial aid is guaranteed."
    }
  ],
  "amendment_text": "Proposes adding a clause for technology transfer incentives in Article 5.",
  "rationale": "This amendment aligns with our national interest in promoting green technology exports while ensuring equitable burden sharing.",
  "is_endorsement": false,
  "endorsed_delegate_id": "Delegate1",
  "current_status": "reviewing_inputs",
  "agent_type": "Delegate3",
  "national_interests": "Spain advocates for a balanced approach to emission reduction intensity, targeting a 55% reduction by 2030 compared to 1990 levels, while seeking substantial financial commitments from developed nations to support its renewable energy transition and adaptation projects in vulnerable coastal regions.",
  "national_interests_context": "As a member of the European Union, Spain's position is influenced by the EU's collective climate goals and its own economic reliance on tourism and agriculture, which are highly sensitive to climate change impacts. The country also faces internal political pressures to accelerate the energy transition while maintaining economic competitiveness.",
  "bottom_line_threshold": 0.9112980708523912,
  "concession_willingness": 0.6285352140835616,
  "target_clauses": [
    "financial_commitments_2",
    "compliance_mechanisms_1"
  ],
  "synthesis_notes": "Delegate1's focus on mitigation is strong, but Delegate2's financial concerns are valid. A compromise on funding mechanisms is necessary to avoid impasse.",
  "id": "16"
}
```

#### 画像 17：Ambassador Kenji Tanaka

```json
{
  "name": "Ambassador Kenji Tanaka",
  "country": "Japan",
  "clause_positions": [
    {
      "clause_id": "mitigation_1",
      "position": "conditional_support",
      "rationale": "Acceptable if financial aid is guaranteed."
    }
  ],
  "amendment_text": "Proposes adding a clause for technology transfer incentives in Article 5.",
  "rationale": "This amendment aligns with our national interest in promoting green technology exports while ensuring equitable burden sharing.",
  "is_endorsement": false,
  "endorsed_delegate_id": "Delegate1",
  "current_status": "reviewing_inputs",
  "agent_type": "Delegate3",
  "national_interests": "Japan emphasizes a technology-driven approach to emission reduction, aiming for carbon neutrality by 2050, and seeks financial commitments that support innovation in clean energy technologies, hydrogen economy, and carbon capture and storage (CCS) initiatives.",
  "national_interests_context": "Japan's interests are shaped by its status as a developed economy with advanced technological capabilities, its vulnerability to natural disasters exacerbated by climate change, and its strategic goal to lead in green technology markets. The country also considers its energy security needs and the economic implications of transitioning away from fossil fuels.",
  "bottom_line_threshold": 0.7283199631229418,
  "concession_willingness": 0.2743788240611,
  "target_clauses": [
    "financial_commitments_2",
    "compliance_mechanisms_1"
  ],
  "synthesis_notes": "Delegate1's focus on mitigation is strong, but Delegate2's financial concerns are valid. A compromise on funding mechanisms is necessary to avoid impasse.",
  "id": "17"
}
```

#### 画像 18：Minister Amina Diallo

```json
{
  "name": "Minister Amina Diallo",
  "country": "Senegal",
  "clause_positions": [
    {
      "clause_id": "mitigation_1",
      "position": "conditional_support",
      "rationale": "Acceptable if financial aid is guaranteed."
    }
  ],
  "amendment_text": "Proposes adding a clause for technology transfer incentives in Article 5.",
  "rationale": "This amendment aligns with our national interest in promoting green technology exports while ensuring equitable burden sharing.",
  "is_endorsement": false,
  "endorsed_delegate_id": "Delegate1",
  "current_status": "reviewing_inputs",
  "agent_type": "Delegate3",
  "national_interests": "Senegal prioritizes financial commitments from developed nations to fund climate adaptation measures, particularly in agriculture and coastal protection, while advocating for a fair and achievable emission reduction intensity target that accounts for its limited industrial capacity and development needs.",
  "national_interests_context": "As a developing nation in West Africa, Senegal's position is influenced by its vulnerability to climate change impacts such as sea-level rise and desertification, its dependence on agriculture for livelihoods, and its need for international support to meet its climate goals without compromising economic growth and poverty reduction efforts.",
  "bottom_line_threshold": 0.5483350479005701,
  "concession_willingness": 0.603244532235145,
  "target_clauses": [
    "financial_commitments_2",
    "compliance_mechanisms_1"
  ],
  "synthesis_notes": "Delegate1's focus on mitigation is strong, but Delegate2's financial concerns are valid. A compromise on funding mechanisms is necessary to avoid impasse.",
  "id": "18"
}
```

#### 画像 19：Dr. Sarah Johnson

```json
{
  "name": "Dr. Sarah Johnson",
  "country": "Canada",
  "clause_positions": [
    {
      "clause_id": "mitigation_1",
      "position": "conditional_support",
      "rationale": "Acceptable if financial aid is guaranteed."
    }
  ],
  "amendment_text": "Proposes adding a clause for technology transfer incentives in Article 5.",
  "rationale": "This amendment aligns with our national interest in promoting green technology exports while ensuring equitable burden sharing.",
  "is_endorsement": false,
  "endorsed_delegate_id": "Delegate1",
  "current_status": "reviewing_inputs",
  "agent_type": "Delegate3",
  "national_interests": "Canada supports a robust emission reduction intensity target of 40-45% below 2005 levels by 2030, and seeks financial commitments that facilitate the development of its vast renewable energy resources, including hydro, wind, and solar, while ensuring a just transition for workers in fossil fuel industries.",
  "national_interests_context": "Canada's interests are shaped by its abundant natural resources, its commitment to the Paris Agreement, and the political dynamics of balancing environmental goals with economic interests in the oil and gas sector. The country also considers its northern regions' vulnerability to climate change and the importance of indigenous communities in the energy transition.",
  "bottom_line_threshold": 0.8473351100225757,
  "concession_willingness": 0.3871764652141872,
  "target_clauses": [
    "financial_commitments_2",
    "compliance_mechanisms_1"
  ],
  "synthesis_notes": "Delegate1's focus on mitigation is strong, but Delegate2's financial concerns are valid. A compromise on funding mechanisms is necessary to avoid impasse.",
  "id": "19"
}
```

#### 画像 20：Ambassador Rajesh Kumar

```json
{
  "name": "Ambassador Rajesh Kumar",
  "country": "India",
  "clause_positions": [
    {
      "clause_id": "mitigation_1",
      "position": "conditional_support",
      "rationale": "Acceptable if financial aid is guaranteed."
    }
  ],
  "amendment_text": "Proposes adding a clause for technology transfer incentives in Article 5.",
  "rationale": "This amendment aligns with our national interest in promoting green technology exports while ensuring equitable burden sharing.",
  "is_endorsement": false,
  "endorsed_delegate_id": "Delegate1",
  "current_status": "reviewing_inputs",
  "agent_type": "Delegate3",
  "national_interests": "India advocates for a differentiated approach to emission reduction intensity, emphasizing its right to develop and meet the energy needs of its growing population, while seeking significant financial commitments and technology transfer from developed nations to support its renewable energy expansion and climate resilience projects.",
  "national_interests_context": "India's position is influenced by its status as a developing nation with a large population, its heavy reliance on coal for energy, its vulnerability to climate change impacts such as flooding and heatwaves, and its strategic goal to become a global leader in renewable energy. The country also considers its economic growth priorities and the need for international support to achieve its climate commitments.",
  "bottom_line_threshold": 0.6002854027314222,
  "concession_willingness": 0.507821773053149,
  "target_clauses": [
    "financial_commitments_2",
    "compliance_mechanisms_1"
  ],
  "synthesis_notes": "Delegate1's focus on mitigation is strong, but Delegate2's financial concerns are valid. A compromise on funding mechanisms is necessary to avoid impasse.",
  "id": "20"
}
```

## 附录四：全部关系记录

双向记录表示双方都有关系边，单向记录从左侧来源指向右侧目标。下面按来源编号分组，保留文件内每条记录。

- 画像 1：10（双向）、6（双向）、11（双向）、17（双向）、1（单向）。
- 画像 2：7（双向）、8（双向）、15（双向）、13（双向）、20（双向）、19（双向）、1（单向）、5（单向）、3（单向）。
- 画像 3：8（双向）、12（双向）、14（双向）、18（双向）、16（双向）、1（单向）、2（单向）。
- 画像 4：7（双向）、12（双向）、18（双向）、5（单向）。
- 画像 5：8（双向）、11（双向）、13（双向）、17（双向）、18（双向）、19（双向）、4（单向）、1（单向）、2（单向）。
- 画像 6：7（单向）、9（单向）、14（单向）、15（单向）、19（单向）、20（单向）。
- 画像 7：10（单向）、15（单向）、16（单向）。
- 画像 8：10（单向）、11（单向）、15（单向）、13（单向）、19（单向）、17（单向）。
- 画像 9：10（单向）、6（单向）、13（单向）、12（单向）、16（单向）。
- 画像 10：6（单向）、9（单向）、10（单向）、13（单向）、11（单向）、19（单向）、17（单向）。
- 画像 11：14（单向）、13（单向）、11（单向）、19（单向）、16（单向）。
- 画像 12：14（单向）、13（单向）、15（单向）、18（单向）。
- 画像 13：12（单向）、11（单向）、17（单向）。
- 画像 14：11（单向）、15（单向）、13（单向）、18（单向）。
- 画像 15：12（单向）、14（单向）、18（单向）。
- 画像 16：19（单向）、17（单向）、20（单向）。
- 画像 17：20（单向）、16（单向）。
- 画像 18：16（单向）。
- 画像 19：20（单向）、16（单向）。
- 画像 20：18（单向）、19（单向）、17（单向）。

## 附录五：环境初值与数据模式

原始环境初值如下。数据模式及字段默认值也一并列出，便于检查初值、配置和实际处理函数之间的差异。

```json
{
  "draft_content": "Article 3: Mitigation Commitments. Each Party shall implement national policies to reduce greenhouse gas emissions by 45% below 2005 levels by 2030. Article 7: Financial Mechanisms. Developed Parties shall provide an annual aggregate of $100 billion in climate finance to developing Parties, with 50% allocated to adaptation and 50% to mitigation. Article 12: Compliance. A compliance committee shall be established to review Party performance every two years, with non-compliance resulting in mandatory corrective action plans.",
  "agenda_items": [
    "Review and amendment of Article 3 regarding emission reduction intensity targets",
    "Negotiation of Article 7 financial commitment structures and disbursement timelines",
    "Discussion of Article 12 compliance mechanisms and enforcement protocols",
    "Clarification of legal definitions for 'developed' and 'developing' Parties in the context of climate finance"
  ]
}
```

### `system_data_model.json`

```json
{
  "environment": {
    "variables": [
      {
        "name": "draft_content",
        "type": "str",
        "default_value": null
      },
      {
        "name": "agenda_items",
        "type": "list[str]",
        "default_value": null
      }
    ]
  },
  "agents": {
    "Chairperson": {
      "variables": [
        {
          "name": "draft_distributed",
          "type": "bool",
          "default_value": null
        },
        {
          "name": "agenda_set",
          "type": "bool",
          "default_value": null
        },
        {
          "name": "all_positions",
          "type": "dict[str, dict[str, str]]",
          "default_value": null
        },
        {
          "name": "all_amendments",
          "type": "list[dict]",
          "default_value": null
        },
        {
          "name": "identified_divergences",
          "type": "list[str]",
          "default_value": null
        },
        {
          "name": "concession_willingness",
          "type": "dict[str, bool]",
          "default_value": null
        },
        {
          "name": "outcome_status",
          "type": "str",
          "default_value": null
        },
        {
          "name": "aligned_clauses",
          "type": "list[str]",
          "default_value": null
        },
        {
          "name": "divergent_clauses",
          "type": "list[str]",
          "default_value": null
        },
        {
          "name": "final_accepted_positions",
          "type": "dict[str, str]",
          "default_value": null
        },
        {
          "name": "final_agreed_text",
          "type": "str",
          "default_value": null
        },
        {
          "name": "simulation_status",
          "type": "str",
          "default_value": null
        },
        {
          "name": "concession_willingness_status",
          "type": "dict[str, bool]",
          "default_value": null
        },
        {
          "name": "impasse_record",
          "type": "str",
          "default_value": null
        }
      ]
    },
    "Delegate1": {
      "variables": [
        {
          "name": "national_interests",
          "type": "str",
          "default_value": null
        },
        {
          "name": "clause_positions",
          "type": "dict[str, str]",
          "default_value": null
        },
        {
          "name": "national_interests_context",
          "type": "str",
          "default_value": null
        },
        {
          "name": "target_clauses",
          "type": "list[str]",
          "default_value": null
        },
        {
          "name": "amendment_text",
          "type": "str",
          "default_value": null
        },
        {
          "name": "rationale",
          "type": "str",
          "default_value": null
        }
      ]
    },
    "Delegate2": {
      "variables": [
        {
          "name": "national_interests",
          "type": "str",
          "default_value": null
        },
        {
          "name": "clause_positions",
          "type": "dict[str, str]",
          "default_value": null
        },
        {
          "name": "national_interests_context",
          "type": "str",
          "default_value": null
        },
        {
          "name": "target_clauses",
          "type": "list[str]",
          "default_value": null
        },
        {
          "name": "amendment_text",
          "type": "str",
          "default_value": null
        },
        {
          "name": "rationale",
          "type": "str",
          "default_value": null
        },
        {
          "name": "is_endorsement",
          "type": "bool",
          "default_value": null
        },
        {
          "name": "endorsed_delegate_id",
          "type": "str",
          "default_value": null
        }
      ]
    },
    "Delegate3": {
      "variables": [
        {
          "name": "national_interests",
          "type": "str",
          "default_value": null
        },
        {
          "name": "clause_positions",
          "type": "dict[str, str]",
          "default_value": null
        },
        {
          "name": "national_interests_context",
          "type": "str",
          "default_value": null
        },
        {
          "name": "target_clauses",
          "type": "list[str]",
          "default_value": null
        },
        {
          "name": "amendment_text",
          "type": "str",
          "default_value": null
        },
        {
          "name": "rationale",
          "type": "str",
          "default_value": null
        },
        {
          "name": "is_endorsement",
          "type": "bool",
          "default_value": null
        },
        {
          "name": "endorsed_delegate_id",
          "type": "str",
          "default_value": null
        }
      ]
    }
  }
}
```

### `profile/schema/Chairperson.json`

```json
{
  "name": {
    "type": "str",
    "default": "Ambassador Elena Vance",
    "private": false,
    "sampling": "llm",
    "description": "The full name of the Chairperson, a senior diplomat with experience in multilateral climate negotiations."
  },
  "role_title": {
    "type": "str",
    "default": "Presiding Officer of the Climate Cooperation Roundtable",
    "private": false,
    "sampling": "llm",
    "description": "The formal diplomatic title of the Chairperson."
  },
  "diplomatic_style": {
    "type": "str",
    "default": "Formal, neutral, and procedurally rigorous",
    "private": false,
    "sampling": "llm",
    "description": "The communication style adopted by the Chairperson, focusing on neutrality and procedural fairness."
  },
  "coordination_strategy": {
    "type": "str",
    "default": "Consensus-building through iterative compromise and clause-by-clause alignment",
    "private": true,
    "sampling": "llm",
    "description": "The specific strategic approach the Chairperson uses to manage divergences and seek consensus."
  },
  "agenda_set": {
    "type": "str",
    "default": "pending",
    "private": false,
    "sampling": "default"
  },
  "draft_distributed": {
    "type": "str",
    "default": "pending",
    "private": false,
    "sampling": "default"
  },
  "all_positions": {
    "type": "list",
    "default": [
      {
        "delegate": "Delegate1",
        "clause": "Emission Reduction Intensity",
        "position": "awaiting_input"
      }
    ],
    "private": false,
    "sampling": "default"
  },
  "all_amendments": {
    "type": "list",
    "default": [
      {
        "delegate": "Delegate1",
        "clause": "Financial Commitments",
        "proposal": "awaiting_input"
      }
    ],
    "private": false,
    "sampling": "default"
  },
  "identified_divergences": {
    "type": "list",
    "default": [
      "No divergences identified yet"
    ],
    "private": false,
    "sampling": "default"
  },
  "concession_willingness": {
    "type": "list",
    "default": [
      {
        "delegate": "Delegate1",
        "willingness": "unknown"
      }
    ],
    "private": false,
    "sampling": "default"
  },
  "aligned_clauses": {
    "type": "list",
    "default": [
      "Preamble"
    ],
    "private": false,
    "sampling": "default"
  },
  "divergent_clauses": {
    "type": "list",
    "default": [
      "None"
    ],
    "private": false,
    "sampling": "default"
  },
  "final_accepted_positions": {
    "type": "list",
    "default": [
      {
        "clause": "General Principles",
        "position": "pending"
      }
    ],
    "private": false,
    "sampling": "default"
  },
  "outcome_status": {
    "type": "str",
    "default": "in_progress",
    "private": false,
    "sampling": "default"
  },
  "final_agreed_text": {
    "type": "str",
    "default": "Draft text under negotiation...",
    "private": false,
    "sampling": "default"
  },
  "impasse_record": {
    "type": "str",
    "default": "No impasse recorded yet.",
    "private": false,
    "sampling": "default"
  },
  "simulation_status": {
    "type": "str",
    "default": "initializing",
    "private": false,
    "sampling": "default"
  },
  "concession_willingness_status": {
    "type": "list",
    "default": [
      {
        "delegate": "Delegate1",
        "status": "unknown"
      }
    ],
    "private": false,
    "sampling": "default"
  },
  "id": {
    "type": "str",
    "default": "0",
    "private": true,
    "sampling": "default",
    "description": "Unique id of agent"
  }
}
```

### `profile/schema/Delegate1.json`

```json
{
  "name": {
    "type": "str",
    "default": "Ambassador John Doe",
    "private": false,
    "sampling": "llm",
    "description": "The full name of the Delegate1 representative, typically a senior diplomat or minister."
  },
  "country": {
    "type": "str",
    "default": "United States",
    "private": false,
    "sampling": "llm",
    "description": "The country Delegate1 represents in the negotiation."
  },
  "national_interests": {
    "type": "str",
    "default": "Prioritize industrial competitiveness while maintaining moderate emission reduction targets; seek flexible financial mechanisms for developing nations.",
    "private": true,
    "sampling": "llm",
    "description": "A detailed description of the national interests regarding emission reduction intensity and financial commitments that guide Delegate1's strategy."
  },
  "national_interests_context": {
    "type": "str",
    "default": "The country is a major emitter with a strong industrial base. Domestic political pressure exists to avoid binding long-term financial liabilities. The mandate allows for conditional support on mitigation if financial clauses are softened.",
    "private": true,
    "sampling": "llm",
    "description": "Additional context explaining the political, economic, or social factors behind the national interests."
  },
  "diplomatic_style": {
    "type": "str",
    "default": "Assertive but collaborative",
    "private": false,
    "sampling": "random",
    "choices": [
      "Assertive but collaborative",
      "Cautious and procedural",
      "Aggressive and confrontational",
      "Flexible and conciliatory"
    ]
  },
  "emission_reduction_priority": {
    "type": "int",
    "default": 7,
    "private": true,
    "sampling": "random",
    "range": [
      1,
      10
    ]
  },
  "financial_commitment_priority": {
    "type": "int",
    "default": 4,
    "private": true,
    "sampling": "random",
    "range": [
      1,
      10
    ]
  },
  "clause_positions": {
    "type": "list",
    "default": [
      {
        "clause_id": "Article 3.1",
        "position": "conditional_support",
        "comment": "Acceptable if timeline is extended."
      }
    ],
    "private": false,
    "sampling": "default"
  },
  "target_clauses": {
    "type": "list",
    "default": [
      "Article 3.1",
      "Article 5.2"
    ],
    "private": true,
    "sampling": "default"
  },
  "amendment_text": {
    "type": "str",
    "default": "Proposed Amendment to Article 3.1: Extend the compliance deadline from 2030 to 2035 for industrial sectors.",
    "private": false,
    "sampling": "default"
  },
  "rationale": {
    "type": "str",
    "default": "The current timeline is too aggressive for our industrial transition capabilities. We propose a phased approach to ensure economic stability while meeting climate goals.",
    "private": false,
    "sampling": "default"
  },
  "current_status": {
    "type": "str",
    "default": "reviewing_draft",
    "private": false,
    "sampling": "default"
  },
  "concession_willingness": {
    "type": "float",
    "default": 0.6,
    "private": true,
    "sampling": "default"
  },
  "id": {
    "type": "str",
    "default": "0",
    "private": true,
    "sampling": "default",
    "description": "Unique id of agent"
  }
}
```

### `profile/schema/Delegate2.json`

```json
{
  "name": {
    "type": "str",
    "default": "Ambassador Elena Rossi",
    "private": false,
    "sampling": "llm",
    "description": "The full name of the second negotiating delegate, representing a specific nation."
  },
  "national_interests": {
    "type": "str",
    "default": "Prioritize moderate emission reduction targets (15% by 2030) and seek financial aid for green infrastructure transition.",
    "private": true,
    "sampling": "llm",
    "description": "A concise summary of the delegate's core national interests regarding emission reduction intensity and financial commitments."
  },
  "national_interests_context": {
    "type": "str",
    "default": "The nation is a developing economy with high industrial dependency but significant renewable energy potential. It seeks a balance between growth and climate responsibility, demanding technology transfer alongside funding.",
    "private": true,
    "sampling": "llm",
    "description": "Detailed background context explaining the geopolitical and economic factors influencing the delegate's stance."
  },
  "target_clauses": {
    "type": "list",
    "default": [
      "Article 3: Mitigation Targets",
      "Article 5: Financial Mechanisms"
    ],
    "private": true,
    "sampling": "llm",
    "description": "A list of specific clause identifiers or titles from the draft agreement that are most critical to this delegate's national interests."
  },
  "clause_positions": {
    "type": "list",
    "default": [
      {
        "clause": "Article 3",
        "position": "conditional_support",
        "reason": "Targets are too aggressive without adequate funding."
      }
    ],
    "private": false,
    "sampling": "default",
    "description": "Dynamic record of the delegate's current stance on each reviewed clause. Each item is a dict with 'clause', 'position' (support/conditional_support/oppose), and 'reason'."
  },
  "amendment_text": {
    "type": "str",
    "default": "Proposed Amendment to Article 5: Add a clause requiring 50% of funds to be allocated to technology transfer for developing nations.",
    "private": false,
    "sampling": "default",
    "description": "The specific text of the amendment or concession proposed by the delegate in the current round."
  },
  "rationale": {
    "type": "str",
    "default": "This amendment ensures that the financial commitments are not just monetary but also facilitate the necessary technological shift for our industrial sector.",
    "private": false,
    "sampling": "default",
    "description": "The diplomatic and strategic justification for the proposed amendment or position."
  },
  "is_endorsement": {
    "type": "int",
    "default": 0,
    "private": false,
    "sampling": "default",
    "description": "Boolean flag (0 or 1) indicating if the delegate is primarily endorsing Delegate1's proposal rather than proposing a new one."
  },
  "endorsed_delegate_id": {
    "type": "str",
    "default": "Delegate1",
    "private": false,
    "sampling": "default",
    "description": "The identifier of the delegate whose proposal is being endorsed, if is_endorsement is true."
  },
  "diplomatic_tone": {
    "type": "str",
    "default": "firm_but_cooperative",
    "private": false,
    "sampling": "random",
    "choices": [
      "aggressive",
      "firm_but_cooperative",
      "conciliatory",
      "neutral"
    ],
    "description": "The general diplomatic tone adopted by the delegate during negotiations."
  },
  "concession_willingness": {
    "type": "float",
    "default": 0.6,
    "private": true,
    "sampling": "random",
    "range": [
      0,
      1
    ],
    "description": "A score representing how willing the delegate is to make concessions on non-core issues."
  },
  "current_status": {
    "type": "str",
    "default": "reviewing_draft",
    "private": false,
    "sampling": "default",
    "description": "The current state of the delegate in the workflow (e.g., reviewing_draft, forming_position, proposing_amendment, waiting)."
  },
  "id": {
    "type": "str",
    "default": "0",
    "private": true,
    "sampling": "default",
    "description": "Unique id of agent"
  }
}
```

### `profile/schema/Delegate3.json`

```json
{
  "name": {
    "type": "str",
    "default": "Ambassador Elena Rossi",
    "private": false,
    "sampling": "llm",
    "description": "The full name of the third negotiating representative (Delegate3)."
  },
  "country": {
    "type": "str",
    "default": "Italy",
    "private": false,
    "sampling": "llm",
    "description": "The country represented by Delegate3."
  },
  "national_interests": {
    "type": "str",
    "default": "Prioritizes balanced emission reduction targets with significant financial support for developing nations; opposes binding penalties without compliance mechanisms.",
    "private": true,
    "sampling": "llm",
    "description": "A detailed description of the national interests regarding emission reduction intensity and financial commitments."
  },
  "national_interests_context": {
    "type": "str",
    "default": "As a G7 member with a strong manufacturing sector, the nation seeks to protect industrial competitiveness while demonstrating leadership in climate action. Financial commitments are viewed as a tool for geopolitical influence.",
    "private": true,
    "sampling": "llm",
    "description": "The broader political and economic context influencing the national interests."
  },
  "bottom_line_threshold": {
    "type": "float",
    "default": 0.75,
    "private": true,
    "sampling": "random",
    "range": [
      0.5,
      0.95
    ],
    "description": "The minimum level of alignment (0.0 to 1.0) required on core clauses before the delegate considers their national bottom line touched."
  },
  "concession_willingness": {
    "type": "float",
    "default": 0.6,
    "private": true,
    "sampling": "random",
    "range": [
      0.2,
      0.9
    ],
    "description": "The initial willingness to make concessions (0.0 to 1.0) to push the negotiation forward."
  },
  "clause_positions": {
    "type": "list",
    "default": [
      {
        "clause_id": "mitigation_1",
        "position": "conditional_support",
        "rationale": "Acceptable if financial aid is guaranteed."
      }
    ],
    "private": false,
    "sampling": "default",
    "description": "A list of positions on specific clauses, including clause ID, position (support/conditional_support/oppose), and rationale."
  },
  "target_clauses": {
    "type": "list",
    "default": [
      "financial_commitments_2",
      "compliance_mechanisms_1"
    ],
    "private": true,
    "sampling": "default",
    "description": "A list of clause IDs that are of primary concern to this delegate."
  },
  "amendment_text": {
    "type": "str",
    "default": "Proposes adding a clause for technology transfer incentives in Article 5.",
    "private": false,
    "sampling": "default",
    "description": "The specific text of the amendment or concession proposed by Delegate3."
  },
  "rationale": {
    "type": "str",
    "default": "This amendment aligns with our national interest in promoting green technology exports while ensuring equitable burden sharing.",
    "private": false,
    "sampling": "default",
    "description": "The diplomatic and strategic reasoning behind the proposed amendment or position."
  },
  "is_endorsement": {
    "type": "bool",
    "default": false,
    "private": false,
    "sampling": "default",
    "description": "Indicates whether Delegate3 is endorsing a previous delegate's proposal rather than making a new one."
  },
  "endorsed_delegate_id": {
    "type": "str",
    "default": "Delegate1",
    "private": false,
    "sampling": "default",
    "description": "The ID of the delegate whose proposal is being endorsed, if is_endorsement is true."
  },
  "synthesis_notes": {
    "type": "str",
    "default": "Delegate1's focus on mitigation is strong, but Delegate2's financial concerns are valid. A compromise on funding mechanisms is necessary to avoid impasse.",
    "private": true,
    "sampling": "default",
    "description": "Internal notes synthesizing the inputs from Delegate1 and Delegate2 to inform Delegate3's strategy."
  },
  "current_status": {
    "type": "str",
    "default": "reviewing_inputs",
    "private": false,
    "sampling": "default",
    "description": "The current state of the agent in the workflow (e.g., reviewing_inputs, formulating_position, proposing_amendment, waiting_for_outcome)."
  },
  "id": {
    "type": "str",
    "default": "0",
    "private": true,
    "sampling": "default",
    "description": "Unique id of agent"
  }
}
```

### `profile/schema/Relationship.json`

```json
[
  {
    "source_agent": "Chairperson",
    "target_agent": "Delegate1",
    "direction": "bidirectional"
  },
  {
    "source_agent": "Chairperson",
    "target_agent": "Delegate2",
    "direction": "bidirectional"
  },
  {
    "source_agent": "Chairperson",
    "target_agent": "Delegate3",
    "direction": "bidirectional"
  },
  {
    "source_agent": "Chairperson",
    "target_agent": "Chairperson",
    "direction": "unidirectional"
  },
  {
    "source_agent": "Delegate1",
    "target_agent": "Delegate1",
    "direction": "unidirectional"
  },
  {
    "source_agent": "Delegate1",
    "target_agent": "Delegate2",
    "direction": "unidirectional"
  },
  {
    "source_agent": "Delegate2",
    "target_agent": "Delegate2",
    "direction": "unidirectional"
  },
  {
    "source_agent": "Delegate2",
    "target_agent": "Delegate3",
    "direction": "unidirectional"
  },
  {
    "source_agent": "Delegate3",
    "target_agent": "Delegate3",
    "direction": "unidirectional"
  },
  {
    "source_agent": "Delegate1",
    "target_agent": "Delegate3",
    "direction": "unidirectional"
  }
]
```
