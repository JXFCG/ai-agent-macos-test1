#!/usr/bin/env python3
import subprocess
import sys
import time
import requests

# 配置项
AGENT_HEALTH_URL = "http://localhost:8080/health"
POSTGRES_SERVICE = "postgres"
MYSQL_SERVICE = "mysql"
AGENT_SERVICE = "agent"
MOUNT_TEST_FILE = "/app/data/persist_test.txt"

def run_cmd(cmd, check=True, timeout=120):
    print(f"\n[命令] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        print(f"[错误] 命令失败: {cmd}\nstdout: {result.stdout}\nstderr: {result.stderr}")
        sys.exit(1)
    return result

def wait_for_http(url, max_retries=12, delay=5):
    print(f"[等待] 等待 {url} 返回 200...")
    for i in range(max_retries):
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                print(f"[成功] {url} 返回 200")
                return True
        except Exception:
            pass
        time.sleep(delay)
    print(f"[失败] {url} 未就绪")
    sys.exit(1)

def wait_for_container_healthy(service, max_retries=12, delay=5):
    print(f"[等待] 等待容器 {service} 健康...")
    for i in range(max_retries):
        result = run_cmd(f"docker inspect --format='{{{{.State.Health.Status}}}}' {service}", check=False)
        status = result.stdout.strip().strip("'")
        if status == "healthy":
            print(f"[成功] 容器 {service} 健康")
            return True
        time.sleep(delay)
    print(f"[失败] 容器 {service} 未达到健康状态")
    sys.exit(1)

def main():
    print("=" * 60)
    print("开始 Docker Compose macOS 兼容性测试")
    print("=" * 60)

    run_cmd("docker compose version")
    run_cmd("docker compose up -d")

    # 等待数据库健康
    wait_for_container_healthy(POSTGRES_SERVICE)
    wait_for_container_healthy(MYSQL_SERVICE)
    # 等待 Agent HTTP
    wait_for_http(AGENT_HEALTH_URL)

    # 数据库连接测试
    print("\n[验证] PostgreSQL 连接...")
    pg = run_cmd(f"docker compose exec -T {POSTGRES_SERVICE} pg_isready -U agent -d agent", check=False)
    if "accepting connections" not in pg.stdout:
        print(f"[失败] PostgreSQL 异常: {pg.stdout}")
        sys.exit(1)
    print("[成功] PostgreSQL 正常")

    print("\n[验证] MySQL 连接...")
    my = run_cmd(f"docker compose exec -T {MYSQL_SERVICE} mysqladmin ping -h localhost -uroot -prootsecret", check=False)
    if "mysqld is alive" not in my.stdout:
        print(f"[失败] MySQL 异常: {my.stdout}")
        sys.exit(1)
    print("[成功] MySQL 正常")

    # 数据持久化测试
    print("\n[验证] 数据持久化...")
    run_cmd(f"docker compose exec {AGENT_SERVICE} sh -c 'echo persist_test > {MOUNT_TEST_FILE}'")
    run_cmd(f"docker compose restart {AGENT_SERVICE}")
    wait_for_http(AGENT_HEALTH_URL, max_retries=6, delay=5)
    read = run_cmd(f"docker compose exec {AGENT_SERVICE} cat {MOUNT_TEST_FILE}", check=False)
    if "persist_test" not in read.stdout:
        print(f"[失败] 持久化验证失败: 文件内容 '{read.stdout}'")
        sys.exit(1)
    print("[成功] 数据持久化正常")

    print("\n✅ 所有测试通过！")

if __name__ == "__main__":
    main()
