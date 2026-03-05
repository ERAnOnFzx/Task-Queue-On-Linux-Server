# Task-Queue-On-Linux-Server
A zero-dependency, lightweight GPU task queue with native Shadow Reservation scheduling. 极简零依赖的深度学习多卡调度队列，原生支持影子预占防阻塞算法。

[中文版](#中文版) | [English Version](#english-version)

---

<h2 id="中文版"> 🇨🇳 中文版</h2>

**Task-Queue-On-Linux-Server** 是一个极简、零依赖的轻量级 GPU 多卡任务队列与调度服务。它原生实现了**“影子预占 (Shadow Reservation)”**调度算法，完美解决实验室/多任务集群中的 GPU 资源抢占、排队插队与饿死问题。

### ✨ 核心特性
- **🚀 零依赖**：仅使用 Python 标准库，无需 `pip install`，下载即用。
- **🧠 影子预占调度**：严格遵循 FIFO 优先级。大型任务等待资源时会预占显卡，防止小型任务恶意插队。
- **🐍 虚拟环境管理**：支持注册多个 Python / torchrun 路径，一键别名调用，告别冗长绝对路径。
- **📊 进程级追踪**：自动记录真实 PID，完美衔接 Linux 原生的 `top` 监控与 `kill` 管理。

---

### 🎬 核心场景推演：自动接力与影子预占

假设你有一台 **8 卡服务器 (GPU 0~7)**，我们来看看 Task-Queue-On-Linux-Server 是如何极其智能地管理队列的：

#### 🕒 [时间点 T0]：提交任务
你依次提交了 4 个任务：
1. **任务 A** (占用 `GPU 0,1,2,3`) -> 🟢 资源充足，**立即运行**。
2. **任务 B** (占用 `GPU 4,5,6,7`) -> 🟢 资源充足，**立即运行**。
3. **任务 C** (需要 `ALL` 全部 8 张卡) -> 🟡 资源不足，**排队等待**（此时任务 C 开始**影子预占**所有 8 张卡）。
4. **任务 D** (占用 `GPU 0,1`) -> 🟡 前方有任务 C 预占了全部卡位，尽管它只需要 2 张卡，也必须**排队等待**（严格防插队）。

此时，使用 `python task_queue.py current` 看到的面板是：
```text
--- 当前剩余任务 (集群共计 8 张卡) ---
[task_A] 🟢 [正在执行] [PID: 1001] [GPU: 0,1,2,3] train_A.py ...
[task_B] 🟢 [正在执行] [PID: 1002] [GPU: 4,5,6,7] train_B.py ...
[task_C] 🟡 [排队等待] [GPU: ALL] train_C.py ...
[task_D] 🟡 [排队等待] [GPU: 0,1] train_D.py ...
```

#### 🕒 [时间点 T1]：任务 A 执行完毕
系统自动回收 `GPU 0,1,2,3`。
调度器开始扫描：
* 任务 C 需要 8 张卡，但任务 B 还在用后 4 张，资源仍不够。继续等待。
* 任务 D 虽然只需要 `GPU 0,1`（现在刚好空闲），但因为任务 C 排在前面并“影子预占”了这些卡，任务 D **依然被阻塞**。
* **结果：** 完美保护了任务 C 不被饿死！

#### 🕒 [时间点 T2]：任务 B 执行完毕
系统自动回收 `GPU 4,5,6,7`。此时 8 张卡全部空闲！
* 调度器扫描到任务 C 资源满足，**自动顶上运行任务 C**！

#### 🕒 [时间点 T3]：任务 C 执行完毕
8 张卡再次释放。
* 调度器扫描到队列最后的任务 D，资源满足，**自动顶上运行任务 D**！

**整个过程无人值守，显卡利用率最大化，且绝对公平！**

---

### 🛠️ 快速开始

#### 1. 启动常驻调度服务
建议将输出重定向到日志文件中，方便后续查看服务状态和报错：
```bash
nohup python task_queue.py server --device_num 8 > queue_server.log 2>&1 &
```

#### 2. 环境管理 (注册与查看)
你可以将常用的虚拟环境或执行路径注册进工具中：
```bash
# 注册常规 Python 环境
python task_queue.py env_add pangu_env /home/user/miniconda3/envs/pangu_env/bin/python

# 注册 torchrun 环境 (针对分布式训练)
python task_queue.py env_add pangu_torchrun /home/user/miniconda3/envs/pangu_env/bin/torchrun
```

#### 3. 提交任务 (Add)
系统会自动解析命令中的 `CUDA_VISIBLE_DEVICES` 分配卡位。如果不写，默认占用全卡。
强烈建议在命令末尾加上 `> xxx.log 2>&1`，确保正常输出和 OOM 报错都能被记录。

**普通单卡/多卡 Python 任务：**
```bash
python task_queue.py add \
  --base_dir "~/my_project" \
  --command "CUDA_VISIBLE_DEVICES=0,1 {pangu_env} train.py > train.log 2>&1" \
  --python pangu_env
```

**分布式大模型微调 (torchrun)：**
```bash
python task_queue.py add \
  --base_dir "~/LLMMoEfication/LTE_reproduce" \
  --command "CUDA_VISIBLE_DEVICES=4,5,6,7 {pangu_torchrun} --nproc_per_node=4 main_finetune_Pangu.py --dataset xsum > train0305.log 2>&1" \
  --python pangu_torchrun
```

#### 4. 查看队列与删除任务
```bash
# 查看排队队列 (显示 PID 与卡位占用)
python task_queue.py current

# 查看历史归档 (显示退出状态码)
python task_queue.py history

# 删除指定排队任务
python task_queue.py delete 8f4b2a1c
```
**⚠️ 强杀任务提醒：** 正在 `🟢 [正在执行]` 的任务无法通过 delete 删除。若需强行终止，请根据 current 面板显示的 PID，直接使用系统命令 `kill -9 <PID>`，调度器会自动捕获该中断并推进下一个任务。

---

<h2 id="english-version"> 🇬🇧 English Version</h2>

**Task-Queue-On-Linux-Server** is a minimalist, zero-dependency GPU task queue. It natively implements the **Shadow Reservation** scheduling algorithm, preventing resource starvation and unfair line-jumping in multi-tenant deep learning clusters.

### 🎬 Core Scenario: Auto-Relay & Shadow Reservation

Imagine an **8-GPU server (GPU 0-7)**. You submit 4 tasks:
1. **Task A** (`GPU 0-3`) -> 🟢 Starts immediately.
2. **Task B** (`GPU 4-7`) -> 🟢 Starts immediately.
3. **Task C** (`ALL GPUs`) -> 🟡 Queued (Starts "Shadow Reserving" all 8 GPUs).
4. **Task D** (`GPU 0-1`) -> 🟡 Queued (Blocked by Task C's shadow reservation, preventing line-jumping).

**The Timeline:**
* **T1 (Task A finishes):** GPUs 0-3 are free. Task C still waits for GPUs 4-7. Task D is perfectly blocked by Task C's shadow reservation. Task C won't starve!
* **T2 (Task B finishes):** GPUs 4-7 are free. 8 GPUs are fully available. The queue manager automatically pops and **starts Task C**!
* **T3 (Task C finishes):** GPUs are freed. The manager automatically pops and **starts Task D**!
*Fully unattended, maximum GPU utilization, and strictly fair.*

### 🛠️ Quick Start

**1. Start the daemon:**
```bash
nohup python task_queue.py server --device_num 8 > queue_server.log 2>&1 &
```

**2. Manage Environments:**
```bash
python task_queue.py env_add my_env /home/user/miniconda3/envs/my_env/bin/python
python task_queue.py env_add my_torchrun /home/user/miniconda3/envs/my_env/bin/torchrun
```

**3. Submit Tasks (`> log.txt 2>&1` is highly recommended for tracking OOM errors):**
```bash
# Standard Task
python task_queue.py add \
  --base_dir "~/my_project" \
  --command "CUDA_VISIBLE_DEVICES=0,1 {my_env} train.py > train.log 2>&1" \
  --python my_env

# Distributed task using torchrun
python task_queue.py add \
  --base_dir "~/LLMMoEfication/LTE_reproduce" \
  --command "CUDA_VISIBLE_DEVICES=4,5,6,7 {my_torchrun} --nproc_per_node=4 main_finetune_Pangu.py > train.log 2>&1" \
  --python my_torchrun
```

**4. Monitor & Manage:**
```bash
python task_queue.py current
python task_queue.py history
python task_queue.py delete 8f4b2a1c
```
*(Note: To kill a `Running` task, find its PID in the `current` panel and use `kill -9 <PID>` in your OS terminal.)*
