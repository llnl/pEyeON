import unittest
import os
import shutil
import json

from unittest.mock import patch, MagicMock
from eyeon import parse
from pathlib import Path


class X86ParseTestCase(unittest.TestCase):
    def checkOutputs(self) -> None:  # these files + paths should be created by parse
        self.assertTrue(os.path.isdir("./tests/testresults"))
        self.assertTrue(os.path.isdir("./tests/testresults/certs"))
        self.assertTrue(
            os.path.isfile("./tests/testresults/Wintap.exe.2950c0020a37b132718f5a832bc5cabd.json")
        )
        self.assertTrue(
            os.path.isfile(
                "./tests/testresults/WintapSetup.msi.f06087338f3b3e301d841c29429a1c99.json"
            )
        )

    def certExtracted(self) -> None:
        self.assertTrue(
            os.path.isfile(
                "./tests/testresults/certs/552f7bdcf1a7af9e6ce672017f4f12abf77240c78e761ac203d1d9d20ac89988.crt"  # noqa: E501
            )
        )
        self.assertTrue(
            os.path.isfile(
                "./tests/testresults/certs/33846b545a49c9be4903c60e01713c1bd4e4ef31ea65cd95d69e62794f30b941.crt"  # noqa: E501
            )
        )  # noqa: E501

    def validateWintapExeJson(self) -> None:
        with open("./tests/testresults/Wintap.exe.2950c0020a37b132718f5a832bc5cabd.json") as schem:
            schema = json.loads(schem.read())
        self.assertEqual(schema["bytecount"], 201080)
        self.assertEqual(schema["filename"], "Wintap.exe")
        self.assertEqual(schema["md5"], "2950c0020a37b132718f5a832bc5cabd")
        self.assertEqual(schema["sha1"], "1585373cc8ab4f22ce6e553be54eacf835d63a95")
        self.assertEqual(
            schema["sha256"], "bdd73b73b50350a55e27f64f022db0f62dd28a0f1d123f3468d3f0958c5fcc39"
        )
        self.assertEqual(schema["authenticode_integrity"], "OK")
        self.assertEqual(schema["signatures"][0]["verification"], "OK")
        self.assertEqual(schema["authentihash"], schema["signatures"][0]["sha1"])

        self.assertNotIn(  # check that the first cert has no issuer in the chain
            "issuer_sha256", schema["signatures"][0]["certs"][0]
        )
        self.assertEqual(  # check that the second cert has the first issuer's sha
            schema["signatures"][0]["certs"][1]["issuer_sha256"],
            "552f7bdcf1a7af9e6ce672017f4f12abf77240c78e761ac203d1d9d20ac89988",
        )

    def validateWintapSetupMsiJson(self) -> None:
        with open(
            "./tests/testresults/WintapSetup.msi.f06087338f3b3e301d841c29429a1c99.json"
        ) as schem:
            schema = json.loads(schem.read())
        self.assertEqual(schema["bytecount"], 13679616)
        self.assertEqual(schema["filename"], "WintapSetup.msi")
        self.assertEqual(schema["md5"], "f06087338f3b3e301d841c29429a1c99")
        self.assertEqual(schema["sha1"], "ffb3f6b7d55dfbd293a922e2bfa7ba0110d2ff9c")
        self.assertEqual(
            schema["sha256"], "7bc438c474f01502c7f6e2447b7c525888c86c25c4d0703495c20fe22a71ddc0"
        )
        self.assertFalse(schema["signatures"])  # WintapSetup.msi has no signatures

    @patch("eyeon.parse.logger")
    @patch("eyeon.parse.Observe")
    def test_permission_error(self, mock_observe, mock_logger):
        mock_observe.side_effect=PermissionError()

        file_and_path = ("secret.txt", "/dev/null")
        
        p=parse.Parse("/dev/null")
        p._observe(file_and_path)

        mock_logger.warning.assert_called_once_with("File secret.txt cannot be read.")

    @patch("eyeon.parse.logger")
    @patch("eyeon.parse.Observe")
    def test_file_not_found_error(self, mock_observe, mock_logger):
        mock_observe.side_effect=FileNotFoundError()

        file_and_path = ("does_not_exist.txt", "/dev/null")
        
        p=parse.Parse("/dev/null")
        p._observe(file_and_path)

        mock_logger.warning.assert_called_once_with("No such file does_not_exist.txt.")

    @patch("eyeon.parse.time.time")
    @patch("eyeon.parse.os.getpid")
    @patch.object(parse.Parse, "_observe")
    def test_observe_worker(self, mock_parse_observe, mock_pid, mock_time):
        progress_map={}
        mock_pid.return_value=1
        mock_time.return_value=10.0

        mock_args=("test.txt", "/test/result/path", progress_map)

        p=parse.Parse("/dev/null")
        p._observe_worker(mock_args)

        mock_parse_observe.assert_called_once_with(("test.txt", "/test/result/path"))


    @classmethod
    def tearDownClass(self) -> None:
        if Path("./tests/testresults").exists():
            shutil.rmtree("./tests/testresults")
        else:
            pass


class TestParseFunctions(unittest.TestCase):
    def setUp(self):
        self.prs=parse.Parse("/dev/null")

        #---Patch Logging---
        logger_patcher = patch("eyeon.parse.logger")
        self.mock_logger = logger_patcher.start()
        self.addCleanup(logger_patcher.stop)

        #---Patch Dir Walking---
        dir_walk_patcher=patch("eyeon.parse.os.walk")
        self.mock_walk=dir_walk_patcher.start()
        self.addCleanup(dir_walk_patcher.stop)
        # Default: single directory with one file; tests can override
        self.mock_walk.return_value = [
            ("/dev/null", [], ["file1.bin"])
        ]

        #---Patch Threading---
        thread_patcher=patch("eyeon.parse.threading.Thread")
        self.mock_thread_cls=thread_patcher.start()
        self.addCleanup(thread_patcher.stop)

        # Thread instance returned whenever Thread(...) is constructed
        self.mock_thread = MagicMock()
        self.mock_thread_cls.return_value = self.mock_thread

        #---Patch Pool---
        pool_patcher=patch("eyeon.parse.Pool")
        self.mock_pool_cls=pool_patcher.start()
        self.addCleanup(pool_patcher.stop)

        # Context-managed Pool instance
        self.mock_pool = self.mock_pool_cls.return_value.__enter__.return_value
        # Simulate one completed task result so the for-loop in __call__ can iterate once
        self.mock_pool.imap_unordered.return_value = [None]

        #---Patch Manager---
        manager_patcher=patch("eyeon.parse.Manager")
        self.mock_manager_cls=manager_patcher.start()
        self.addCleanup(manager_patcher.stop)
        #create manager instance
        self.mock_manager=self.mock_manager_cls.return_value
        #give dict attribute an empty dict by default
        self.progress_map={} #need this for control
        self.mock_manager.dict.return_value = self.progress_map

        #---Patch Parse._observe so no real work happens---
        self.observe_patcher = patch.object(parse.Parse, "_observe")
        self.mock_observe = self.observe_patcher.start()
        self.addCleanup(self.observe_patcher.stop)

    def _get_monitor_call_from_threads(self):
        '''
        using mock threads gets multiple calls, get only the monitor call
        for easier assertion testing.
        '''
        thread_calls=self.mock_thread_cls.call_args_list

        monitor_call=[
            c for c in thread_calls if c.kwargs.get("daemon") is True
            and getattr(c.kwargs.get("target"), "__name__", "") == "monitor"
            ]
        
        if not monitor_call:
            self.fail("No monitor function found in Threads call...")
        else:
            return monitor_call

    def test_threads_start_monitor(self):
        """
        When threads > 1, a monitor thread should be created as daemon and started.
        """
        self.prs(threads=2)

        monitor_call=self._get_monitor_call_from_threads()

        # Exactly one monitor thread created with daemon=True
        self.assertEqual(len(monitor_call), 1)
        self.assertIn("target", monitor_call[0].kwargs)
        self.assertTrue(monitor_call[0].kwargs["daemon"])

    @patch("eyeon.parse.time.sleep", autospec=True)
    def test_hung_process(self, mock_sleep):
        self.prs(threads=2)

        monitor_call=self._get_monitor_call_from_threads()[0]
        monitor_func=monitor_call.kwargs["target"]#get the actual function from the call

        #control time
        #check interval is 30 seconds, Hang threshold is 120
        with patch("eyeon.parse.time.time", autospec=True) as mock_time:
            #duration = 350 - 100 = 250 > 120
            mock_time.return_value=350 #return a time that would lead to a duration greater than the hang threshold

            #worker that started at 100
            self.progress_map.clear()
            self.progress_map[1234]={
                "file":"hung_file.bin",
                "start":100.0 
            }

            # Make the monitor loop run only once by raising an exception after first check,
            # so this test does not hang forever.
            def sleep_side_effect(_interval):
                raise KeyboardInterrupt()
            
            mock_sleep.side_effect=sleep_side_effect

            with self.assertRaises(KeyboardInterrupt):
                monitor_func() #call the monitor function we grab from our mock threads

        # After the first iteration the monitor should have logged a warning
        self.mock_logger.warning.assert_called()
        logged_messages = [
            args[0] for args, _ in self.mock_logger.warning.call_args_list
        ]
        self.assertTrue(
            any("possible hung process" in msg for msg in logged_messages),
            msg=f"warning not found in: {logged_messages}",
        )

    @patch("eyeon.parse.time.sleep", autospec=True)
    def test_no_hung_process_no_warning(self, mock_sleep):
        self.prs(threads=2)

        monitor_call=self._get_monitor_call_from_threads()[0]
        monitor_func=monitor_call.kwargs["target"]#get the actual function from the call

        #control time
        #check interval is 30 seconds, Hang threshold is 120
        with patch("eyeon.parse.time.time", autospec=True) as mock_time:
            #duration = 200 - 100 = 100 < 120
            mock_time.return_value=200 

            #worker that started at 100
            self.progress_map.clear()
            self.progress_map[1234]={
                "file":"hung_file.bin",
                "start":100.0 
            }

            # Make the monitor loop run only once by raising an exception after first check,
            # so this test does not hang forever.
            def sleep_side_effect(_interval):
                raise KeyboardInterrupt()
            
            mock_sleep.side_effect=sleep_side_effect

            with self.assertRaises(KeyboardInterrupt):
                monitor_func() #call the monitor function we grab from our mock threads

        # After the first iteration the monitor should have logged a warning
        logged_messages = [
            args[0] for args, _ in self.mock_logger.warning.call_args_list
        ]
        self.assertFalse(
            any("possible hung process" in msg for msg in logged_messages),
            msg=f"warning not found in: {logged_messages}",
        )

class X86SinglethreadTestCase(X86ParseTestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.PRS = parse.Parse("./tests/binaries")
        self.PRS(result_path="tests/testresults")  # run scan

    def testCommon(self):
        self.checkOutputs()
        self.certExtracted()
        self.validateWintapExeJson()
        self.validateWintapSetupMsiJson()

    @classmethod
    def tearDownClass(self) -> None:
        shutil.rmtree("./tests/testresults")

class X86TwoThreadTestCase(X86ParseTestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.PRS = parse.Parse("./tests/binaries")
        self.PRS(result_path="tests/testresults", threads=2)

    def testCommon(self):
        self.checkOutputs()
        self.certExtracted()
        self.validateWintapExeJson()
        self.validateWintapSetupMsiJson()


class X86ThreeThreadTestCase(X86ParseTestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.PRS = parse.Parse("./tests/binaries")
        self.PRS(result_path="tests/testresults", threads=3)

    def testCommon(self):
        self.checkOutputs()
        self.certExtracted()
        self.validateWintapExeJson()
        self.validateWintapSetupMsiJson()


if __name__ == "__main__":
    unittest.main()
