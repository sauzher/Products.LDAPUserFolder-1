##############################################################################
#
# Copyright (c) 2000-2008 Jens Vagelpohl and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" LDAP-based CMF membership tool tests

$Id: __init__.py 58 2008-05-28 21:33:24Z jens $
"""

from unittest import main
from unittest import makeSuite
from unittest import TestCase
from unittest import TestSuite
import Testing
import Zope2
Zope2.startup()

from AccessControl.SecurityManagement import newSecurityManager
from OFS.Folder import Folder

try:
    from Products.CMFCore.tests.base.testcase import SecurityTest
    from Products.CMFCore.PortalFolder import PortalFolder
    from Products.CMFCore.tests.base.dummy import DummySite
    from Products.CMFCore.tests.base.dummy import DummyTool
    from Products.LDAPUserFolder.LDAPMemberDataTool import LDAPMemberDataTool
    from Products.LDAPUserFolder.tests.base.dummy import LDAPDummyUserFolder
    from Products.LDAPUserFolder.tests.base.dummy import LDAPDummyUser
except ImportError:
    SecurityTest = TestCase


class LDAPMembershipToolTests(TestCase):

    def test_z3interfaces(self):
        from zope.interface.verify import verifyClass
        from Products.CMFCore.interfaces import IMembershipTool
        from Products.LDAPUserFolder.LDAPMembershipTool import LDAPMembershipTool

        verifyClass(IMembershipTool, LDAPMembershipTool)


class LDAPMembershipToolSecurityTests(SecurityTest):

    def _makeOne(self, *args, **kw):
        from Products.LDAPUserFolder.LDAPMembershipTool import LDAPMembershipTool

        return LDAPMembershipTool(*args, **kw)

    def _makeSite(self, parent=None):
        if parent is None:
            parent = self.root
        site = DummySite( 'site' ).__of__( parent )
        site._setObject( 'portal_membership', self._makeOne() )
        return site

    def test_getCandidateLocalRoles(self):
        site = self._makeSite()
        mtool = site.portal_membership
        acl_users = site._setObject( 'acl_users', LDAPDummyUserFolder() )

        newSecurityManager(None, acl_users.user_foo)
        rval = mtool.getCandidateLocalRoles(mtool)
        self.assertEqual( rval, ('Dummy',) )
        newSecurityManager(None, acl_users.all_powerful_Oz)
        rval = mtool.getCandidateLocalRoles(mtool)
        self.assertEqual( rval, ('Manager', 'Member', 'Owner', 'Reviewer') )

    def test_createMemberArea(self):
        site = self._makeSite()
        mtool = site.portal_membership
        members = site._setObject( 'Members', PortalFolder('Members') )
        acl_users = site._setObject( 'acl_users', LDAPDummyUserFolder() )
        wtool = site._setObject( 'portal_workflow', DummyTool() )

        # permission
        mtool.createMemberArea('user_foo')
        self.failIf( hasattr(members.aq_self, 'user_foo') )
        newSecurityManager(None, acl_users.user_bar)
        mtool.createMemberArea('user_foo')
        self.failIf( hasattr(members.aq_self, 'user_foo') )
        newSecurityManager(None, acl_users.user_foo)
        mtool.setMemberareaCreationFlag()
        mtool.createMemberArea('user_foo')
        self.failIf( hasattr(members.aq_self, 'user_foo') )
        newSecurityManager(None, acl_users.all_powerful_Oz)
        mtool.setMemberareaCreationFlag()
        mtool.createMemberArea('user_foo')
        self.failUnless( hasattr(members.aq_self, 'user_foo') )

        # default content
        f = members.user_foo
        ownership = acl_users.user_foo
        localroles = ( ( 'user_foo', ('Owner',) ), )
        self.assertEqual( f.getOwner(), ownership )
        self.assertEqual( f.get_local_roles(), localroles,
                          'CMF Collector issue #162 (LocalRoles broken): %s'
                          % str( f.get_local_roles() ) )

    def test_deleteMembers(self):
        site = self._makeSite()
        mtool = site.portal_membership
        members = site._setObject( 'Members', PortalFolder('Members') )
        acl_users = site._setObject( 'acl_users', LDAPDummyUserFolder() )
        utool = site._setObject( 'portal_url', DummyTool() )
        wtool = site._setObject( 'portal_workflow', DummyTool() )
        mdtool = site._setObject( 'portal_memberdata', LDAPMemberDataTool() )
        newSecurityManager(None, acl_users.all_powerful_Oz)

        self.assertEqual( acl_users.getUserById('user_foo'),
                          acl_users.user_foo )
        mtool.createMemberArea('user_foo')
        self.failUnless( hasattr(members.aq_self, 'user_foo') )
        mdtool.registerMemberData('Dummy', 'user_foo')
        self.failUnless( mdtool._members.has_key('user_foo') )

        rval = mtool.deleteMembers( ('user_foo', 'user_baz') )
        self.assertEqual( rval, ('user_foo',) )
        self.failIf( acl_users.getUserById('user_foo', None) )
        self.failIf( mdtool._members.has_key('user_foo') )
        self.failIf( hasattr(members.aq_self, 'user_foo') )

    def test_getMemberById_nonesuch(self):
        INVALID_USER_ID = 'nonesuch'

        self.root._setObject( 'folder', Folder( 'folder' ) )
        site = self._makeSite( self.root.folder )
        tool = site.portal_membership
        site.acl_users = LDAPDummyUserFolder()
        self.assertEqual( None, tool.getMemberById( INVALID_USER_ID ) )

    def test_getMemberById_local(self):
        LOCAL_USER_ID = 'user_foo'

        self.root._setObject( 'folder', Folder('folder') )
        site = self._makeSite( self.root.folder )
        site._setObject( 'acl_users', LDAPDummyUserFolder() )
        tool = site.portal_membership
        member = tool.getMemberById( LOCAL_USER_ID)
        self.assertEqual( member.getId(), LOCAL_USER_ID )

    def test_getMemberById_nonlocal(self):
        NONLOCAL_USER_ID = 'user_bar'

        self.root._setObject( 'folder', Folder( 'folder' ) )
        site = self._makeSite( self.root.folder )
        self.root.folder._setObject( 'acl_users', LDAPDummyUserFolder() )
        tool = site.portal_membership
        member = tool.getMemberById( NONLOCAL_USER_ID )
        self.assertEqual( member.getId(), NONLOCAL_USER_ID )

    def test_getMemberById_chained(self):
        LOCAL_USER_ID = 'user_foo'
        NONLOCAL_USER_ID = 'user_bar'

        self.root._setObject( 'folder', Folder( 'folder' ) )
        site = self._makeSite( self.root.folder )
        tool = site.portal_membership

        local_uf = LDAPDummyUserFolder()
        delattr( local_uf, NONLOCAL_USER_ID )
        site._setObject('acl_users', local_uf)

        nonlocal_uf = LDAPDummyUserFolder()
        delattr( nonlocal_uf, LOCAL_USER_ID )
        self.root.folder._setObject('acl_users', nonlocal_uf)

        local_member = tool.getMemberById(LOCAL_USER_ID)
        self.assertEqual(local_member.getId(), LOCAL_USER_ID)

        nonlocal_member = tool.getMemberById(NONLOCAL_USER_ID)
        self.assertEqual(nonlocal_member.getId(), NONLOCAL_USER_ID)

def test_suite():
    try:
        from Products import CMFCore

        return TestSuite((
            makeSuite( LDAPMembershipToolTests ),
            makeSuite( LDAPMembershipToolSecurityTests )
            ))
    except ImportError:
        # No CMF, no tests.
        return TestSuite(())

if __name__ == '__main__':
    main(defaultTest='test_suite')
