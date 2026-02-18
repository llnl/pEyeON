from alive_progress import alive_bar, alive_it
from typing import Any

from loguru import logger
from .observe import Observe
import os
import duckdb
import time
from importlib.resources import files
import threading # allows the monitor to run concurrently without blocking multiprocessing 
from multiprocessing import Pool, Manager


class Parse:
    """
    General parser for eyeon. Given a folder path, will return a list of observations.

    Parameters
    ----------

    dirpath : str
        A string specifying the folder to parse.
    """

    def __init__(self, dirpath: str) -> None:
        self.path = dirpath

    def _observe(self, file_and_path: tuple) -> None:
        file, result_path = file_and_path
        try:
            o = Observe(file)
            o.write_json(result_path)
        except PermissionError:
            logger.warning(f"File {file} cannot be read.")
        except FileNotFoundError:
            logger.warning(f"No such file {file}.")

    def _observe_worker(self, args) -> None:
        """
        wrapper to handle and monitor observe workers. 
        Assists in identifying problematic files

        :param args: (file: str, result_path: str, progress_map: dict) 
        """

        file, result_path, progress_map = args

        pid= os.getpid()
        start_time=time.time()

        progress_map[pid] = {
            "file": file,
            "start": start_time,
        }

        try:
            self._observe((file, result_path))
        finally:
            # Clear the entry when done or on error
            progress_map.pop(pid, None)


    def __call__(self, result_path: str = "./results", threads: int = 1) -> Any:
        with alive_bar(
            bar=None,
            elapsed_end=False,
            monitor_end=False,
            stats_end=False,
            receipt_text=True,
            spinner="waves",
            stats=False,
            monitor=False,
        ) as bar:
            bar.title("Collecting Files... ")
            files = [
                (os.path.join(dir, file), result_path)
                for dir, _, files in os.walk(self.path)
                for file in files
            ]
            bar.title("")
            bar.text(f"{len(files)} files collected")

        if threads > 1:
            manager=Manager()
            progress_map= manager.dict()

            def monitor():
                CHECK_INTERVAL=30 #seconds between checks
                HANG_THRESHOLD=120

                while True:
                    now = time.time()
                    workers=list(progress_map.items())
                    if not workers:
                        continue
                        
                    for pid, info in workers:
                        file=info.get("file")
                        start=info.get("start", now)
                        duration=now-start
                        if duration > HANG_THRESHOLD:
                            logger.warning(
                                f"[monitor] - possible hung process: pid={pid} processing {file} for {duration:.1f}s"
                            )
                    
                    time.sleep(CHECK_INTERVAL) #sleep so it's not infinitely spinning

            monitor_thread = threading.Thread(target=monitor, daemon=True) #run monitor thread in the background, removes when finished
            monitor_thread.start()


            with Pool(threads) as p:
                with alive_bar(
                    len(files), 
                    spinner="waves", 
                    title=f"Parsing with {threads} threads..."
                ) as bar:
                    # each worker gets the file, result_path, and the shared progress_map
                    iterable = [
                        (file, result_path, progress_map) for (file, result_path) in files
                    ]
                    for _ in p.imap_unordered(self._observe_worker, iterable):
                        bar()  # update the bar when a thread finishes

        else:
            #Single process path (no inter‑process monitoring needed)
            for filet in alive_it(files, spinner="waves", title="Parsing files..."):
                self._observe(filet)

    def write_database(self, database: str, outdir: str = "./results") -> None:
        """
        Parse all output json files and add to database

        Parameters
        ----------
            database : str
                The filepath to the duckdb database
            outdir : str
                A string specifying where results were saved
        """
        if os.path.exists(outdir) and database:
            try:
                with alive_bar(
                    bar=None,
                    elapsed_end=False,
                    monitor_end=False,
                    stats_end=False,
                    receipt_text=True,
                    spinner="waves",
                    stats=False,
                    monitor=False,
                ) as bar:
                    bar.title(f"Writing to database {database}")
                    db_exists = os.path.exists(database)
                    db_path = os.path.dirname(database)
                    if db_path:
                        os.makedirs(db_path, exist_ok=True)
                    con = duckdb.connect(database)  # creates or connects
                    if not db_exists:  # database exists, load the json file in
                        # create table and views from sql
                        con.sql(files("database").joinpath("eyeon-ddl.sql").read_text())

                    # add the file to the observations table, making it match template
                    # observations with missing keys keys with null
                    con.sql(
                        f"""
                    insert into observations by name
                    select * from
                    read_json_auto(['{outdir}/*.json',
                                    '{files('database').joinpath('observations.json')}'],
                                    union_by_name=true, auto_detect=true)
                    where filename is not null;
                    """
                    )
                    bar.title("")
                    bar.text("Database updated")
                    con.close()
            except duckdb.IOException as ioe:
                con = None
                s = f":exclamation: Failed to attach to db {database}: {ioe}"
                print(s)
        else:
            raise FileNotFoundError
