#!/usr/bin/env python3
"""Vitals Explorer launcher.

    python main.py

Creates the MySQL database and table if needed, fills them with sample data on
the first run, then starts the web app and opens it in your browser.
"""
import argparse
import getpass
import sys
import threading
import webbrowser


def _require_dependencies() -> None:
    missing = []
    for module, package in (
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pymysql", "PyMySQL"),
        ("cryptography", "cryptography"),  # MySQL 8 login (caching_sha2_password)
    ):
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        print(f"Missing Python packages: {', '.join(missing)}")
        print("Install everything with:  pip install -r requirements.txt")
        sys.exit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vitals Explorer")
    parser.add_argument("--reseed", action="store_true",
                        help="delete all readings and generate fresh sample data")
    parser.add_argument("--no-browser", action="store_true",
                        help="do not open the browser automatically")
    parser.add_argument("--host", help="address to listen on (default 127.0.0.1)")
    parser.add_argument("--port", type=int, help="port to listen on (default 8000)")
    return parser.parse_args()


def main() -> None:
    _require_dependencies()
    args = _parse_args()

    import pymysql
    import uvicorn

    try:
        from app.config import settings
        from app import database
    except ValueError as exc:  # invalid value in .env / environment
        print(f"Configuration error: {exc}")
        sys.exit(1)

    if args.host:
        settings.app_host = args.host
    if args.port:
        settings.app_port = args.port

    # 1) Connect to MySQL and create the database (asks for the password if needed).
    password_attempts = 0
    while True:
        try:
            database.ensure_database()
            break
        except pymysql.err.OperationalError as exc:
            code = exc.args[0] if exc.args else None
            if code == 1045 and sys.stdin.isatty() and password_attempts < 3:
                password_attempts += 1
                settings.mysql_password = getpass.getpass(
                    f"MySQL password for '{settings.mysql_user}'@'{settings.mysql_host}': "
                )
                continue
            print("\nCould not connect to MySQL.")
            print(f"  Server : {settings.mysql_host}:{settings.mysql_port}")
            print(f"  User   : {settings.mysql_user}")
            print(f"  Reason : {exc}")
            print("\nCheck that MySQL is running and set the right credentials in a .env file")
            print("(copy .env.example to .env) or in the MYSQL_* environment variables.")
            sys.exit(1)

    # 2) Table and sample data.
    try:
        database.ensure_schema()
        count, inserted = database.seed_if_needed(reseed=args.reseed)
    except pymysql.MySQLError as exc:
        print(f"\nDatabase setup failed: {exc}")
        sys.exit(1)

    if inserted:
        print(f"Generated {count} sample readings (20.09.2026 20:10 to 21.09.2026 08:10).")
    else:
        print(f"Database '{settings.mysql_database}' already holds {count} readings. "
              "Use --reseed to regenerate them.")

    # 3) Start the web app.
    shown_host = "localhost" if settings.app_host in ("0.0.0.0", "::") else settings.app_host
    url = f"http://{shown_host}:{settings.app_port}"
    print(f"\nVitals Explorer is running at {url}  (press Ctrl+C to stop)\n")
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()

    from app.api import app as fastapi_app

    try:
        uvicorn.run(fastapi_app, host=settings.app_host, port=settings.app_port, log_level="info")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
