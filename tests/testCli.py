import unittest
import tempfile
import shutil

from eyeon.cli import CommandLine
from unittest.mock import patch
from pathlib import Path


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        log_patcher=patch("eyeon.cli.CommandLine._configure_logger", return_value=None)
        self.mock_log=log_patcher.start()

        self.cli1 = CommandLine(
            "observe -o ./outputs  -g file.log -v DEBUG -l LLNL demo.ipynb ".split()
        )

        self.cli2 = CommandLine(
            "parse --output-dir ./outputs --log-file file.log --log-level DEBUG tests -t 2 ".split()  # noqa: E501
        )

        self.cli3 = CommandLine(
            "checksum Wintap.exe -a sha1 1585373cc8ab4f22ce6e553be54eacf835d63a95".split()
        )

        self.cli4 = CommandLine(
            "observe Wintap.exe -c 1585373cc8ab4f22ce6e553be54eacf835d63a95 -a sha1".split()
        )

        self.addCleanup(log_patcher.stop)

    def testObserveArgs(self) -> None:
        self.mock_log.assert_called()
        self.assertEqual(self.cli1.args.filename, "demo.ipynb")
        self.assertEqual(self.cli1.args.output_dir, "./outputs")
        self.assertEqual(self.cli1.args.log_level, "DEBUG")
        self.assertEqual(self.cli1.args.log_file, "file.log")
        self.assertEqual(self.cli1.args.location, "LLNL")
        self.assertEqual(self.cli1.args.func, self.cli1.observe)

    def testParseArgs(self) -> None:
        self.assertEqual(self.cli2.args.dir, "tests")
        self.assertEqual(self.cli2.args.output_dir, "./outputs")
        self.assertEqual(self.cli2.args.log_file, "file.log")
        self.assertEqual(self.cli2.args.log_level, "DEBUG")
        self.assertEqual(self.cli2.args.threads, 2)
        self.assertEqual(self.cli2.args.func, self.cli2.parse)

    def testChecksumArgs(self):
        self.assertEqual(self.cli3.args.file, "Wintap.exe")
        self.assertEqual(self.cli3.args.algorithm, "sha1")
        self.assertEqual(self.cli3.args.cksum, "1585373cc8ab4f22ce6e553be54eacf835d63a95")
        self.assertEqual(self.cli3.args.func, self.cli3.checksum)

    def testObserveChecksumArgs(self):
        self.assertEqual(self.cli4.args.filename, "Wintap.exe")
        self.assertEqual(self.cli4.args.checksum, "1585373cc8ab4f22ce6e553be54eacf835d63a95")
        self.assertEqual(self.cli4.args.algorithm, "sha1")

    def testObserveMissingArgs(self):
        with self.assertRaises(SystemExit):
            CommandLine([])


class CliTestObserve(unittest.TestCase):
    def setUp(self):
        # patch observe and checksum functions
        self.observe_patch = patch("eyeon.observe.Observe")
        self.checksum_patch = patch("eyeon.checksum.Checksum")
        self.log_patcher=patch("eyeon.cli.CommandLine._configure_logger", return_value=None)
        
        self.mock_log=self.log_patcher.start()
        self.observe_mock = self.observe_patch.start()
        self.checksum_mock = self.checksum_patch.start()

        self.addCleanup(self.observe_patch.stop)
        self.addCleanup(self.checksum_patch.stop)
        self.addCleanup(self.log_patcher.stop)

    def testObserve_no_checksum(self):
        args = ["observe", "Wintap.exe"]
        cli = CommandLine(args)

        print(cli.args)

        cli.observe(cli.args)
        self.observe_mock.assert_called_once_with("Wintap.exe")
        self.checksum_mock.assert_not_called()

    def testObserve_checksum(self):
        args = ["observe", "Wintap.exe", "-c", "abc123"]
        cli = CommandLine(args)

        cli.observe(cli.args)
        self.observe_mock.assert_called_once_with("Wintap.exe")
        self.checksum_mock.assert_called_once_with("Wintap.exe", "md5", "abc123")

    def testObserve_checksum_alg(self):
        args = ["observe", "Wintap.exe", "-c", "abc123", "-a", "sha1"]
        cli = CommandLine(args)

        cli.observe(cli.args)
        self.observe_mock.assert_called_once_with("Wintap.exe")
        self.checksum_mock.assert_called_once_with("Wintap.exe", "sha1", "abc123")

    def testObserve_optional_args(self):
        args = [
            "observe",
            "Wintap.exe",
            "-o",
            "./output",
            "-g",
            "mylog.log",
            "-v",
            "DEBUG",
        ]
        cli = CommandLine(args)

        cli.observe(cli.args)
        self.observe_mock.assert_called_once_with("Wintap.exe")
        self.checksum_mock.assert_not_called()

class CliTestLogger(unittest.TestCase):
    def setUp(self):
        # Temporary directory for filesystem operations
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tmp_dir, ignore_errors=True))

        min_cli_args=[
            "observe",
            "Wintap.exe"
            ]
        self.cli=CommandLine(min_cli_args)

    @patch("eyeon.cli.logger")
    def test_configure_logger_with_file(self, mock_logger):
        #create a temp dir/file
        log_file = Path(self.tmp_dir) / "logs" / "eyeon.log"

        self.cli._configure_logger("DEBUG", str(log_file))

        log_path = Path(log_file)
        # Parent directory created
        self.assertTrue(log_path.parent.exists())
        self.assertTrue(log_path.parent.is_dir())

        #logger.remove called
        mock_logger.remove.assert_called_once()

        #logger.add called for this file and for stderr
        file_calls = [
            call
            for call in mock_logger.add.call_args_list
            if call.args and call.args[0] == log_path
        ]
        self.assertEqual(len(file_calls), 1)

        _, file_kwargs = file_calls[0]
        self.assertEqual(file_kwargs["level"], "DEBUG")
        self.assertIn("format", file_kwargs)
        self.assertEqual(mock_logger.add.call_count, 2)

        # Debug message logged
        mock_logger.debug.assert_called_once()
        debug_args, _ = mock_logger.debug.call_args
        self.assertIn("Logging configured", debug_args[0])
        

    @patch("eyeon.cli.logger")
    def test_configure_logger_no_file(self, mock_logger):
        self.cli._configure_logger("INFO", None)

        mock_logger.remove.assert_called_once()
        # Only stderr handler
        self.assertEqual(mock_logger.add.call_count, 1)

        mock_logger.debug.assert_called_once()
        debug_args, _ = mock_logger.debug.call_args
        self.assertIn("Logging configured", debug_args[0])

    @patch("eyeon.cli.logger")
    def test_configure_logger_overwrites_existing(self, mock_logger):
        log_file = f"{Path(self.tmp_dir)}/logs/eyeon.log"
        log_path = Path(log_file)

        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("old content")

        # precondition
        self.assertTrue(log_path.exists())

        self.cli._configure_logger("ERROR", log_file)

        # unlink() should remove the file; logger.add is mocked so nothing recreates it
        self.assertFalse(log_path.exists())

        file_calls = [
            call
            for call in mock_logger.add.call_args_list
            if call.args and call.args[0] == log_path
        ]
        self.assertEqual(len(file_calls), 1)


if __name__ == "__main__":
    unittest.main()
