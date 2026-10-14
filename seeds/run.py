"""python -m seeds.run --profile e2e"""

import argparse
from collections.abc import Callable

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.generated.db.models import Base
from seeds import e2e

PROFILES: dict[str, Callable[[], list[object]]] = {"e2e": e2e.build}


def reset(session: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(delete(table))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="seeds.run")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="e2e")
    args = parser.parse_args(argv)
    objects = PROFILES[args.profile]()
    with SessionLocal() as session, session.begin():
        reset(session)
        session.add_all(objects)
    print(f"seeded profile={args.profile} objects={len(objects)}")


if __name__ == "__main__":
    main()
