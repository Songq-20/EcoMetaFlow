# EcoMetaFlow 设计手册
## 目的
> EcoMetaFlow 旨在一站式处理环境宏基因组、宏病毒组的测序数据，生成基础数据文件及统计结果。同时计划引入基于微生物致病性和耐药性的风险评估模块。
## 接受输入
* metagenomic raw reads -- fq.gz
* metaviromic raw reads -- fq.gz
* sample metadata -- csv
* installed (conda or mamba) environment path -- txt
* parameter -- txt : allow users to cuntom the parameters in each kay tools in the pipline.
## 基本原则（拟定）
0. 软件本体只做调用现有 bioinformatics pipeline生成结果和进行基础生态统计，给 report 两件事，不重新开发工具。
1. 软件做模块设计，接收数据后，用户自行选择`virus pridiction`, `MAGs pipline`, `micro- risk based on reads`, `micro- risk`
## 运行流程
0. 安装时，`installed (conda or mamba) environment path` 都是必要的，文件中的 env 与 requirement 对比，缺失的进行 conda 安装。
1. 运行时检查输入，`paired reads`,`sample metadata`,`parameter`文件不可缺少，`-m module`参数不可缺少，同时接收参数 `-t max threads`, `-o work_dir`, `-tmp tmp_dir`
2. 按照用户输入的模块，进行相应的调用和运行：  
2.1 检查工作路径是否存在，不存在就创建  
2.2 按照parameter 文件，调整脚本中调用 pipline 时的参数  
2.3 运行。
---  
---
## 模块设计
### virus pridiction
```
raw reads --(trimmomatic)--> clean reads --(megahit)--> contigs --(virsorter2,genomad,virfinder,vibrant)--> vcontig  --(checkv clustering)--> vOTU --(classify workflow)--> tax --(bowtie2,samtools+cleanreads)--> abundance --> reports
```
### MAGs pipline
```
raw reads --(trimmomatic)--> clean reads --(megahit)--> contigs --(BASALT)--> bins --(checkm+drep)--> nrMH_MAGs --(gtdb-tk)--> tax --(coberm+cleanreads)--> abundance --> reports
```
### micro- risk based on reads
```
raw reads --(trimmomatic)--> clean reads --(Kraken2+taxonkit)--> tax --compare with database(based on tax)--> pathogenic reads --> abundance --> reports
```
### micro- risk
```
#viral risk
raw reads --(trimmomatic)--> clean reads --(megahit)--> contigs --(virsorter2,genomad,virfinder,vibrant)--> vcontig  --(checkv clustering)--> vOTU --(classify workflow)--> tax --(bowtie2,samtools+cleanreads)--> abundance -- compare with database(based on tax) --> pathogenic virus -->  reports
#risk index calculate
.......

#prokaryotes risk
raw reads --(trimmomatic)--> clean reads --(megahit)--> contigs --(BASALT)--> bins --(checkm+drep)--> nrMH_MAGs --(gtdb-tk)--> tax --(coberm+cleanreads)--> abundance -- compare with database(drep 95% with database seqs) --> pathogenic MAGs --> reports
#risk index calculate
.......

#系统发育树验证
......
```
