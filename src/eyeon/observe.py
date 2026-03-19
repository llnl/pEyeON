"""
eyeon.observe.Observe makes an observation of a file.
An observation will output a json file containing unique identifying information
such as hashes, modify date, certificate info, etc.
See the Observe class doc for full details.
"""

import datetime
import hashlib
import json
import os
import pprint
import subprocess
import threading

import re
import duckdb
from importlib.resources import files
from pathlib import Path
import pluggy
from surfactant.plugin.manager import get_plugin_manager
from surfactant.sbomtypes._software import Software
from queue import Queue
from uuid import uuid4

from loguru import logger


class Observe:
    """
    Class to create an Observation of a file.

    Parameters:
    -----------
        file (str): Path to file to be scanned.

    Required Attributes:
    ----------------------
        bytecount : int
            size of file
        filename : str
            File name
        magic : str
            Magic byte descriptor
        md5 : str
            ``md5sum`` of file
        modtime : str
            Datetime string of last modified time
        observation_ts : str
            Datetime string of time of scan
        permissions : str
            Octet string of file permission value
        sha1 : str
            ``sha1sum`` of file
        sha256 : str
            ``sha256sum`` of file
        ssdeep : str
            Fuzzy hash used by VirusTotal to match similar binaries.
        config : dict
            toml configuration file elements

    Optional Attributes:
    -----------------------
        compiler : str
            String describing compiler, compiler version, flags, etc.
        host : str
            csv string containing intended install locations
        imphash : str
            Import hash for Windows binaries
        telfhash : str
            Telfhash for ELF Linux binaries
        detect_it_easy : str
            Detect-It-Easy output.
        signatures : dict
            Descriptors of signature information, including signatures and certificates. Only
            valid for Windows
        metadata : dict
            Windows File Properties -- OS, Architecture, File Info, etc.
    """

    def __init__(self, file: str) -> None:
        logger.debug(f"initializing observe object for {file}")

        self.uuid = str(uuid4())
        stat = os.stat(file)
        self.bytecount = stat.st_size
        self.filename = os.path.basename(file)  # TODO: split into absolute path maybe?
        self.signatures = []
        # self.set_detect_it_easy(file)
        # surfactant stuff
        mgr = get_plugin_manager()
        self.filetype = mgr.hook.identify_file_type(filepath=file, context=None)

        if (self.filetype is None) or (self.filetype == []):
            logger.debug(f"Unknown file type for {file}")
            self.metadata = {
                "Unknown": {
                    "description": "some other file not in"
                    "{a.out, coff, docker image, elf, java, "
                    "js, mach-o, native lib, ole, pe, rpm, uboot image}"
                }
            }
        else:
            # if len(self.filetype) > 1:  # TODO: test this
            #     print(self.filetype)
            #     raise Exception("Multiple filetypes")
            # self.filetype = self.filetype[0]
            logger.debug(f"Setting metadata for {file}")
            self.set_metadata(file, mgr)

        if self.filetype is None:  # md files etc have no filetype
            logger.warning(f"file {self.filename} has no type")
            self.filetype = []

        if "PE" in self.filetype:
            self.set_imphash(file)
            self.certs = {}
            self.set_signatures(file)
            self.set_issuer_sha256()
        
        else:
            self.imphash = "N/A"

        if "ELF" in self.filetype:
            self.set_telfhash(file)

        if "JAVACLASS" in self.filetype:
            if "description" not in self.metadata:  # if the environment is not missing javatools
                self.prep_javaclass_metadata()

        self.set_magic(file)
        self.modtime = datetime.datetime.fromtimestamp(
            stat.st_mtime, tz=datetime.timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")
        self.observation_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.permissions = oct(stat.st_mode)

        self.md5 = Observe.create_hash(file, "md5")
        self.sha1 = Observe.create_hash(file, "sha1")
        self.sha256 = Observe.create_hash(file, "sha256")
        self.set_ssdeep(file)

        logger.debug(f"end of init for {file}")

    @staticmethod
    def create_hash(file, hash):
        """
        Generator for hash functions.
        """
        hashers = {
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256,
        }
        with open(file, "rb") as f:
            h = hashers[hash]()
            h.update(f.read())
            return h.hexdigest()

    def set_magic(self, file: str) -> None:
        """
        Reads magic bytes at beginning of file.
        """
        try:
            import magic
        except ImportError:
            logger.warning("libmagic1 or python-magic is not installed.")
        self.magic = magic.from_file(file)

    def set_imphash(self, file: str) -> None:
        """
        Sets import hash for PE files.
        See https://www.mandiant.com/resources/blog/tracking-malware-import-hashing.
        """
        import pefile

        logger.debug(f"impash for {file}")

        pef = pefile.PE(file)
        self.imphash = pef.get_imphash()

    def set_signatures(self, file: str) -> None:
        """
        Runs LIEF signature validation and collects certificate chain.
        """
        import lief

        logger.debug(f"starting set LEIF sigs for {file}")

        def verif_flags(flag: lief.PE.Signature.VERIFICATION_FLAGS) -> str:
            """
            Map flags to strings
            """
            if flag == 0:
                return "OK"

            VERIFICATION_FLAGS = {
                1: "INVALID_SIGNER",
                2: "UNSUPPORTED_ALGORITHM",
                4: "INCONSISTENT_DIGEST_ALGORITHM",
                8: "CERT_NOT_FOUND",
                16: "CORRUPTED_CONTENT_INFO",
                32: "CORRUPTED_AUTH_DATA",
                64: "MISSING_PKCS9_MESSAGE_DIGEST",
                128: "BAD_DIGEST",
                256: "BAD_SIGNATURE",
                512: "NO_SIGNATURE",
                1024: "CERT_EXPIRED",
                2048: "CERT_FUTURE",
            }
            vf = ""

            for k, v in VERIFICATION_FLAGS.items():
                if flag.value & k:
                    if len(vf):
                        vf += " | "
                    vf += v
            logger.debug(f"finished LEIF sigs for {file}")
            return vf

        def hashit(c: lief.PE.x509):
            hc = hashlib.sha256()
            hc.update(c.raw)
            return hc.hexdigest()

        def cert_parser(cert: lief.PE.x509) -> dict:
            """lief certs are messy. convert to json data"""

            logger.debug(f"starting cert parse for LEIF sigs")

            crt = str(cert).split("\n")
            cert_d = {}
            for line in crt:
                if line:  # catch empty string
                    try:
                        k, v = re.split(r"\s+: ", line)  # noqa: W605
                    except ValueError:  # not enough values to unpack
                        k = re.split(r"\s+: ", line)[0]  # noqa: W605
                        v = ""
                    except Exception as e:
                        print(line)
                        raise (e)
                    k = "_".join(k.split())  # replace space with underscore
                    cert_d[k] = v
                cert_d["sha256"] = hashit(cert)
            return cert_d

        pe = lief.parse(file)
        if len(pe.signatures) > 1:
            logger.info("file has multiple signatures")
        self.signatures = []
        if not pe.signatures:
            logger.info(f"file {file} has no signatures.")
            return

        # perform authentihash computation
        self.authentihash = pe.authentihash(pe.signatures[0].digest_algorithm).hex()

        # verifies signature digest vs the hashed code to validate code integrity
        self.authenticode_integrity = verif_flags(pe.verify_signature())

        self.signatures = []
        for sig in pe.signatures:
            certs = []
            for c in sig.certificates:
                cert_dict = cert_parser(c)
                certs.append(cert_dict)
                self.certs[cert_dict["sha256"]] = c.raw
            self.signatures.append(
                {
                    "certs": certs,
                    "signers": str(sig.signers[0]),
                    "digest_algorithm": str(sig.digest_algorithm),
                    "verification": verif_flags(
                        sig.check()
                    ),  # gives us more info than a bool on fail
                    "sha1": sig.content_info.digest.hex(),
                    # "sections": [s.__str__() for s in pe.sections]
                    # **signinfo,
                }
            )

        logger.debug(f"finished cert parse for LEIF sigs")

    def set_issuer_sha256(self) -> None:
        """
        Parses the certificates to build issuer_sha256 chain
        The match between issuer and subject name is case insensitive,
        as per RFC 5280 4.1.2.4 section 7.1
        """
        logger.debug("identifying issuer")
        subject_sha = {}  # dictionary that maps subject to sha256
        for sig in self.signatures:
            for cert in sig["certs"]:  # set mappings
                subject_sha[cert["subject_name"].casefold()] = cert["sha256"]

        for sig in self.signatures:
            for cert in sig["certs"]:  # parse mappings, set issuer sha based on issuer name
                if cert["issuer_name"].casefold() in subject_sha:
                    cert["issuer_sha256"] = subject_sha[cert["issuer_name"].casefold()]

    def set_telfhash(self, file: str) -> None:
        """
        Sets telfhash for ELF files.
        See https://github.com/trendmicro/telfhash.
        """
        try:
            import telfhash
        except ModuleNotFoundError:
            logger.warning("tlsh and telfhash are not installed.")
            return
        
        def worker()->None:
            '''
            Worker for telfhash since it can hang indefinitely on select files
            '''
            try:
                logger.debug(f"getting elf hash for {file}")
                self.telfhash = telfhash.telfhash(file)[0]["telfhash"]
                
            except Exception as e:
                logger.debug(f"telfhash failed for {file}: {e}")
                return 
            
        timeout=30
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            logger.warning(
                f"telfhash timed out for {file} after {timeout} seconds"
            )
            return
        

    def set_ssdeep(self, file: str) -> None:
        """
        Computes fuzzy hashing using ssdeep.
        See https://ssdeep-project.github.io/ssdeep/index.html.
        """
        logger.debug(f"starting ssdeep for {file}")
        try:
            out = subprocess.run(
                ["ssdeep", "-b", file], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            ).stdout.decode("utf-8")
        except FileNotFoundError:
            logger.warning("ssdeep is not installed.")
            return
        out = out.split("\n")[1]  # header/hash/emptystring
        out = out.split(",")[0]  # hash/filename
        self.ssdeep = out
        logger.debug(f"finished ssdeep for {file}")

    def set_metadata(self, file: str, mgr: pluggy.PluginManager) -> None:
        sw = Software()  # dummy
        q = Queue()  # dummy
        kwargs = { #possible args for surfactant plugins
            "sbom": None,
            "software": sw,
            "filename": file,
            "filetype": self.filetype,
            "context_queue": q,
            "current_context": None,
            "children": None,
            "software_field_hints": [],
            "omit_unrecognized_types": None,
        }

        logger.debug(f"trying surfactant for {file}")

        self.metadata={}

        hooks=mgr.hook.extract_file_info.get_hookimpls()

        for plugin in hooks:
            plugin_name=plugin.plugin_name.split(".")[-1]
            logger.debug(f"trying hook: {plugin_name}")

            filtered_kwargs={}

            #if plugin function takes argument, add it to filtered 
            for k, v in kwargs.items():
                if k in plugin.argnames: 
                    filtered_kwargs[k]=v
                
            logger.info(f"filtered args {filtered_kwargs} for {plugin_name}")

            try:
                result=plugin.function(**filtered_kwargs)
            except Exception as e:
                # Log plugin failure but continue with other plugins
                logger.exception(
                    f"Fail - Plugin {plugin_name} failed on file {file}: {e}"
                )
                continue

            if not result:
                # Plugin returned nothing useful, just skip it
                logger.debug(f"Plugin {plugin_name} returned no metadata for {file}")
                continue

            logger.debug(f"Success - Plugin {plugin_name} produced metadata: {result}")

            if plugin_name in self.metadata:
                raise Exception(
                    f"duplicate {self.filetype} metadata for {file} from plugin {plugin_name}"
                )

            self.metadata[plugin_name] = result

        if not self.metadata:
            logger.debug(f"No plugin produced metadata for {file}, using Unknown fallback")
            self.metadata = {
                "Unknown": {
                    "description": "some other file not in"
                    "{a.out, coff, docker image, elf, java, "
                    "js, mach-o, native lib, ole, pe, rpm, uboot image}"
                }
            }

    def _safe_serialize(self, obj) -> str:
        """
        Certs are byte objects, not json.
        This function gives a default value to unserializable data.
        Returns json encoded string where the non-serializable bits are
        a string saying not serializable.

        Parameters:
        -----------
            obj : dict
                Object to serialize.

        """

        def default(o):
            return f"<<non-serializable: {type(o).__qualname__}>>"

        return json.dumps(obj, default=default)

    def write_json(self, outdir: str = ".") -> None:
        """
        Writes observation to json file.

        Parameters:
        -----------
            outdir : str
                Output directory prefix. Defaults to local directory.
        """
        os.makedirs(outdir, exist_ok=True)
        vs = vars(self)
        if "certs" in vs:
            Path(os.path.join(outdir, "certs")).mkdir(parents=True, exist_ok=True)
            for c, b in self.certs.items():
                with open(f"{os.path.join(outdir, 'certs', c)}.crt", "wb") as cert_out:
                    cert_out.write(b)
        outfile = f"{os.path.join(outdir, self.filename)}.{self.md5}.json"
        vs = {k: v for k, v in vs.items() if k != "certs"}
        with open(outfile, "w") as f:
            f.write(self._safe_serialize(vs))

    def write_database(self, database: str, outdir: str = ".") -> None:
        """
        Creates or loads json file into duckdb database

        Parameters:
        -----------
            database : str
                Path to duckdb database file.
            outdir : str
                Output directory prefix. Defaults to current working directory.
        """
        observation_json = f"{os.path.join(outdir, self.filename)}.{self.md5}.json"
        if os.path.exists(observation_json):
            try:
                if not os.path.exists(database):  # create the table if database is new
                    # create table and views from sql
                    db_path = os.path.dirname(database)
                    if db_path != "":
                        os.makedirs(db_path, exist_ok=True)
                    con = duckdb.connect(database)  # creates or connects
                    con.sql(files("database").joinpath("eyeon-ddl.sql").read_text())
                else:
                    con = duckdb.connect(database)  # creates or connects
                # add the file to the observations table, making it match template
                # observations with missing keys will get null vals as placeholder to match sql
                con.sql(
                    f"""
                insert into observations by name
                select * from
                read_json_auto(['{observation_json}',
                                '{files('database').joinpath('observations.json')}'],
                                union_by_name=true, auto_detect=true)
                where filename is not null;
                """
                )
                con.close()
            except duckdb.IOException as ioe:
                con = None
                s = f":exclamation: Failed to attach to db {database}: {ioe}"
                print(s)
        else:
            raise FileNotFoundError

    def __str__(self) -> str:
        return pprint.pformat(vars(self), indent=2)

    def prep_javaclass_metadata(self) -> None:
        nmd = {"javaClasses": []}

        if len(self.metadata.keys()) > 1:
            print(self.metadata)
        i = 0
        for k, v in self.metadata.get("javaClasses", {}).items():
            nmd["javaClasses"].append(v)
            nmd["javaClasses"][i]["javaClassName"] = k
            i += 1

        self.metadata = nmd
