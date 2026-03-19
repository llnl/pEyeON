import os
import unittest

from glob import glob
import datetime as dt

import json

from eyeon import observe

import jsonschema


class ObservationTestCase(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.OBS = observe.Observe("tests/binaries/a_out_files/big_m68020.aout")

    def testVars(self) -> None:
        self.assertEqual(self.OBS.bytecount, 4)
        self.assertEqual(self.OBS.filename, "big_m68020.aout")
        self.assertEqual(self.OBS.md5, "e8d3808a4e311a4262563f3cb3a31c3e")
        self.assertEqual(self.OBS.sha1, "fbf8688fbe1976b6f324b0028c4b97137ae9139d")
        self.assertEqual(
            self.OBS.sha256, "9e125f97e5f180717096c57fa2fdf06e71cea3e48bc33392318643306b113da4"
        )
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)
        self.assertEqual(self.OBS.permissions, "0o100644")
        self.assertCountEqual(self.OBS.filetype, ["A.OUT big"])

    @classmethod
    def tearDownClass(self) -> None:
        try:
            for j in glob("*.json"):
                os.remove(j)
        except FileNotFoundError:
            pass


class ObservationTestCase2(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.OBS = observe.Observe("tests/binaries/coff_files/intel_80386_coff")

    def testVars(self) -> None:
        self.assertEqual(self.OBS.bytecount, 2)
        self.assertEqual(self.OBS.filename, "intel_80386_coff")
        self.assertEqual(self.OBS.md5, "3e44d3b6dd839ce18f1b298bac5ce63f")
        self.assertEqual(self.OBS.sha1, "aad24871701ab7c50fec7f4f2afb7096e5292854")
        self.assertEqual(
            self.OBS.sha256, "ed22c79e7ff516da5fb6310f6137bfe3b9724e9902c14ca624bfe0873f8f2d0c"
        )
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)
        self.assertEqual(self.OBS.permissions, "0o100644")
        self.assertEqual(
            len(self.OBS.signatures), 0
        )  # this file is unsigned, should have no signatures
        self.assertCountEqual(self.OBS.filetype, ["COFF"])

    def testValidateJson(self) -> None:
        with open("schema/observation.schema.json") as schem:
            schema = json.loads(schem.read())
        obs_json = json.loads(json.dumps(vars(self.OBS)))
        print(jsonschema.validate(instance=obs_json, schema=schema))

    def testValidateSchema(self) -> None:
        with open("schema/observation.schema.json") as schem:
            schema = json.loads(schem.read())

        with open("schema/meta.schema.json") as schem:
            meta = json.loads(schem.read())

        print(jsonschema.validate(instance=schema, schema=meta))

    @classmethod
    def tearDownClass(self) -> None:
        try:
            for j in glob("*.json"):
                os.remove(j)
        except FileNotFoundError:
            pass


class ObservationTestCase3(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.OBS = observe.Observe("tests/binaries/ELF_shared_obj_test_no1/bin/hello_world")

    def testVars(self) -> None:
        self.assertEqual(self.OBS.bytecount, 16424)
        self.assertEqual(self.OBS.filename, "hello_world")
        self.assertEqual(self.OBS.md5, "d2a52fd35b9bec826c814f26cba50b4d")
        self.assertEqual(self.OBS.sha1, "558931bab308cb5d7adb275f7f6a94757286fc63")
        self.assertEqual(
            self.OBS.sha256, "f776715b7a01c4d4efc6be326b3e82ce546efd182c39040a7a9159f6dbe13398"
        )
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)
        self.assertEqual(self.OBS.permissions, "0o100755")
        self.assertCountEqual(self.OBS.filetype, ["ELF"])

    @classmethod
    def tearDownClass(self) -> None:
        try:
            for j in glob("*.json"):
                os.remove(j)
        except FileNotFoundError:
            pass
        # self.OBS.write_json()
        # unittest.mock?


class ObservationTestCase4(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.OBS = observe.Observe("tests/binaries/java_class_no1/HelloWorld.class")

    def testVars(self) -> None:
        self.assertEqual(self.OBS.bytecount, 1091)
        self.assertEqual(self.OBS.filename, "HelloWorld.class")
        self.assertEqual(self.OBS.md5, "eed620dc71014e2bbe9171867d4a36da")
        self.assertEqual(self.OBS.sha1, "326afcefa84a51113d49d623cf8902b7a07b4e98")
        self.assertEqual(
            self.OBS.sha256, "990f9f530a833d2ab6ef1580235832a1849de3080efc69cc17cf6575e5a1c469"
        )
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)
        self.assertEqual(self.OBS.permissions, "0o100644")
        self.assertCountEqual(self.OBS.filetype, ["JAVACLASS"])

    # def test_detect_it_easy(self) -> None:
    #     expected_output = (
    #         "Binary\n"
    #         "    Format: Java Class File (.CLASS)(Java SE 11)\n\n"
    #     )
    #     self.assertEqual(self.OBS.detect_it_easy, expected_output)


class ObservationTestCase5(unittest.TestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.OBS = observe.Observe(
            "tests/binaries/NET_app_config_test_no1/ConsoleApp2.exe"
        )

    def testToString(self):
        try:
            str(self.OBS)
        except Exception as e:
            self.fail(f"Observe.__str__ raised exception {e} unexpectedly!")


class ObservationTestCase6(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.OBS = observe.Observe("tests/binaries/macho_arm_files/hello_world")

    def testVars(self) -> None:
        self.assertEqual(self.OBS.bytecount, 39224)
        self.assertEqual(self.OBS.filename, "hello_world")
        self.assertEqual(self.OBS.md5, "fef627973d231c07707d3483f6d22ac9")
        self.assertEqual(self.OBS.sha1, "0d66561ca5dfb55376d2bee4bf883938ac229549")
        self.assertEqual(
            self.OBS.sha256, "e8569fc3f4f4a6de36a9b02f585853c6ffcab877a725373d06dad9b44e291088"
        )
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)
        self.assertEqual(self.OBS.permissions, "0o100755")
        self.assertEqual(len(self.OBS.signatures), 0)  # unsigned, should have no signatures
        self.assertCountEqual(self.OBS.filetype, ["MACHO64"])

    # def test_detect_it_easy(self) -> None:
    #     expected_output = (
    #         "Mach-O64\n\n"
    #     )
    #     self.assertEqual(self.OBS.detect_it_easy, expected_output)

    def testValidateJson(self) -> None:
        with open("schema/observation.schema.json") as schem:
            schema = json.loads(schem.read())
        obs_json = json.loads(json.dumps(vars(self.OBS)))
        print(jsonschema.validate(instance=obs_json, schema=schema))

    def testValidateSchema(self) -> None:
        with open("schema/observation.schema.json") as schem:
            schema = json.loads(schem.read())

        with open("schema/meta.schema.json") as schem:
            meta = json.loads(schem.read())

        print(jsonschema.validate(instance=schema, schema=meta))

    @classmethod
    def tearDownClass(self) -> None:
        try:
            for j in glob("*.json"):
                os.remove(j)
        except FileNotFoundError:
            pass


class ObservationTestCase7(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.OBS = observe.Observe("tests/binaries/Windows_dll_test_no1/hello_world.exe")

    def testVars(self) -> None:
        self.assertEqual(self.OBS.bytecount, 58880)
        self.assertEqual(self.OBS.filename, "hello_world.exe")
        self.assertEqual(self.OBS.md5, "c1550ecc547c89b2f24599c990a29184")
        self.assertEqual(self.OBS.sha1, "e4e8ecba8d39ba23cf6f13498021049d62c3659c")
        self.assertEqual(
            self.OBS.sha256, "de22b757eaa0ba2b79378722e8057d3052edc87caf543b17d8267bd2713162a8"
        )
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)
        self.assertEqual(self.OBS.permissions, "0o100644")
        self.assertCountEqual(self.OBS.filetype, ["PE"])


class ObservationTestCase8(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.OBS = observe.Observe("tests/binaries/powerpc/hello_world_ppc")

    def testVars(self) -> None:
        self.assertEqual(self.OBS.bytecount, 71056)
        self.assertEqual(self.OBS.filename, "hello_world_ppc")
        self.assertEqual(self.OBS.md5, "0c51f3e375a077b1ab85106cd8339f1d")
        self.assertEqual(self.OBS.sha1, "ff06f8bc9a328dbba9cd6cdb9d573ae0a9b8e172")
        self.assertEqual(
            self.OBS.sha256, "d01d7dbd0b47fa1f7b1b54f35e48b64051c0b5b128a9ecbe8d8cb311e5ff4508"
        )
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)
        self.assertEqual(self.OBS.permissions, "0o100755")
        self.assertCountEqual(self.OBS.filetype, ["ELF"])

    # def test_detect_it_easy(self) -> None:
    #     expected_output = (
    #         "ELF64\n"
    #         "    Compiler: gcc((GNU) 14.2.0)[EXEC PPC64-64]\n"
    #         "    Library: GLIBC(2.34)[EXEC PPC64-64]\n\n"
    #     )
    #     self.assertEqual(self.OBS.detect_it_easy, expected_output)


class ObservationTestCase9(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.OBS = observe.Observe("tests/binaries/msitest_no1/test.msi")

    def testVars(self) -> None:
        self.assertEqual(self.OBS.bytecount, 12288)
        self.assertEqual(self.OBS.filename, "test.msi")
        self.assertEqual(self.OBS.md5, "ebe91666b88d9acccbea8da417f22422")
        self.assertEqual(self.OBS.sha1, "8de8e4289c7956a370a64aa814f40bdc1b407d00")
        self.assertEqual(
            self.OBS.sha256, "f9c66eb5a1f6c52c8d7ef2fb3bb0e8e0a0c103ae92048ce6b678152542a77c83"
        )
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)
        self.assertEqual(self.OBS.permissions, "0o100644")
        self.assertCountEqual(self.OBS.filetype, ["OLE"])


class ObservationTestCase10(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.OBS = observe.Observe("tests/binaries/Wintap.exe")

    def testVars(self) -> None:
        self.assertEqual(self.OBS.bytecount, 201080)
        self.assertEqual(self.OBS.filename, "Wintap.exe")
        self.assertEqual(self.OBS.md5, "2950c0020a37b132718f5a832bc5cabd")
        self.assertEqual(self.OBS.sha1, "1585373cc8ab4f22ce6e553be54eacf835d63a95")
        self.assertEqual(
            self.OBS.sha256, "bdd73b73b50350a55e27f64f022db0f62dd28a0f1d123f3468d3f0958c5fcc39"
        )
        try:
            dt.datetime.strptime(self.OBS.modtime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail()
        self.assertIsInstance(self.OBS.observation_ts, str)
        self.assertEqual(self.OBS.permissions, "0o100755")
        self.assertEqual(self.OBS.authenticode_integrity, "OK")
        self.assertEqual(self.OBS.signatures[0]["verification"], "OK")
        self.assertEqual(self.OBS.authentihash, self.OBS.signatures[0]["sha1"])

        self.assertNotIn(  # check that the first cert has no issuer in the chain
            "issuer_sha256", self.OBS.signatures[0]["certs"][0]
        )
        self.assertEqual(  # check that the second cert has the first issuer's sha
            self.OBS.signatures[0]["certs"][1]["issuer_sha256"],
            "552f7bdcf1a7af9e6ce672017f4f12abf77240c78e761ac203d1d9d20ac89988",
        )
        self.assertCountEqual(self.OBS.filetype, ["PE"])


class TestFilePermissions(unittest.TestCase):
    def test_nonreadable_file(self):
        # Check to see if permission error is raised
        self.assertRaises(PermissionError, observe.Observe, "/etc/shadow")


class TestFolderPermissions(unittest.TestCase):
    def test_nonreadable_folder(self):
        self.assertRaises(PermissionError, observe.Observe, "/root")


with open("schema/observation.schema.json") as schem:
    schema = json.loads(schem.read())


class TestJSONSchema(unittest.TestCase):
    def test_json_valid_required_properties(self) -> None:
        valid_data = {
            "filename": "little_386.aout",
            "bytecount": 4,
            "magic": "Linux/i386 demand-paged executable (ZMAGIC)",  # noqa: E501
            "md5": "90a2eac40885beab82e592192a2cadd1",
            "observation_ts": "2024-12-04 22:27:45",
            "sha1": "f265f86a2f7bde59b88a47e53c0893d66a55a6cc",
            "sha256": "0dabc62368f8c774acf547ee84e794d172a72c0e8bb3c78d261a6e896ea60c42",
            "uuid": "f1eba7e3-e4c0-43e8-91dc-009a85367517",
            "filetype": ["A.OUT little"],
        }
        assert jsonschema.validate(instance=valid_data, schema=schema) is None

    def test_json_invalid_required_properties(self) -> None:
        invalid_data = {
            "filename": "little_386.aout",
            "bytecount": 4,
            "magic": "Linux/i386 demand-paged executable (ZMAGIC)",  # noqa: E501
            "md5": "90a2eac40885beab82e592192a2cadd1",
            "observation_ts": "2024-12-04 22:27:45",
            "sha1": "f265f86a2f7bde59b88a47e53c0893d66a55a6cc",
            "sha256": "0dabc62368f8c774acf547ee84e794d172a72c0e8bb3c78d261a6e896ea60c42",
            "uuid": "f1eba7e3-e4c0-43e8-91dc-009a85367517",
            "invalid": "Invalid required property",
            "filetype": ["A.OUT little"],
        }
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            assert jsonschema.validate(instance=invalid_data, schema=schema) is None

    def test_type_mismatch(self) -> None:
        invalid_type_data = {
            "filename": "little_386.aout",
            "bytecount": "four",
            "magic": "Linux/i386 demand-paged executable (ZMAGIC)",  # noqa: E501
            "md5": "90a2eac40885beab82e592192a2cadd1",
            "observation_ts": "2024-12-04 22:27:45",
            "sha1": "f265f86a2f7bde59b88a47e53c0893d66a55a6cc",
            "sha256": "0dabc62368f8c774acf547ee84e794d172a72c0e8bb3c78d261a6e896ea60c42",
            "uuid": "f1eba7e3-e4c0-43e8-91dc-009a85367517",
            "filetype": ["A.OUT little"],
        }
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            assert jsonschema.validate(instance=invalid_type_data, schema=schema) is None

    def test_missing_required_fields(self) -> None:
        missing_data = {
            "filename": "little_386.aout",
            "bytecount": 4,
            "magic": "Linux/i386 demand-paged executable (ZMAGIC)",  # noqa: E501
            "md5": "90a2eac40885beab82e592192a2cadd1",
            "observation_ts": "2024-12-04 22:27:45",
            "sha256": "0dabc62368f8c774acf547ee84e794d172a72c0e8bb3c78d261a6e896ea60c42",
            "uuid": "f1eba7e3-e4c0-43e8-91dc-009a85367517",
            "filetype": ["A.OUT little"],
        }
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            assert jsonschema.validate(instance=missing_data, schema=schema) is None

    def test_additional_properties(self) -> None:
        additional_data = {
            "filename": "little_386.aout",
            "bytecount": 4,
            "magic": "Linux/i386 demand-paged executable (ZMAGIC)",  # noqa: E501
            "md5": "90a2eac40885beab82e592192a2cadd1",
            "observation_ts": "2024-12-04 22:27:45",
            "sha1": "f265f86a2f7bde59b88a47e53c0893d66a55a6cc",
            "sha256": "0dabc62368f8c774acf547ee84e794d172a72c0e8bb3c78d261a6e896ea60c42",
            "uuid": "f1eba7e3-e4c0-43e8-91dc-009a85367517",
            "extra_property": "Extra property",
            "filetype": ["A.OUT little"],
        }
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            assert jsonschema.validate(instance=additional_data, schema=schema) is None


if __name__ == "__main__":
    unittest.main()
