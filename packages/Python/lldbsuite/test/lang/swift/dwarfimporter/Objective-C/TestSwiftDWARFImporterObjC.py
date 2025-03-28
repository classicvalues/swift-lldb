# TestSwiftDWARFImporterObjC.py
#
# This source file is part of the Swift.org open source project
#
# Copyright (c) 2014 - 2019 Apple Inc. and the Swift project authors
# Licensed under Apache License v2.0 with Runtime Library Exception
#
# See https://swift.org/LICENSE.txt for license information
# See https://swift.org/CONTRIBUTORS.txt for the list of Swift project authors
#
# ------------------------------------------------------------------------------
import lldb
from lldbsuite.test.decorators import *
import lldbsuite.test.lldbtest as lldbtest
import lldbsuite.test.lldbutil as lldbutil
import os
import unittest2


class TestSwiftDWARFImporterObjC(lldbtest.TestBase):

    mydir = lldbtest.TestBase.compute_mydir(__file__)

    def build(self):
        include = self.getBuildArtifact('include')
        inputs = self.getSourcePath('Inputs')
        lldbutil.mkdir_p(include)
        import shutil
        for f in ['module.modulemap', 'objc-header.h']:
            shutil.copyfile(os.path.join(inputs, f), os.path.join(include, f))

        super(TestSwiftDWARFImporterObjC, self).build()

        # Remove the header files to thwart ClangImporter.
        self.assertTrue(os.path.isdir(include))
        shutil.rmtree(include)

    @skipUnlessDarwin
    @swiftTest
    def test_dwarf_importer(self):
        self.runCmd("settings set symbols.use-swift-dwarfimporter true")
        self.build()
        target, process, thread, bkpt = lldbutil.run_to_source_breakpoint(
            self, 'break here', lldb.SBFileSpec('main.swift'))
        lldbutil.check_variable(self,
                                target.FindFirstGlobalVariable("pureSwift"),
                                value="42")
        lldbutil.check_variable(self,
                                target.FindFirstGlobalVariable("obj"),
                                typename="Swift.Optional<__ObjC.ObjCClass>",
                                num_children=0)
        self.expect("target var obj", substrs=["ObjCClass",
                                               "private_ivar", "42"])
        # FIXME: This triggers an assertion in ClangImporter:
        #        "ObjC property without getter"
        #self.expect("target var swiftChild", substrs=["ObjCClass",
        #                                              "private_ivar", "42"])
        # This is a Clang type, since Clang doesn't generate DWARF for protocols.
        self.expect("target var -d no-dyn proto", substrs=["(id)", "proto"])
        # This is a Swift type.
        self.expect("target var -d run proto", substrs=["(ProtoImpl?)", "proto"])
        self.expect("target var -O proto", substrs=["<ProtoImpl"])
