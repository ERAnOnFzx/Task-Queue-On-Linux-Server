# Task-Queue-On-Linux-Server
A zero-dependency, lightweight GPU task queue with native Shadow Reservation scheduling. 极简零依赖的深度学习多卡调度队列，原生支持影子预占防阻塞算法。


# LiteGPUTQ (Lite GPU Task Queue)

---

<h2 id="中文版"> 🇨🇳 中文版</h2>

**LiteGPUTQ** 是一个极简、零依赖的轻量级 GPU 多卡任务队列与调度服务。原生实现了**“影子预占 (Shadow Reservation)”**调度算法，完美解决多任务间的 GPU 资源抢占与阻塞问题。

### ✨ 核心特性
- **🚀 零依赖**：仅使用 Python 标准库，无需 pip install，下载即用。
- **🧠 影子预占调度**：严格遵循 FIFO 优先级，防止小任务恶意插队抢占大任务的资源。
- **🐍 虚拟环境管理**：支持注册多个 Python 解释器，提交任务时一键别名调用。
- **📊 进程追踪**：自动记录任务 PID，支持使用 top 或 kill 进行系统级干预。

### 🛠️ 快速开始

#### 1. 启动常驻调度服务
（注意：建议启动时将输出重定向到日志文件中，可方便后续查看 PID 和报错）
```bash
nohup python task_queue.py server --device_num 8 > queue_server.log 2>&1 &
```

#### 2. 注册环境与提交任务
```bash
python task_queue.py env_add my_env /home/user/miniconda3/envs/my_env/bin/python
python task_queue.py add --base_dir "~/my_project" --command "CUDA_VISIBLE_DEVICES=0,1 {my_env} train.py" --python my_env
```

#### 3. 查看队列状态
```bash
python task_queue.py current
python task_queue.py history
```

---

<h2 id="english-version"> 🇬🇧 English Version</h2>

**LiteGPUTQ** is a minimalist, zero-dependency GPU task queue. It natively implements the **Shadow Reservation** scheduling algorithm, resolving GPU resource contention and blocking issues gracefully.

### 🛠️ Quick Start
#### Start the resident daemon service:
```bash
nohup python task_queue.py server --device_num 8 > queue_server.log 2>&1 &
```

#### Submit a task (environment parsing supported):
```bash
python task_queue.py env_add my_env /home/user/miniconda3/envs/my_env/bin/python
python task_queue.py add --base_dir "~/my_project" --command "CUDA_VISIBLE_DEVICES=0,1 {my_env} train.py" --python my_env
```

#### Check the queue status
```bash
python task_queue.py current
python task_queue.py history
```
|||bash
python task_queue.py add --base_dir "~/my_project" --command "CUDA_VISIBLE_DEVICES=0,1 python train.py"
|||
