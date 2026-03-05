import threading
import time
import subprocess
import os
import argparse
import re
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy

class TaskQueueService:
    def __init__(self, device_num):
        self.device_num = device_num
        self.current_tasks = []
        self.history_tasks = []
        self.envs = {}
        self.lock = threading.Lock()

    def _generate_id(self):
        return os.urandom(4).hex()

    def register_env(self, name, path):
        with self.lock:
            self.envs[name] = path
        return f"✅ 成功注册 Python 环境: {{{name}}} -> {path}"

    def show_envs(self):
        with self.lock:
            if not self.envs:
                return "⚠️ 当前未注册任何 Python 环境。"
            res = ["--- 已注册的 Python 环境 ---"]
            for k, v in self.envs.items():
                res.append(f"{{{k}}}: {v}")
            return "\n".join(res)

    def _parse_gpus(self, command):
        match = re.search(r'CUDA_VISIBLE_DEVICES\s*=\s*"?([0-9,]+)"?', command)
        if match:
            gpus_str = match.group(1)
            gpus = set(int(g.strip()) for g in gpus_str.split(',') if g.strip().isdigit())
            # 使用 in range 完美避开前端小于号解析 bug
            valid_gpus = {g for g in gpus if g in range(self.device_num)}
            if valid_gpus:
                return valid_gpus
        return set(range(self.device_num))

    def insert_task(self, base_dir, command, python_env):
        with self.lock:
            if python_env:
                if python_env not in self.envs:
                    return f"❌ 插入失败：未找到名为 '{python_env}' 的环境，请先使用 env_add 注册。"
                env_path = self.envs[python_env]
                target_str = f"{{{python_env}}}"
                if target_str in command:
                    command = command.replace(target_str, env_path, 1)

            gpus = self._parse_gpus(command)
            task_id = self._generate_id()
            task = {
                'id': task_id,
                'base_dir': base_dir,
                'command': command,
                'gpus': list(gpus),
                'status': 'pending',
                'pid': None
            }
            self.current_tasks.append(task)
        
        gpu_display = ",".join(map(str, sorted(gpus))) if len(gpus) != self.device_num else "ALL"
        return f"✅ 成功插入任务！\n任务 ID: {task_id}\n需求 GPU: [{gpu_display}]\n执行命令: {command}"

    def show_current(self):
        with self.lock:
            if not self.current_tasks:
                return "当前剩余任务列表为空，正在静默等待。"
            
            res = [f"--- 当前剩余任务 (集群共计 {self.device_num} 张卡) ---"]
            for t in self.current_tasks:
                status = t['status']
                gpu_display = ",".join(map(str, sorted(t['gpus']))) if len(t['gpus']) != self.device_num else "ALL"
                pid_info = f" [PID: {t['pid']}]" if status == 'running' and t['pid'] else ""
                marker = " 🟢 [正在执行]" if status == 'running' else " 🟡 [排队等待]"
                res.append(f"[{t['id']}]{marker}{pid_info} [GPU: {gpu_display}] {t['command']} (Dir: {t['base_dir']})")
            return "\n".join(res)

    def show_history(self):
        with self.lock:
            if not self.history_tasks:
                return "历史任务列表为空。"
            
            res = ["--- 历史任务记录 ---"]
            for t in self.history_tasks:
                gpu_display = ",".join(map(str, sorted(t['gpus']))) if len(t['gpus']) != self.device_num else "ALL"
                pid_info = f" [PID: {t['pid']}]" if t.get('pid') else ""
                res.append(f"[{t['id']}] [状态: {t['status']}]{pid_info} [GPU: {gpu_display}] {t['command']}")
            return "\n".join(res)

    def delete_task(self, task_id):
        with self.lock:
            for i, t in enumerate(self.current_tasks):
                if t['id'] == task_id:
                    if t['status'] == 'running':
                        return f"❌ 拒绝删除：任务 {task_id} 正在执行中 (PID: {t['pid']})。请在系统层面强行 kill 进程。"
                    del self.current_tasks[i]
                    return f"✅ 已从 [当前剩余任务] 中删除任务 {task_id}。"
            
            for i, t in enumerate(self.history_tasks):
                if t['id'] == task_id:
                    del self.history_tasks[i]
                    return f"✅ 已从 [历史任务记录] 中删除任务 {task_id}。"
            return f"⚠️ 未找到 ID 为 {task_id} 的任务。"

    def _run_single_task(self, task):
        try:
            expanded_dir = os.path.expanduser(task['base_dir'])
            process = subprocess.Popen(task['command'], shell=True, cwd=expanded_dir)
            
            task['pid'] = process.pid
            print(f"[Task Started] Task ID: {task['id']}, PID: {process.pid}", flush=True)
            
            process.wait()
            task['status'] = f"completed (code: {process.returncode})"
        except Exception as e:
            task['status'] = f"failed (error: {str(e)})"
            print(f"[Task Failed] Task ID: {task['id']}, Error: {str(e)}", flush=True)
        
        with self.lock:
            if task in self.current_tasks:
                self.current_tasks.remove(task)
            self.history_tasks.append(task)
            print(f"[Task Finished] Task ID: {task['id']}, Final Status: {task['status']}", flush=True)

    def run_worker(self):
        while True:
            with self.lock:
                running_tasks = [t for t in self.current_tasks if t['status'] == 'running']
                running_gpus = set()
                for t in running_tasks:
                    running_gpus.update(t['gpus'])
                
                available_gpus = set(range(self.device_num)) - running_gpus
                
                for task in self.current_tasks:
                    if task['status'] == 'pending':
                        req_gpus = set(task['gpus'])
                        
                        if req_gpus.issubset(available_gpus):
                            task['status'] = 'running'
                            available_gpus -= req_gpus
                            threading.Thread(target=self._run_single_task, args=(task,), daemon=True).start()
                        else:
                            available_gpus -= req_gpus

            time.sleep(2)

def start_server(port=9000, device_num=8):
    print("="*40, flush=True)
    print(f"Task Queue Server Started", flush=True)
    print(f"Server PID: {os.getpid()}", flush=True)
    print("="*40, flush=True)

    service = TaskQueueService(device_num)
    worker_thread = threading.Thread(target=service.run_worker, daemon=True)
    worker_thread.start()

    server = SimpleXMLRPCServer(("localhost", port), allow_none=True)
    server.register_instance(service)
    print(f"🚀 多卡调度服务已在端口 {port} 启动，监控 {device_num} 张 GPU，正在后台静默运行...\n", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="多 GPU 智能排队运行工具")
    subparsers = parser.add_subparsers(dest="action", help="选择操作")

    server_parser = subparsers.add_parser("server", help="启动常驻服务进程")
    server_parser.add_argument("--device_num", type=int, default=8, help="GPU 总数量")

    env_add_parser = subparsers.add_parser("env_add", help="注册 Python 环境")
    env_add_parser.add_argument("name", help="环境别名")
    env_add_parser.add_argument("path", help="Python 解释器绝对路径")
    subparsers.add_parser("env_list", help="显示已注册的 Python 环境")

    subparsers.add_parser("current", help="显示当前剩余任务")
    subparsers.add_parser("history", help="显示历史任务")
    
    add_parser = subparsers.add_parser("add", help="插入新的任务")
    add_parser.add_argument("--base_dir", required=True, help="运行目录")
    add_parser.add_argument("--command", required=True, help="命令行命令")
    add_parser.add_argument("--python", default="", help="使用预存的 Python 环境别名")

    del_parser = subparsers.add_parser("delete", help="根据 ID 删除任务")
    del_parser.add_argument("id", help="8位16进制任务ID")

    args = parser.parse_args()

    if args.action == "server":
        start_server(device_num=args.device_num)
    elif args.action:
        try:
            proxy = ServerProxy("http://localhost:9000")
            if args.action == "env_add":
                print(proxy.register_env(args.name, args.path))
            elif args.action == "env_list":
                print(proxy.show_envs())
            elif args.action == "current":
                print(proxy.show_current())
            elif args.action == "history":
                print(proxy.show_history())
            elif args.action == "add":
                print(proxy.insert_task(args.base_dir, args.command, args.python))
            elif args.action == "delete":
                print(proxy.delete_task(args.id))
        except ConnectionRefusedError:
            print("❌ 连接失败！请确认是否已经运行了: python task_queue.py server --device_num 8")
    else:
        parser.print_help()
