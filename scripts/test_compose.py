#!/usr/bin/env python3
import subprocess
import sys
import time
import socket

# ===== 配置项（请根据您的 compose 修改） =====
POSTGRES_SERVICE = "postgres"
MYSQL_SERVICE = "mysql"
POSTGRES_PORT = 5432
MYSQL_PORT = 3306
# 如果 compose 中设置了 MYSQL_ROOT_PASSWORD，请填写；若无密码，保持为空字符串
MYSQL_ROOT_PASSWORD = "root"   # 改为您的实际密码，或留空

def run_cmd(cmd, check=True, timeout=120):
    print(f"\n[命令] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        print(f"[错误] 命令失败: {cmd}\nstdout: {result.stdout}\nstderr: {result.stderr}")
        sys.exit(1)
    return result

def wait_for_port(host, port, max_retries=30, delay=2):
    print(f"[等待] 等待 {host}:{port} 可连接...")
    for i in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(f"[成功] {host}:{port} 已就绪")
                return True
        except Exception:
            pass
        time.sleep(delay)
    print(f"[失败] {host}:{port} 未就绪")
    sys.exit(1)

def wait_for_postgres_ready(max_retries=20, delay=3):
    print(f"[等待] 等待 PostgreSQL 数据库就绪...")
    for i in range(max_retries):
        cmd = f"docker-compose exec -T {POSTGRES_SERVICE} pg_isready -h localhost -p 5432 -U postgres"
        result = run_cmd(cmd, check=False)
        if "accepting connections" in result.stdout:
            print(f"[成功] PostgreSQL 已就绪")
            return True
        print(f"尝试 {i+1}/{max_retries}: PostgreSQL 未就绪，等待 {delay} 秒...")
        time.sleep(delay)
    print(f"[失败] PostgreSQL 未就绪")
    sys.exit(1)

def wait_for_mysql_ready(max_retries=20, delay=3):
    print(f"[等待] 等待 MySQL 数据库就绪...")
    for i in range(max_retries):
        # 尝试无密码连接
        cmd = f"docker-compose exec -T {MYSQL_SERVICE} mysqladmin -h 127.0.0.1 -P 3306 -uroot ping"
        result = run_cmd(cmd, check=False)
        if "mysqld is alive" in result.stdout:
            print(f"[成功] MySQL 已就绪 (无密码)")
            return True
        # 如果有密码，尝试带密码
        if MYSQL_ROOT_PASSWORD:
            cmd2 = f"docker-compose exec -T {MYSQL_SERVICE} mysqladmin -h 127.0.0.1 -P 3306 -uroot -p{MYSQL_ROOT_PASSWORD} ping"
            result2 = run_cmd(cmd2, check=False)
            if "mysqld is alive" in result2.stdout:
                print(f"[成功] MySQL 已就绪 (使用密码)")
                return True
        print(f"尝试 {i+1}/{max_retries}: MySQL 未就绪，等待 {delay} 秒...")
        time.sleep(delay)
    print(f"[失败] MySQL 未就绪")
    sys.exit(1)

def main():
    print("=" * 60)
    print("开始 Docker Compose macOS 兼容性测试")
    print("=" * 60)

    run_cmd("docker-compose version")

    print("\n[启动] 启动数据库服务 (postgres 和 mysql)...")
    run_cmd("docker-compose up -d postgres mysql")

    wait_for_port("localhost", POSTGRES_PORT)
    wait_for_port("localhost", MYSQL_PORT)

    wait_for_postgres_ready()
    wait_for_mysql_ready()

    # 最终验证 PostgreSQL
    print("\n[验证] PostgreSQL 连接...")
    pg = run_cmd(
        f"docker-compose exec -T {POSTGRES_SERVICE} pg_isready -h localhost -p 5432 -U postgres",
        check=False
    )
    if "accepting connections" not in pg.stdout:
        print(f"[失败] PostgreSQL 异常: {pg.stdout}")
        sys.exit(1)
    print("[成功] PostgreSQL 正常")

    # 最终验证 MySQL
    print("\n[验证] MySQL 连接...")
    # 使用与等待循环相同的逻辑
    cmd = f"docker-compose exec -T {MYSQL_SERVICE} mysqladmin -h 127.0.0.1 -P 3306 -uroot ping"
    result = run_cmd(cmd, check=False)
    if "mysqld is alive" in result.stdout:
        print("[成功] MySQL 正常")
    elif MYSQL_ROOT_PASSWORD:
        cmd2 = f"docker-compose exec -T {MYSQL_SERVICE} mysqladmin -h 127.0.0.1 -P 3306 -uroot -p{MYSQL_ROOT_PASSWORD} ping"
        result2 = run_cmd(cmd2, check=False)
        if "mysqld is alive" in result2.stdout:
            print("[成功] MySQL 正常 (使用密码)")
        else:
            print(f"[失败] MySQL 异常: {result2.stdout}")
            sys.exit(1)
    else:
        print(f"[失败] MySQL 异常: {result.stdout}")
        sys.exit(1)

    print("\n✅ 所有测试通过！")

if __name__ == "__main__":
    main()
