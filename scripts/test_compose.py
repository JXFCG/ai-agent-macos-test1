#!/usr/bin/env python3


import subprocess
import sys
import time
import socket



POSTGRES_SERVICE = "postgres"

MYSQL_SERVICE = "mysql"


POSTGRES_PORT = 5432

MYSQL_PORT = 3306



POSTGRES_USER = "agent"

MYSQL_ROOT_PASSWORD = "rootsecret"



def run_cmd(cmd, check=True, timeout=120):

    print(f"\n[命令] {cmd}")


    result = subprocess.run(

        cmd,

        shell=True,

        capture_output=True,

        text=True,

        timeout=timeout

    )


    if result.stdout:

        print(result.stdout)


    if result.stderr:

        print(result.stderr)



    if check and result.returncode != 0:

        print("[失败] 命令执行失败")

        sys.exit(1)


    return result





def wait_for_port(host, port, retries=60):


    print(
        f"[等待] 检查 {host}:{port}"
    )


    for i in range(retries):

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
                f"[成功] {host}:{port} 已打开"
            )

            return True



        print(

            f"等待 {i+1}/{retries}"

        )


        time.sleep(5)



    print(

        f"[失败] {host}:{port}"

    )


    sys.exit(1)







def wait_postgres():


    print(

        "\n[等待] PostgreSQL"

    )



    for i in range(30):


        result = run_cmd(

            f"docker compose exec -T {POSTGRES_SERVICE} "
            f"pg_isready -U {POSTGRES_USER}",

            check=False

        )



        if "accepting connections" in result.stdout:


            print(

                "[成功] PostgreSQL ready"

            )

            return



        time.sleep(5)



    print(

        "[失败] PostgreSQL"

    )

    sys.exit(1)







def wait_mysql():


    print(

        "\n[等待] MySQL"

    )



    for i in range(30):


        result = run_cmd(

            f"docker compose exec -T {MYSQL_SERVICE} "
            f"mysqladmin ping "
            f"-uroot "
            f"-p{MYSQL_ROOT_PASSWORD}",

            check=False

        )



        if "mysqld is alive" in result.stdout:


            print(

                "[成功] MySQL ready"

            )

            return



        time.sleep(5)



    print(

        "[失败] MySQL"

    )

    sys.exit(1)







def main():


    print("="*60)

    print(

        "Docker Compose macOS Compatibility Test"

    )

    print("="*60)



    run_cmd(

        "docker compose version"

    )



    print(

        "\n[启动] docker compose"

    )



    run_cmd(

        "docker compose up -d postgres mysql"

    )



    wait_for_port(

        "localhost",

        POSTGRES_PORT

    )


    wait_for_port(

        "localhost",

        MYSQL_PORT

    )



    wait_postgres()


    wait_mysql()



    print(

        "\n=========================="

    )

    print(

        "✅ 所有测试通过"

    )

    print(

        "=========================="

    )






if __name__ == "__main__":

    main()
