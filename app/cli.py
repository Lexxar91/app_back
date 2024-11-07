from dotenv import load_dotenv
import os
import pathlib
from typing import Optional, Tuple

import pandas as pd
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
import tqdm
import typer
from typing_extensions import Annotated

from app.models import Ownership, Patent, Person
from app.parsers import OwnershipParser, PatentParser, PersonParser


CHUNKSIZE = 1e3

load_dotenv()

app = typer.Typer()
db_url = os.getenv("DATABASE_CLI_URL")
engine = create_engine(db_url)


def _ensure_proceed(model_cls):
    stmt = select(func.count()).select_from(model_cls)

    with Session(engine) as session:
        cnt = session.execute(stmt).scalar()

    if cnt > 0:
        print(
            f"{model_cls.__name__} table already contains {cnt} records."
            " Are you sure you want to continue?"
            " New records will be added, existing will be preserved.\n"
            " y = yes, any other = exit"
        )
        task = input().strip()
        if task != "y":
            print("Okay, bye")
            return False

    return True


def _process_file(
    filename: pathlib.Path,
    model_cls,
    parser_cls,
    commit_every: int = 1e3,
):
    if not _ensure_proceed(model_cls):
        return

    print(f"Loading data from file {filename} to {model_cls.__name__} table")

    parser = parser_cls(filename)
    if not parser.setup():
        print("Incorrect input file")
        return

    success, error = 0, 0
    with Session(engine) as session:
        for i, item in enumerate(tqdm.tqdm(parser.parse())):
            if item is None:
                continue

            record = model_cls(**item)
            session.add(record)

            if i > 0 and i % commit_every == 0:
                try:
                    session.commit()
                    success += 1 * commit_every
                except Exception as e:
                    session.rollback()
                    print(f"Error while trying to insert portion #{i} of data to table: {e}")
                    error += 1 * commit_every

        try:
            session.commit()
            success += 1 * commit_every
        except Exception as e:
            session.rollback()
            print(f"Error while trying to insert portion #{i} of data to table: {e}")
            error += 1 * commit_every

    print("Completed")
    print(f"Inserted {success} records, failed to insert {error} records")


@app.command("load-patents")
def cli_load_patents(
    input_file: Annotated[
        pathlib.Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False
        )
    ]
):
    _process_file(input_file, Patent, PatentParser)


@app.command("load-persons")
def cli_load_persons(
    input_file: Annotated[
        pathlib.Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False
        )
    ]
):
    _process_file(input_file, Person, PersonParser)


@app.command("load-ownership")
def cli_load_ownership(input_file: str):
    _process_file(input_file, Ownership, OwnershipParser, commit_every=1)


if __name__ == "__main__":
    app()
