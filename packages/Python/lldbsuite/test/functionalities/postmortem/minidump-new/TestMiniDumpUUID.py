"""
Test basics of Minidump debugging.
"""

from __future__ import print_function
from six import iteritems

import shutil

import lldb
import os
from lldbsuite.test.decorators import *
from lldbsuite.test.lldbtest import *
from lldbsuite.test import lldbutil


class MiniDumpUUIDTestCase(TestBase):

    mydir = TestBase.compute_mydir(__file__)

    NO_DEBUG_INFO_TESTCASE = True

    def setUp(self):
        super(MiniDumpUUIDTestCase, self).setUp()
        self._initial_platform = lldb.DBG.GetSelectedPlatform()

    def tearDown(self):
        lldb.DBG.SetSelectedPlatform(self._initial_platform)
        super(MiniDumpUUIDTestCase, self).tearDown()

    def verify_module(self, module, verify_path, verify_uuid):
        uuid = module.GetUUIDString()
        self.assertEqual(verify_path, module.GetFileSpec().fullpath)
        self.assertEqual(verify_uuid, uuid)

    def test_zero_uuid_modules(self):
        """
            Test multiple modules having a MINIDUMP_MODULE.CvRecord that is valid,
            but contains a PDB70 value whose age is zero and whose UUID values are 
            all zero. Prior to a fix all such modules would be duplicated to the
            first one since the UUIDs claimed to be valid and all zeroes. Now we
            ensure that the UUID is not valid for each module and that we have
            each of the modules in the target after loading the core
        """
        self.dbg.CreateTarget(None)
        self.target = self.dbg.GetSelectedTarget()
        self.process = self.target.LoadCore("linux-arm-zero-uuids.dmp")
        modules = self.target.modules
        self.assertEqual(2, len(modules))
        self.verify_module(modules[0], "/file/does/not/exist/a", None)
        self.verify_module(modules[1], "/file/does/not/exist/b", None)

    def test_uuid_modules_no_age(self):
        """
            Test multiple modules having a MINIDUMP_MODULE.CvRecord that is valid,
            and contains a PDB70 value whose age is zero and whose UUID values are 
            valid. Ensure we decode the UUID and don't include the age field in the UUID.
        """
        self.dbg.CreateTarget(None)
        self.target = self.dbg.GetSelectedTarget()
        self.process = self.target.LoadCore("linux-arm-uuids-no-age.dmp")
        modules = self.target.modules
        self.assertEqual(2, len(modules))
        self.verify_module(modules[0], "/tmp/a", "01020304-0506-0708-090A-0B0C0D0E0F10")
        self.verify_module(modules[1], "/tmp/b", "0A141E28-323C-4650-5A64-6E78828C96A0")

    def test_uuid_modules_no_age_apple(self):
        """
            Test multiple modules having a MINIDUMP_MODULE.CvRecord that is valid,
            and contains a PDB70 value whose age is zero and whose UUID values are 
            valid. Ensure we decode the UUID and don't include the age field in the UUID.
            Also ensure that the first uint32_t is byte swapped, along with the next
            two uint16_t values. Breakpad incorrectly byte swaps these values when it
            saves Darwin minidump files.
        """
        self.dbg.CreateTarget(None)
        self.target = self.dbg.GetSelectedTarget()
        self.process = self.target.LoadCore("macos-arm-uuids-no-age.dmp")
        modules = self.target.modules
        self.assertEqual(2, len(modules))
        self.verify_module(modules[0], "/tmp/a", "04030201-0605-0807-090A-0B0C0D0E0F10")
        self.verify_module(modules[1], "/tmp/b", "281E140A-3C32-5046-5A64-6E78828C96A0")

    def test_uuid_modules_with_age(self):
        """
            Test multiple modules having a MINIDUMP_MODULE.CvRecord that is valid,
            and contains a PDB70 value whose age is valid and whose UUID values are 
            valid. Ensure we decode the UUID and include the age field in the UUID.
        """
        self.dbg.CreateTarget(None)
        self.target = self.dbg.GetSelectedTarget()
        self.process = self.target.LoadCore("linux-arm-uuids-with-age.dmp")
        modules = self.target.modules
        self.assertEqual(2, len(modules))
        self.verify_module(modules[0], "/tmp/a", "01020304-0506-0708-090A-0B0C0D0E0F10-10101010")
        self.verify_module(modules[1], "/tmp/b", "0A141E28-323C-4650-5A64-6E78828C96A0-20202020")

    def test_uuid_modules_elf_build_id_16(self):
        """
            Test multiple modules having a MINIDUMP_MODULE.CvRecord that is valid,
            and contains a ELF build ID whose value is valid and is 16 bytes long.
        """
        self.dbg.CreateTarget(None)
        self.target = self.dbg.GetSelectedTarget()
        self.process = self.target.LoadCore("linux-arm-uuids-elf-build-id-16.dmp")
        modules = self.target.modules
        self.assertEqual(2, len(modules))
        self.verify_module(modules[0], "/tmp/a", "01020304-0506-0708-090A-0B0C0D0E0F10")
        self.verify_module(modules[1], "/tmp/b", "0A141E28-323C-4650-5A64-6E78828C96A0")

    def test_uuid_modules_elf_build_id_20(self):
        """
            Test multiple modules having a MINIDUMP_MODULE.CvRecord that is valid,
            and contains a ELF build ID whose value is valid and is 20 bytes long.
        """
        self.dbg.CreateTarget(None)
        self.target = self.dbg.GetSelectedTarget()
        self.process = self.target.LoadCore("linux-arm-uuids-elf-build-id-20.dmp")
        modules = self.target.modules
        self.assertEqual(2, len(modules))
        self.verify_module(modules[0], "/tmp/a", "01020304-0506-0708-090A-0B0C0D0E0F10-11121314")
        self.verify_module(modules[1], "/tmp/b", "0A141E28-323C-4650-5A64-6E78828C96A0-AAB4BEC8")

    def test_uuid_modules_elf_build_id_zero(self):
        """
            Test multiple modules having a MINIDUMP_MODULE.CvRecord that is valid,
            and contains a ELF build ID whose value is all zero.
        """
        self.dbg.CreateTarget(None)
        self.target = self.dbg.GetSelectedTarget()
        self.process = self.target.LoadCore("linux-arm-uuids-elf-build-id-zero.dmp")
        modules = self.target.modules
        self.assertEqual(2, len(modules))
        self.verify_module(modules[0], "/not/exist/a", None)
        self.verify_module(modules[1], "/not/exist/b", None)

    @expectedFailureAll(oslist=["windows"])
    def test_partial_uuid_match(self):
        """
            Breakpad has been known to create minidump files using CvRecord in each
            module whose signature is set to PDB70 where the UUID only contains the
            first 16 bytes of a 20 byte ELF build ID. Code was added to 
            ProcessMinidump.cpp to deal with this and allows partial UUID matching. 

            This test verifies that if we have a minidump with a 16 byte UUID, that
            we are able to associate a symbol file with a 20 byte UUID only if the
            first 16 bytes match. In this case we will see the path from the file
            we found in the test directory and the 20 byte UUID from the actual
            file, not the 16 byte shortened UUID from the minidump.
        """
        so_path = self.getBuildArtifact("libuuidmatch.so")
        self.yaml2obj("libuuidmatch.yaml", so_path)
        self.dbg.CreateTarget(None)
        self.target = self.dbg.GetSelectedTarget()
        cmd = 'settings set target.exec-search-paths "%s"' % (os.path.dirname(so_path))
        self.dbg.HandleCommand(cmd)
        self.process = self.target.LoadCore("linux-arm-partial-uuids-match.dmp")
        modules = self.target.modules
        self.assertEqual(1, len(modules))
        self.verify_module(modules[0], so_path, 
                           "7295E17C-6668-9E05-CBB5-DEE5003865D5-5267C116")

    @expectedFailureAll(oslist=["windows"])
    def test_partial_uuid_mismatch(self):
        """
            Breakpad has been known to create minidump files using CvRecord in each
            module whose signature is set to PDB70 where the UUID only contains the
            first 16 bytes of a 20 byte ELF build ID. Code was added to 
            ProcessMinidump.cpp to deal with this and allows partial UUID matching. 
            
            This test verifies that if we have a minidump with a 16 byte UUID, that
            we are not able to associate a symbol file with a 20 byte UUID only if
            any of the first 16 bytes do not match. In this case we will see the UUID
            from the minidump file and the path from the minidump file.
        """
        so_path = self.getBuildArtifact("libuuidmismatch.so")
        self.yaml2obj("libuuidmismatch.yaml", so_path)
        self.dbg.CreateTarget(None)
        self.target = self.dbg.GetSelectedTarget()
        cmd = 'settings set target.exec-search-paths "%s"' % (os.path.dirname(so_path))
        self.dbg.HandleCommand(cmd)
        self.process = self.target.LoadCore("linux-arm-partial-uuids-mismatch.dmp")
        modules = self.target.modules
        self.assertEqual(1, len(modules))
        self.verify_module(modules[0],
                           "/invalid/path/on/current/system/libuuidmismatch.so", 
                           "7295E17C-6668-9E05-CBB5-DEE5003865D5")
