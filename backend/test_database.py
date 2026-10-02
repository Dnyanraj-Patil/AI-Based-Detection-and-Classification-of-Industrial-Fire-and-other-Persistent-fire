from sqlalchemy import text

from app.db.database import engine


def main():
    print("Testing PostgreSQL connection...")

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT version();")
        )

        print("\nPostgreSQL:")
        print(result.scalar())

        result = connection.execute(
            text("SELECT PostGIS_Full_Version();")
        )

        print("\nPostGIS:")
        print(result.scalar())

    print("\nDATABASE CONNECTION: OK")


if __name__ == "__main__":
    main()