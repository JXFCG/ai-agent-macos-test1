#!/usr/bin/env python3
import subprocess
import sys
import time
import socket

# 配置项
POSTGRES_SERVICE = "postgres"
MYSQL_SERVICE = "mysql"
POSTGRES_PORT = 5432
MYSQL_PORT = 3306

def run_cmd(cmd, check=True, timeout=120):
    print(f"\n[命令] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        print(f"[错误] 命令失败: {cmd}\nstdout: {result.stdout}\nstderr: {result.stderr}")
        sys.exit(1)
    return result

def wait_for_port(host, port, max_retries=30, delay=2):
    """等待指定端口可连接"""
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

def main():
    print("=" * 60)
    print("开始 Docker Compose macOS 兼容性测试")
    print("=" * 60)

    # 检查 docker-compose 版本
    run_cmd("docker-compose version")

    # 只启动数据库服务（避免 ai-agent 问题）
    print("\n[启动] 启动数据库服务 (postgres 和 mysql)...")
    run_cmd("docker-compose up -d postgres mysql")

    # 等待端口可连接（宿主机映射端口）
    wait_for_port("localhost", POSTGRES_PORT)
    wait_for_port("localhost", MYSQL_PORT)

    # 额外等待几秒让数据库完全初始化
    time.sleep(5)

    # 测试 PostgreSQL 连接
    print("\n[验证] PostgreSQL 连接...")
    pg = run_cmd(
        f"docker-compose exec -T {POSTGRES_SERVICE} pg_isready -U postgres",
        check=False
    )
    if "accepting connections" not in pg.stdout:
        print(f"[失败] PostgreSQL 异常: {pg.stdout}")
        sys.exit(1)
    print("[成功] PostgreSQL 正常")

    # 测试 MySQL 连接
    print("\n[验证] MySQL 连接...")
    my = run_cmd(
        f"docker-compose exec -T {MYSQL_SERVICE} mysqladmin ping -h localhost -uroot -proot",
        check=False
    )
    if "mysqld is alive" not in my.stdout:
        print(f"[失败] MySQL 异常: {my.stdout}")
        sys.exit(1)
    print("[成功] MySQL 正常")

    print("\n✅ 所有测试通过！")

if __name__ == "__main__":
    main()
