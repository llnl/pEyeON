import unittest
import datetime as dt
import os
import json
import jsonschema
import logging
from eyeon import observe


class CorruptFileTestCase(unittest.TestCase):
    """
    This is a superclass the runs common assertions for all of the below
    corruption cases; including bad certificates/signatures and tampered code
    """

    @classmethod
    def corrupt(self, skip, binpath, badbinpath):
        self.badbinpath = badbinpath
        # change some of the data in notepad++.exe to break signature
        writelen = 500  # overwrite some of the bytes

        # open one for read and one for write
        binary = open(binpath, "rb")
        corrupted = open(badbinpath, "wb")

        # get the first chunk and write to corrupted file
        chunk1 = binary.read(skip)
        corrupted.write(chunk1)
        corrupted.write(bytes([0x33] * writelen))  # overwrite some bytes

        # write rest of file
        binary.seek(skip + writelen)
        corrupted.write(binary.read())

        binary.close()
        corrupted.close()

        if not os.path.isfile(badbinpath):
            self.fail(f"Failed to create {badbinpath}")

    def scan(self, badbinpath):
        # scan the corrupted binary
        self.OBS = observe.Observe(badbinpath)

    def corruptedVarsExe(
        self, md5, sha1, sha256, filename, bytecount, sigflag, codeflag, magic=None
    ):
        # verify hashes and see if verification broke properly
        self.assertEqual(self.OBS.bytecount, bytecount)
        self.assertEqual(self.OBS.filename, filename)
        self.assertEqual(self.OBS.md5, md5)
        self.assertEqual(self.OBS.sha1, sha1)
        self.assertEqual(self.OBS.sha256, sha256)
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)

        if magic:  # magic bytes may change during gitlab job, can't always test
            self.assertIn(magic, self.OBS.magic)

        # check signature and authenticode
        self.assertEqual(self.OBS.signatures[0]["verification"], sigflag)
        self.assertEqual(self.OBS.authenticode_integrity, codeflag)

    def validateSchema(self) -> None:
        with open("schema/observation.schema.json") as schem:
            schema = json.loads(schem.read())

        with open("schema/meta.schema.json") as schem:
            meta = json.loads(schem.read())

        print(jsonschema.validate(instance=schema, schema=meta))

    @classmethod
    def tearDownClass(self):
        os.remove(self.badbinpath)

class WintapCertCorrupt(CorruptFileTestCase):
    def setUp(self):
        # path for reading original, and path for writing exe with broken cert
        self.binpath = "tests/binaries/Wintap/Wintap.exe"
        self.badbinpath = "tests/binaries/Wintap/WintapSetup_corrupted.exe"

        # corrupt the first cert, write bad binary, and scan
        self.corrupt(0x0002E940, self.binpath, self.badbinpath)  # location of first cert
        self.scan(self.badbinpath)

    def testCommon(self):
        md5 = "53b22430add80f05a3e092d55c7a3ad1"
        sha1 = "0d4ae039cd9e70dcf1d0d64b6fc4a4ea95d20b6c"
        sha256 = "2a63af1e8d6d14f55d10bcee5a695cc0f51ed296f740bf774952f11ebb36f5a1"
        magic = "PE32 executable (GUI) Intel 80386 Mono/.Net assembly, for MS Windows"
        bytecount = 201080
        sigflag = "CERT_NOT_FOUND"
        codeflag = "CERT_NOT_FOUND | BAD_SIGNATURE"
        filename = self.badbinpath.rsplit("/", maxsplit=1)[-1]
        self.corruptedVarsExe(md5, sha1, sha256, filename, bytecount, sigflag, codeflag, magic)
        self.validateSchema()


class WintapBreakAuthenticode(CorruptFileTestCase):
    def setUp(self):
        self.binpath = "tests/binaries/Wintap/Wintap.exe"
        self.badbinpath = "tests/binaries/Wintap/WintapSetup_corrupted.exe"
        self.corrupt(0x0016490, self.binpath, self.badbinpath)
        self.scan(self.badbinpath)

    def testCommon(self):
        md5 = "6c0a6c03f6751323991eda95c71573cd"
        sha1 = "111ca769e3d92ff58243dc9a2804ebf8770b0698"
        sha256 = "93498a51937835b0801556fb733d9713ed1c60146a33b386dec0cacb3ca4bc2c"
        bytecount = 201080
        sigflag = "OK"  # when you tamper with the code, the signature is still ok
        codeflag = "BAD_DIGEST | BAD_SIGNATURE"
        filename = self.badbinpath.rsplit("/", maxsplit=1)[-1]
        self.corruptedVarsExe(md5, sha1, sha256, filename, bytecount, sigflag, codeflag)
        self.validateSchema()


# class CurlBreakAuthenticode2(CorruptFileTestCase):
#     def setUp(self):
#         self.binpath = "tests/binaries/arm/curl-8.8.0_1-win64arm-mingw.exe"
#         self.badbinpath = "tests/binaries/arm/curl-8.8.0_1-win64arm-mingw_corrupted.exe"
#         self.corrupt(0x00415BB0, self.binpath, self.badbinpath)
#         self.scan(self.badbinpath)

#     def testCommon(self):
#         md5 = "4ee583e324ac1cc55e25acb94047c1fd"
#         sha1 = "4a268ce9447c7096e659559efaafa761952e4393"
#         sha256 = "fb5dce8bd9e138c413dfd6b0d99b702882de282f9a8e63ae9e6055aa913c6b9a"
#         bytecount = 3238492
#         sigflag = "OK"
#         codeflag = "BAD_DIGEST | BAD_SIGNATURE"
#         filename = self.badbinpath.rsplit("/", maxsplit=1)[-1]
#         self.corruptedVarsExe(md5, sha1, sha256, filename, bytecount, sigflag, codeflag)
#         self.configJson()
#         self.validateSchema()


if __name__ == "__main__":
    unittest.main()
