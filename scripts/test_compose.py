#!/usr/bin/env python3

import socket
import subprocess
import sys
import time


COMPOSE_CMD = "docker-compose"

POSTGRES_SERVICE = "postgres"
MYSQL_SERVICE = "mysql"

POSTGRES_PORT = 5432
MYSQL_PORT = 3306

POSTGRES_USER = "agent"
POSTGRES_DATABASE = "agent"

MYSQL_ROOT_PASSWORD = "rootsecret"


def run_cmd(cmd, check=True, timeout=180):
    print()
    print(f"[命令] {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        print(f"[错误] 命令超时: {cmd}")
        if check:
            sys.exit(1)
        return None

    if result.stdout:
        print(result.stdout.strip())

    if result.stderr:
        print(result.stderr.strip())

    if check and result.returncode != 0:
        print(f"[失败] 命令执行失败，退出码: {result.returncode}")
        sys.exit(result.returncode)

    return result


def wait_for_port(host, port, max_retries=60, delay=5):
    print()
    print(f"[等待] 等待 {host}:{port} 可连接...")

    for attempt in range(1, max_retries + 1):

        try:
            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            sock.settimeout(3)

            result = sock.connect_ex(
                (host, port)
            )

            sock.close()

            if result == 0:
                print(
                    f"[成功] {host}:{port} 已就绪"
                )
                return True

        except Exception as exc:
            print(
                f"[警告] 检查 {host}:{port} 发生异常: {exc}"
            )

        print(
            f"尝试 {attempt}/{max_retries}，"
            f"等待 {delay} 秒..."
        )

        time.sleep(delay)

    print(
        f"[失败] {host}:{port} 在规定时间内未就绪"
    )

    return False


def wait_for_postgres_ready(max_retries=40, delay=5):
    print()
    print("[等待] 等待 PostgreSQL 数据库就绪...")

    command = (
        f"{COMPOSE_CMD} exec -T "
        f"{POSTGRES_SERVICE} "
        f"pg_isready "
        f"-h 127.0.0.1 "
        f"-p 5432 "
        f"-U {POSTGRES_USER} "
        f"-d {POSTGRES_DATABASE}"
    )

    for attempt in range(1, max_retries + 1):

        result = run_cmd(
            command,
            check=False
        )

        if result and "accepting connections" in result.stdout:
            print("[成功] PostgreSQL 已就绪")
            return True

        print(
            f"PostgreSQL 尝试 "
            f"{attempt}/{max_retries}..."
        )

        time.sleep(delay)

    print("[失败] PostgreSQL 未就绪")

    return False


def wait_for_mysql_ready(max_retries=40, delay=5):
    print()
    print("[等待] 等待 MySQL 数据库就绪...")

    command = (
        f"{COMPOSE_CMD} exec -T "
        f"{MYSQL_SERVICE} "
        f"mysqladmin "
        f"ping "
        f"-h 127.0.0.1 "
        f"-uroot "
        f"-p{MYSQL_ROOT_PASSWORD} "
        f"--silent"
    )

    for attempt in range(1, max_retries + 1):

        result = run_cmd(
            command,
            check=False
        )

        if result and "mysqld is alive" in result.stdout:
            print("[成功] MySQL 已就绪")
            return True

        print(
            f"MySQL 尝试 "
            f"{attempt}/{max_retries}..."
        )

        time.sleep(delay)

    print("[失败] MySQL 未就绪")

    return False


def validate_postgres():
    print()
    print("[验证] PostgreSQL 最终连接测试...")

    command = (
        f"{COMPOSE_CMD} exec -T "
        f"{POSTGRES_SERVICE} "
        f"pg_isready "
        f"-h 127.0.0.1 "
        f"-p 5432 "
        f"-U {POSTGRES_USER} "
        f"-d {POSTGRES_DATABASE}"
    )

    result = run_cmd(
        command,
        check=False
    )

    if result and "accepting connections" in result.stdout:
        print("[成功] PostgreSQL 正常")
        return True

    print("[失败] PostgreSQL 最终验证失败")
    return False


def validate_mysql():
    print()
    print("[验证] MySQL 最终连接测试...")

    command = (
        f"{COMPOSE_CMD} exec -T "
        f"{MYSQL_SERVICE} "
        f"mysqladmin "
        f"ping "
        f"-h 127.0.0.1 "
        f"-uroot "
        f"-p{MYSQL_ROOT_PASSWORD} "
        f"--silent"
    )

    result = run_cmd(
        command,
        check=False
    )

    if result and "mysqld is alive" in result.stdout:
        print("[成功] MySQL 正常")
        return True

    print("[失败] MySQL 最终验证失败")
    return False


def main():

    print("=" * 60)
    print("Docker Compose macOS Compatibility Test")
    print("=" * 60)

    # --------------------------------------------------
    # 1. 检查 docker-compose
    # --------------------------------------------------

    run_cmd(
        f"{COMPOSE_CMD} --version"
    )

    # --------------------------------------------------
    # 2. 检查 Docker
    # --------------------------------------------------

    run_cmd(
        "docker --version"
    )

    run_cmd(
        "docker info",
        timeout=60
    )

    # --------------------------------------------------
    # 3. 清理旧容器
    # --------------------------------------------------

    print()
    print("[清理] 清理旧的 PostgreSQL / MySQL 容器...")

    run_cmd(
        f"{COMPOSE_CMD} down -v --remove-orphans",
        check=False
    )

    # --------------------------------------------------
    # 4. 启动 PostgreSQL + MySQL
    # --------------------------------------------------

    print()
    print(
        "[启动] 启动 PostgreSQL 和 MySQL..."
    )

    run_cmd(
        f"{COMPOSE_CMD} up -d postgres mysql"
    )

    # --------------------------------------------------
    # 5. 查看容器状态
    # --------------------------------------------------

    run_cmd(
        f"{COMPOSE_CMD} ps"
    )

    # --------------------------------------------------
    # 6. 等待端口
    # --------------------------------------------------

    if not wait_for_port(
        "127.0.0.1",
        POSTGRES_PORT
    ):
        sys.exit(1)

    if not wait_for_port(
        "127.0.0.1",
        MYSQL_PORT
    ):
        sys.exit(1)

    # --------------------------------------------------
    # 7. PostgreSQL ready
    # --------------------------------------------------

    if not wait_for_postgres_ready():
        print()
        print("[诊断] PostgreSQL 日志：")

        run_cmd(
            f"{COMPOSE_CMD} logs postgres",
            check=False
        )

        sys.exit(1)

    # --------------------------------------------------
    # 8. MySQL ready
    # --------------------------------------------------

    if not wait_for_mysql_ready():
        print()
        print("[诊断] MySQL 日志：")

        run_cmd(
            f"{COMPOSE_CMD} logs mysql",
            check=False
        )

        sys.exit(1)

    # --------------------------------------------------
    # 9. 最终验证
    # --------------------------------------------------

    postgres_ok = validate_postgres()

    mysql_ok = validate_mysql()

    # --------------------------------------------------
    # 10. 输出结果
    # --------------------------------------------------

    print()
    print("=" * 60)

    if postgres_ok and mysql_ok:

        print(
            "✅ Docker Compose macOS 兼容性测试通过"
        )

        print(
            "✅ PostgreSQL 正常"
        )

        print(
            "✅ MySQL 正常"
        )

        print("=" * 60)

        sys.exit(0)

    print(
        "❌ Docker Compose macOS 兼容性测试失败"
    )

    print("=" * 60)

    sys.exit(1)


if __name__ == "__main__":
    main()
