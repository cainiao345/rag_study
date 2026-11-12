# 研报问答库（S3 · RAG 验收项目）

把研报 / 财报 PDF 或 txt 解析入库，回答「这家公司现金流怎么样」这类问题，
并在答案后**自动注明出处（文档 + 页码）**——只依据资料作答，资料没写就答「资料中未提及」，绝不编造。

> 这是「Agent 工程化」学习路线 S3 的验收项目，代码集中在 `D:/lw/Obsidian_store/rag_study/`。
> S2 的「盯盘助手后端」在 `../agent_study/`，是**另一个独立仓库**，与本项目互不相干。

## 功能特性
- 📄 **解析入库**：txt（用 `\f` 换页符分页）/ PDF（逐页），页码从第一步就留在出处卡里。
- 🔍 **语义检索**：硅基流动 `BAAI/bge-m3` 把文字变 1024 维向量，Chroma 本地持久化、余弦距离取 top-k。
- 🤖 **防编造作答**：DeepSeek `deepseek-flash` 只准照着检索回来的真料写答案，温度压到 0.1。
- 📌 **答案溯源**：出处由程序拼（文件名 + 页码 + 距离），**不让模型自己写页码**。
- 🧯 **防呆三件套**：`check_env.py`（启动前查钥匙）、`audit_index.py`（入库前查三列）、`audit_hits.py`（调模型前查料）。
- 🔐 **密钥安全**：两把 key 走 `.env` + 环境变量，代码里零明文；`.env` 被 `.gitignore` 排除，不进 Git。

## 技术选型

| 环节 | 选型 | 说明 |
|---|---|---|
| 生成答案 | DeepSeek `deepseek-flash` | `deepseek-chat` 已于 2026/07/24 弃用，新项目不用旧名 |
| 文字→向量 | 硅基流动 `BAAI/bge-m3` | OpenAI 兼容 `/embeddings`，1024 维，中文友好，有免费档（限 RPM/TPM） |
| PDF 文字 | PyMuPDF（`import pymupdf`） | 逐页抽文字、留住页码；PyMuPDF 2.1 起 `import fitz` 已弃用 |
| PDF 表格 | `pdfplumber` | `extract_tables()` 转成「表头：值」的人话 |
| 向量库 | Chroma（`PersistentClient`） | 落盘到 `chroma_db/`，集合 `reports`，`hnsw:space=cosine` |
| 密钥管理 | `.env` + `python-dotenv` | `load_dotenv()` + `os.getenv()`，真 key 绝不进代码、绝不提交 |

> ⚠️ **DeepSeek 没有 `/embeddings` 端点**，所以本项目必须**两个 client、两把 key**：
> `chat_client` 只调对话（DeepSeek）、`embed_client` 只调向量化（硅基流动），不能混用。
> 建库和提问还必须共用同一个 `EMBED_MODEL`，否则两套坐标系、检索全是噪声且**不报错**。

## 环境要求
- Python 3.9+（本机验收环境：3.13.14）
- 能访问 `api.deepseek.com` 与 `api.siliconflow.cn`
- 两把 key：DeepSeek 的、硅基流动的（国内站 `.cn` 与国际站 `.com` 的 key 不通用）

## 快速开始

> 依赖装在**项目专属虚拟环境** `.venv/` 里，不污染全局 Python；`.venv/` 已被 `.gitignore` 排除。

```bash
# ① 进入项目目录（下面所有命令都假设你在这里执行）
cd D:/lw/Obsidian_store/rag_study

# ② 建虚拟环境：只做一次，会在当前目录生成 .venv/ 文件夹
python -m venv .venv

# ③ 激活：三种终端写法不同，选你正在用的那个
source .venv/Scripts/activate          # Git Bash
# .venv\Scripts\Activate.ps1           # Windows PowerShell
# .venv\Scripts\activate.bat           # CMD

# ④ 装依赖：激活后 python / pip 都指向 .venv，不会装到全局
pip install -r requirements.txt

# ⑤ 配置密钥：复制样例为 .env，把两把占位 key 换成真值
cp .env.example .env                   # Windows CMD 用 copy .env.example .env
# .env 已被 .gitignore 排除，永远不会提交；两把 key 来自不同平台，别填反

# ⑥ 启动前自检：检查 4 个必需变量，缺了点名报错，全程不打印密钥
python check_env.py

# ⑦ 放资料：txt / pdf 丢进 data/ 目录
#    txt 用 \f（换页符）分页；PDF 天然逐页；页码就是溯源用的页码

# ⑧ 建库：解析 → 按句切块配出处卡 → 批量向量化 → 删旧集合重建 → 四列入库
python build_index.py
#    会生成 chroma_db/（已排除，不提交）；重复运行是安全的，幂等重建不会 id 冲突

# ⑨ 提问：问题写在命令行里，答案后面自动跟一段【出处】
python answer.py "2023 年经营活动现金流量净额是多少？同比增长多少？"
#    不带参数也能跑，会用同一个默认问题演示

# ⑩ 两个体检工具自测（纯 Python，不调 API、不花钱）
python audit_index.py
python audit_hits.py
```

`.env` 需要的变量（详见 `.env.example`）：

| 变量 | 作用 | 必需 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 生成答案的 key | ✅ |
| `DEEPSEEK_BASE_URL` | DeepSeek 地址，代码有默认值 `https://api.deepseek.com` | 可选 |
| `SILICONFLOW_API_KEY` | 向量化的 key（另一把） | ✅ |
| `EMBED_BASE_URL` | 硅基流动网关，**必须带 `/v1`** | ✅ |
| `EMBED_MODEL` | 向量模型名，大小写要完全一致 | ✅ |

## 文件结构与流水线

```
rag_study/
├── .env.example        # 占位样例（可提交）；真 .env 被排除
├── .gitignore          # 排除 .env / chroma_db/ / .venv/ / __pycache__/
├── requirements.txt    # 5 个依赖，一键安装
├── README.md           # 本文件
├── check_env.py        # ① 启动前：钥匙齐不齐
├── build_index.py      # ② 索引侧：解析 → 切块 → 向量化 → 入库（一次性/改资料后重跑）
├── answer.py           # ③ 问答侧：提问 → 检索 → 防编造 prompt → 生成 → 出处
├── audit_index.py      # 体检：入库前三列对齐（可单独跑自测）
├── audit_hits.py       # 体检：调模型前检索结果质量（可单独跑自测）
├── data/示例研报.txt    # 教学用虚构数据（3 页，非真实研报）
└── chroma_db/          # 运行后自动生成的向量库（不提交）
```

**两条链**：建库（离线、一次性）＝ `check_env → build_index`；问答（每次提问）＝ `check_env → answer`。
改了分块策略或换了资料，**必须重跑 `build_index.py` 重建索引**（第 8 课的坑：不重建就会「改了代码答案没变」）。

## 端到端验收示例

```bash
python answer.py "2023 年经营活动现金流量净额是多少？同比增长多少？"
```

```
【检索】命中 3 块：
  [1] 示例研报.txt 第2页｜距离 0.2568｜217 字
  [2] 示例研报.txt 第3页｜距离 0.3119｜188 字
  [3] 示例研报.txt 第1页｜距离 0.3815｜173 字

【答案】
2023年经营活动产生的现金流量净额为320亿元，同比增长14.3%……

【出处】
[1] 示例研报.txt 第2页（距离 0.2568）
[2] 示例研报.txt 第3页（距离 0.3119）
[3] 示例研报.txt 第1页（距离 0.3815）
```
> 距离每次会有微小浮动（服务端向量计算的正常现象），**排序和第 2 页居首**才是验收要看的。

问资料里没有的内容（如「2025 年海外收入占比」）→ 回答「资料中未提及。」，防编造规矩生效。
`distance` 是**距离**，越小越像（0 = 完全一致）；普遍 >0.8 说明资料可能压根不覆盖这个问题，该先补料。

## 排障速查

| 现象 | 先查哪里 |
|---|---|
| `缺少环境变量：…` | `.env` 有没有复制、有没有填占位值、值后面有没有多余空格 |
| 向量化 401 / 404 | 两把 key 有没有填反；`EMBED_BASE_URL` 是否漏了 `/v1` |
| `Repository not found`（仓库明明建好了） | 多半是**私有仓库没带凭据**：GitHub 对未登录访问私有仓库也故意回这句；用 PAT 登录 GCM 后重试 |
| `Authentication failed` | 密码栏要贴 PAT，不是 GitHub 账号密码；token 可能过期或没勾 `repo` 权限 |
| `CONNECT tunnel failed, 502` | 当前网络代理到不了 GitHub，换网络或绕过代理再 push |
| `请先运行 build_index.py` | 库还没建；`answer.py` 故意用 `get_collection` 明确报错，不悄悄建空库 |
| 答案一直「资料中未提及」 | 先看 `【检索】命中 N 块`，再看 `chroma_db/` 是否为空集合 |
| `集合 reports 现有 6 条` | 说明没走幂等重建（旧集合没删），重跑 `build_index.py` |
| 答案张冠李戴、原文看着却是对的 | 原文↔向量错配（静默错误），**只能重建索引** |
| 改了分块代码答案不变 | 忘了重建索引 |
| 真实研报 PDF 抽不出文字 | 扫描版无文字层，需要 OCR |

## 交付与版本管理

```bash
# 第一次：把当前目录变成 Git 仓库，并直接把主分支命名为 main
git init -b main

# 只把该交的文件加入暂存区（显式列名，比 git add . 更容易自查）
# Git Bash 用 \ 续行；PowerShell 请写成一整行（或用反引号 ` 续行），CMD 不支持 \
git add .env.example .gitignore README.md requirements.txt \
        check_env.py build_index.py answer.py audit_index.py audit_hits.py \
        data/示例研报.txt

# 提交前必查：确认 .env / chroma_db / .venv 都不在待提交列表里
git status --short
git check-ignore -v .env chroma_db/ .venv/ __pycache__/
#   目录名要带结尾的 /，才和 .gitignore 里的 `chroma_db/` 这类规则对得上

# 提交到本地仓库（写清楚这次做了什么，别写 "update"）
git commit -m "完成 S3 验收项目：研报问答库（RAG 全链路 + 答案溯源）"

# 关联远程仓库并推送（仓库需先在 GitHub 上建好，且不要勾选初始化 README）
git remote add origin https://github.com/<你的用户名>/rag_study.git
git branch -M main
git push -u origin main
```

> 🔑 **私有仓库要先登录**：第一次 push 会弹 Git Credential Manager 窗口，
> 用户名填 GitHub 账号名，**密码栏粘贴 Personal Access Token（PAT）**——
> GitHub 2021 年起已禁用账号密码，PAT 需勾选 `repo` 权限并授权到该仓库。
> 登录成功后凭据会存进 Windows 凭据管理器，以后不必再填。
> 若旧凭据失效，先到「Windows 凭据管理器 → Windows 凭据」删掉 `git:https://github.com` 再重试。

> 🔐 **红线**：真 `.env` 绝不提交（含密钥）、`chroma_db/` 绝不提交（体积大、与机器相关）、
> `.venv/` 绝不提交（几百 MB 且平台相关）。这三条已写进 `.gitignore`。
> 万一误提交了 key，**删掉文件再 commit 也没用**（Git 历史里还在），要去平台作废重发。

> 📄 **资料版权**：`data/示例研报.txt` 是教学虚构数据，可以提交；放真实研报前先想清楚版权，
> 必要时把 `.gitignore` 里 `data/` 那一行的注释取消掉。

## 验收清单
- [x] 能把研报 / 财报 PDF 或 txt 解析入库
- [x] 能回答「这家公司现金流怎么样」这类问题，且只依据资料、不编造
- [x] 答案后注明出处（文档 + 页码）
- [x] 命令行可运行 + 完整 README
- [ ] 上传 GitHub（本地 `git init` / `commit` 已完成，推送由仓库维护者执行上一节命令）
