# Task-Queue-On-Linux-Server
A zero-dependency, lightweight GPU task queue with native Shadow Reservation scheduling. 极简零依赖的深度学习多卡调度队列，原生支持影子预占防阻塞算法。

[中文版](#中文版) | [English Version](#english-version)

---

<h2 id="中文版"> 🇨🇳 中文版</h2>

**Task-Queue-On-Linux-Server** 是一个极简、零依赖的轻量级 GPU 多卡任务队列与调度服务。原生实现了**影子预占 (Shadow Reservation)**调度算法，完美解决多任务间的 GPU 资源抢占与阻塞问题。

### ✨ 核心特性
- **🚀 零依赖**：仅使用 Python 标准库，无需 pip install，下载即用。
- **🧠 影子预占调度**：严格遵循 FIFO 优先级。当大型任务等待资源时，会自动预占所需显卡，防止小型任务恶意插队。
- **🐍 虚拟环境管理**：支持注册多个 Python 解释器或执行路径，一键别名调用，告别冗长的绝对路径。
- **📊 进程级追踪**：自动记录并展示任务真实的系统 PID，支持系统级干预。

### 🛠️ 快速开始

#### 1. 启动常驻调度服务
建议将输出重定向到日志文件中，方便后续查看服务状态和报错：
```bash
nohup python task_queue.py server --device_num 8 > queue_server.log 2>&1 &
```

#### 2. 环境管理 (注册与查看)
你可以将常用的 Python 环境注册进工具中：
```bash
# 注册常规 Python 环境
python task_queue.py env_add pangu_env /home/user/miniconda3/envs/pangu_env/bin/python

# 你也可以直接把 torchrun 的绝对路径注册为一个“环境别名”
python task_queue.py env_add pangu_torchrun /home/user/miniconda3/envs/pangu_env/bin/torchrun

# 查看当前所有已注册的环境
python task_queue.py env_list
```

#### 3. 提交任务 (Add)
使用 `--python` 参数调用预先注册的环境，系统会自动解析命令中的 `CUDA_VISIBLE_DEVICES` 分配卡位：

**普通单卡/多卡 Python 任务：**
```bash
python task_queue.py add \
  --base_dir "~/my_project" \
  --command "CUDA_VISIBLE_DEVICES=0,1 {pangu_env} train.py > train.log 2>&1" \
  --python pangu_env
```

**🔥 高阶用法：提交 torchrun 分布式任务 (2 种方式)：**
由于直接写全局的 `torchrun` 会导致找不到虚拟环境里的包，你有两种优雅的解决方案：

*方式一：使用 -m 模块调用 (推荐)*
```bash
python task_queue.py add \
  --base_dir "~/LLMMoEfication/LTE_reproduce" \
  --command "CUDA_VISIBLE_DEVICES=4,5,6,7 {pangu_env} -m torch.distributed.run --nproc_per_node=4 main_finetune_Pangu.py --dataset xsum > train0305.log 2>&1" \
  --python pangu_env
```

*方式二：直接调用刚才注册的 torchrun 别名*
```bash
python task_queue.py add \
  --base_dir "~/LLMMoEfication/LTE_reproduce" \
  --command "CUDA_VISIBLE_DEVICES=4,5,6,7 {pangu_torchrun} --nproc_per_node=4 main_finetune_Pangu.py --dataset xsum > train0305.log 2>&1" \
  --python pangu_torchrun
```
*(注：强烈建议在 command 末尾加上 `> log.txt 2>&1`，这样无论程序正常输出还是 OOM 崩溃，所有的信息都会被完整保存。)*

#### 4. 查看队列与删除任务
```bash
# 查看当前正在运行和排队中的任务 (会显示 PID 和占用的 GPU)
python task_queue.py current

# 查看已完成/失败的历史任务归档 (会显示 Exit Code)
python task_queue.py history

# 从排队队列或历史记录中删除指定任务 (根据 8 位 ID)
python task_queue.py delete 8f4b2a1c
```
**⚠️ 强杀任务提醒：** 正在运行中的任务无法通过 delete 删除。若需强行终止，请在 current 面板查看其 PID，并使用系统命令 `kill -9 <PID>`，调度器会自动捕获中断。

---

<h2 id="english-version"> 🇬🇧 English Version</h2>

**Task-Queue-On-Linux-Server** is a minimalist, zero-dependency GPU task queue. It natively implements the **Shadow Reservation** scheduling algorithm, resolving GPU resource contention gracefully.

### 🛠️ Quick Start

**1. Start the resident daemon service:**
```bash
nohup python task_queue.py server --device_num 8 > queue_server.log 2>&1 &
```

**2. Manage Environments (Include torchrun):**
```bash
python task_queue.py env_add my_env /home/user/miniconda3/envs/my_env/bin/python
python task_queue.py env_add my_torchrun /home/user/miniconda3/envs/my_env/bin/torchrun
python task_queue.py env_list
```

**3. Submit a standard Python task:**
```bash
python task_queue.py add \
  --base_dir "~/my_project" \
  --command "CUDA_VISIBLE_DEVICES=0,1 {my_env} train.py > train.log 2>&1" \
  --python my_env
```

**4. Submit a Distributed Task (`torchrun`):**
To avoid path conflicts, use the `-m` flag with your Python environment or use the registered `torchrun` alias:
```bash
python task_queue.py add \
  --base_dir "~/LLMMoEfication/LTE_reproduce" \
  --command "CUDA_VISIBLE_DEVICES=4,5,6,7 {my_torchrun} --nproc_per_node=4 main_finetune.py > train.log 2>&1" \
  --python my_torchrun
```

**5. Manage Tasks (Check & Delete):**
```bash
python task_queue.py current
python task_queue.py history
python task_queue.py delete 8f4b2a1c
```
*(Note: To kill a "running" task, find its PID in the `current` list and use `kill -9 <PID>` in your OS terminal.)*
|||
*(Note: To kill a "running" task, find its PID in the `current` list and use `kill -9 <PID>` in your OS terminal.)*
