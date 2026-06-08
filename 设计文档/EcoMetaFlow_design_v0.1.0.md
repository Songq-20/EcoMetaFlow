# EcoMetaFlow 设计文档 v0.1.0

> 暂定名：EcoMetaFlow  
> 定位：面向环境宏基因组、宏病毒组和微生物风险分析的生物信息学 workflow runner。  
> 当前版本目标：先搭建一个可运行、可扩展、适合 HPC/本地双场景的工作流骨架，不在 v0.1.0 实际完成完整生信分析。

---

## 1. 项目定位

EcoMetaFlow 不是一个重新发明生信算法的软件，而是一个 **workflow orchestration + tool environment management + result organization + future reporting** 工具。

它的核心目标是：

1. 让用户尽量少手动准备配置文件。
2. 接收一个 raw reads 文件夹，自动识别 `.fq.gz` / `.fastq.gz` 文件。
3. 根据用户选择的模块，自动检查所需工具和数据库。
4. 支持本地单人使用，也支持 HPC 上一人部署、多人共用。
5. 逐步把已有生信工具串联成标准化流程。
6. 最终生成基础生态统计、病毒/MAG/微生物风险相关结果和报告。

---

## 2. 目标用户

### 2.1 小白 / 本地单人用户

用户不应该手动下载一堆工具、数据库，也不应该手动编辑复杂配置。理想使用方式是：

```bash
ecometa-flow install --module virus_prediction

ecometa-flow run \
  -m virus_prediction \
  -i raw_reads \
  -o work_virus \
  -t 16
```

### 2.2 HPC / 课题组共享用户

HPC 上常见情况是：一个人或管理员安装好软件和环境，其他人只需要 `source` 或 `module load`。这种场景必须支持共享的 `envs.yaml`：

```bash
ecometa-flow run \
  -m virus_prediction \
  -i raw_reads \
  -o work_virus \
  --envs /data/software/EcoMetaFlow/config/envs.yaml \
  -t 16
```

也可以通过环境变量省略：

```bash
export ECOMETA_ENVS=/data/software/EcoMetaFlow/config/envs.yaml

ecometa-flow run -m virus_prediction -i raw_reads -o work_virus -t 16
```

---

## 3. 核心模块规划

v0.1.0 只实现模块框架，不真实运行完整工具链。

### 3.1 `virus_prediction`

未来完整流程：

```text
raw reads
→ Trimmomatic
→ clean reads
→ MEGAHIT
→ contigs
→ VirSorter2 / geNomad / VIBRANT / VirFinder
→ viral contigs
→ CheckV
→ clustering / vOTU
→ taxonomy
→ Bowtie2 + Samtools mapping
→ abundance
→ reports
```

### 3.2 `mag_pipeline`

未来完整流程：

```text
raw reads
→ Trimmomatic
→ clean reads
→ MEGAHIT
→ contigs
→ BASALT
→ bins
→ CheckM / CheckM2
→ dRep
→ non-redundant MAGs
→ GTDB-Tk taxonomy
→ CoverM abundance
→ reports
```

### 3.3 `read_based_risk`

未来完整流程：

```text
raw reads
→ Trimmomatic
→ clean reads
→ Kraken2 + TaxonKit
→ taxonomy
→ compare with pathogenic database
→ pathogenic reads / taxa
→ abundance
→ reports
```

### 3.4 `micro_risk`

未来综合风险模块：

```text
virus_prediction results + mag_pipeline results + read_based_risk results
→ compare with pathogenic virus / bacteria databases
→ viral risk
→ prokaryotic risk
→ risk index calculation
→ optional phylogenetic validation
→ reports
```

---

## 4. 输入设计

### 4.1 默认输入：raw reads 文件夹

默认用户只提供一个 reads 文件夹：

```bash
-i raw_reads/
```

程序自动扫描：

```text
*.fq.gz
*.fastq.gz
*.fq
*.fastq
```

v0.1.0 优先支持常见 paired-end 命名：

```text
Sample_R1.fq.gz / Sample_R2.fq.gz
Sample_1.fq.gz  / Sample_2.fq.gz
Sample.R1.fq.gz / Sample.R2.fq.gz
```

如果文件名不标准，程序应该给出明确错误提示，并建议使用 `--samples samples.csv`。

### 4.2 可选输入：samples.csv

高级用户可以手动提供样品表作为兜底：

```bash
--samples samples.csv
```

格式：

```csv
SampleID,R1,R2,Group,DataType
S1,data/S1_R1.fq.gz,data/S1_R2.fq.gz,RW,metagenome
S2,data/S2_R1.fq.gz,data/S2_R2.fq.gz,WW,metavirome
```

必需列：

```text
SampleID,R1,R2
```

其他列可选。

---

## 5. 配置设计

EcoMetaFlow 使用三个概念文件：

### 5.1 `requirements.yaml`

EcoMetaFlow 内置文件，用户不编辑。作用：定义每个模块需要哪些工具和数据库。

示例：

```yaml
modules:
  virus_prediction:
    tools:
      - trimmomatic
      - megahit
      - virsorter2
      - genomad
      - vibrant
      - checkv
      - bowtie2
      - samtools
    databases:
      - checkv_db

  mag_pipeline:
    tools:
      - trimmomatic
      - megahit
      - basalt
      - checkm
      - drep
      - gtdbtk
      - coverm
    databases:
      - gtdbtk_db

  read_based_risk:
    tools:
      - trimmomatic
      - kraken2
      - taxonkit
    databases:
      - kraken2_db
      - pathogen_db
```

### 5.2 `envs.yaml`

实际环境状态文件。作用：记录工具和数据库实际在哪里。

来源可以是：

1. HPC 管理员提供。
2. 用户通过 `ecometa-flow install` 自动生成。
3. 用户手动编辑。
4. 软件默认位置读取。

建议优先级：

```text
1. 命令行 --envs 指定
2. 环境变量 $ECOMETA_ENVS
3. 当前项目目录 ./envs.yaml
4. 用户目录 ~/.ecometa-flow/envs.yaml
5. 软件安装目录 $ECOMETA_HOME/config/envs.yaml
6. PATH 自动检测
```

示例格式：

```yaml
tools:
  trimmomatic:
    mode: conda
    env: /data/software/ecometa-flow/envs/trimmomatic
    command: trimmomatic

  megahit:
    mode: conda
    env: /data/software/ecometa-flow/envs/megahit
    command: megahit

  checkv:
    mode: conda
    env: /data/software/ecometa-flow/envs/checkv
    command: checkv

databases:
  checkv_db: /data/database/checkv-db
  kraken2_db: /data/database/kraken2-db
  gtdbtk_db: /data/database/gtdbtk-db
```

v0.1.0 先支持两种 tool mode：

```text
command：直接调用 command
conda：通过 conda run -p env command 调用
```

以后再支持：

```text
module
apptainer / singularity
absolute_path
```

### 5.3 `install.yaml`

EcoMetaFlow 内置文件，用户一般不编辑。作用：定义缺失工具/数据库如何安装。

v0.1.0 只建立结构和 dry-run，不真实安装大型工具和数据库。

示例：

```yaml
tools:
  trimmomatic:
    installer: conda
    package: bioconda::trimmomatic

  megahit:
    installer: conda
    package: bioconda::megahit

  checkv:
    installer: conda
    package: bioconda::checkv

databases:
  checkv_db:
    installer: manual_or_download_later
    note: "Database download will be implemented in a future version."
```

---

## 6. 安装逻辑

### 6.1 最小模块安装

```bash
ecometa-flow install --module virus_prediction
```

逻辑：

```text
1. 读取 requirements.yaml
2. 找到 virus_prediction 需要的 tools/databases
3. 查找或创建 envs.yaml
4. 对比 requirements.yaml 与 envs.yaml
5. 已存在的跳过
6. 缺失的列出
7. v0.1.0 只 dry-run 显示将要安装什么
8. 未来版本再执行真实安装
```

### 6.2 全量安装

```bash
ecometa-flow install --all
```

逻辑：安装所有模块需要的 tools/databases。

README 必须提醒：`--all` 可能非常大，不建议普通用户一开始使用。

### 6.3 使用已有 envs.yaml

```bash
ecometa-flow install --module virus_prediction --envs envs.yaml
```

逻辑：

```text
1. 读取用户提供的 envs.yaml
2. 和 requirements.yaml 对比
3. 已有工具不动
4. 缺失工具列出
5. v0.1.0 只显示缺失项，不真实安装
```

---

## 7. 运行逻辑

基本命令：

```bash
ecometa-flow run \
  -m virus_prediction \
  -i raw_reads \
  -o work_virus \
  -t 16 \
  --dry-run
```

运行步骤：

```text
1. 解析命令行参数
2. 识别 module
3. 查找 envs.yaml
4. 读取 requirements.yaml
5. 检查该模块所需 tools/databases 是否在 envs.yaml 中存在
6. 扫描 input folder 或读取 samples.csv
7. 验证 paired-end reads
8. 创建标准工作目录
9. 生成计划执行的 shell commands
10. dry-run 时只打印命令，不执行
```

---

## 8. v0.1.0 应实现的功能

v0.1.0 的目标是 **让项目活起来**，而不是完成真实生信分析。

### 8.1 必须实现

1. Python CLI 项目结构。
2. 命令：`run`。
3. 命令：`check`。
4. 命令：`install`，但只支持 dry-run / mock install。
5. 支持模块：
   - `virus_prediction`
   - `mag_pipeline`
   - `read_based_risk`
   - `micro_risk`
6. `-i / --input` 输入 reads 文件夹。
7. 自动扫描 `.fq.gz` / `.fastq.gz`。
8. 自动识别 paired-end reads。
9. `--samples` 可选兜底。
10. `--envs` 可选。
11. `--params` 可选。
12. `--dry-run` 打印计划命令。
13. 对比 `requirements.yaml` 与 `envs.yaml`。
14. 输出缺失工具/数据库列表。
15. 创建标准工作目录。
16. 生成模块对应的计划命令，但不真实执行外部生信工具。
17. README 写清楚使用方式和 `envs.yaml` 格式。

### 8.2 v0.1.0 不做

1. 不真实下载大型数据库。
2. 不真实创建 conda 环境。
3. 不运行 Trimmomatic / MEGAHIT / VirSorter2 / CheckV 等外部工具。
4. 不做 Snakemake / Nextflow。
5. 不做 Web UI。
6. 不做 Docker / Apptainer。
7. 不做完整 report。
8. 不做系统发育树。
9. 不做 risk index 真实计算。
10. 不做复杂文件名识别，只支持常见 paired-end 命名。

---

## 9. v0.1.0 应产生的软件结构

建议项目结构：

```text
EcoMetaFlow/
├── README.md
├── pyproject.toml
├── requirements.txt
├── examples/
│   ├── raw_reads/
│   │   ├── S1_R1.fq.gz
│   │   ├── S1_R2.fq.gz
│   │   ├── S2_R1.fq.gz
│   │   └── S2_R2.fq.gz
│   ├── samples.csv
│   ├── envs.yaml
│   └── params.yaml
├── src/
│   └── ecometa_flow/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── requirements.py
│       ├── envs.py
│       ├── samples.py
│       ├── scanner.py
│       ├── modules.py
│       ├── commands.py
│       ├── runner.py
│       └── installer.py
├── src/ecometa_flow/data/
│   ├── requirements.yaml
│   └── install.yaml
└── tests/
    ├── test_scanner.py
    ├── test_samples.py
    ├── test_envs.py
    └── test_requirements.py
```

生成的工作目录结构：

```text
work_virus/
├── config/
├── data/
├── logs/
├── results/
│   ├── clean_reads/
│   ├── assembly/
│   ├── virus_prediction/
│   ├── mapping/
│   └── abundance/
├── scripts/
│   ├── 00_check_environment.sh
│   ├── 01_trimming.sh
│   ├── 02_assembly.sh
│   └── 03_virus_prediction.sh
└── tmp/
```

---

## 10. Coding 限制

Cursor / Codex 写代码时必须遵守：

1. 优先做小而可运行的版本。
2. 不要过度设计。
3. 不要一次生成复杂 workflow engine。
4. 不要添加 Web UI。
5. 不要添加数据库系统。
6. 不要添加 Docker / Nextflow / Snakemake。
7. 不要真实运行外部工具。
8. 不要真实下载大型数据库。
9. 使用 Python 标准库 + PyYAML 即可。
10. 路径处理必须使用 `pathlib`。
11. CLI 使用 `argparse`，不要先引入 Click/Typer。
12. 代码必须有清楚注释。
13. 每个函数尽量短。
14. 每个模块职责清楚。
15. 所有命令默认支持 `--dry-run`。
16. 文件名识别逻辑先支持常见命名，不要追求覆盖所有情况。
17. 对错误给出人能看懂的提示。
18. 生成 shell command 即可，不执行真实工具。
19. 测试只测内部逻辑，不依赖真实生信软件。
20. 每次开发最多改一小组相关文件。

---

## 11. 后续版本路线

### v0.2.0

实现真实 shell script 输出，支持 Trimmomatic + MEGAHIT 的命令生成。

### v0.3.0

实现 `virus_prediction` 真命令链：VirSorter2 / geNomad / VIBRANT / CheckV 的命令生成与结果目录组织。

### v0.4.0

实现 `mag_pipeline` 真命令链：BASALT / CheckM / dRep / GTDB-Tk / CoverM。

### v0.5.0

实现 `read_based_risk`：Kraken2 / TaxonKit / pathogenic database comparison。

### v0.6.0

实现初版 report：HTML / Markdown summary。

### v0.7.0+

实现 risk index、系统发育验证、可视化和高级报告。

