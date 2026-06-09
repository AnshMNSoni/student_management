from odoo.tests.common import TransactionCase
from odoo import Command

class TestResUsers(TransactionCase):

    def setUp(self):
        super(TestResUsers, self).setUp()
        self.group_student = self.env.ref('student_management.group_student')
        self.group_portal = self.env.ref('base.group_portal')
        self.group_user = self.env.ref('base.group_user')
        self.group_system = self.env.ref('base.group_system')

    def test_01_student_group_resolution_on_create(self):
        """Test that adding a user to group_student automatically configures portal group and strips user/system groups."""
        user = self.env['res.users'].create({
            'name': 'Test Student User',
            'login': 'test_student_user@example.com',
            'email': 'test_student_user@example.com',
            'group_ids': [
                Command.link(self.group_student.id),
                Command.link(self.group_user.id),
            ]
        })

        # The user's groups should contain group_student and group_portal, but NOT group_user
        self.assertIn(self.group_student, user.group_ids)
        self.assertIn(self.group_portal, user.group_ids)
        self.assertNotIn(self.group_user, user.group_ids)
        self.assertNotIn(self.group_system, user.group_ids)

    def test_02_student_group_resolution_on_write(self):
        """Test that writing group_student to group_ids modifies other groups correctly."""
        # Create normal user first
        user = self.env['res.users'].create({
            'name': 'Transition User',
            'login': 'transition@example.com',
            'email': 'transition@example.com',
            'group_ids': [
                Command.link(self.group_user.id)
            ]
        })

        self.assertIn(self.group_user, user.group_ids)

        # Update to student group
        user.write({
            'group_ids': [
                Command.link(self.group_student.id)
            ]
        })

        # Check groups are resolved
        self.assertIn(self.group_student, user.group_ids)
        self.assertIn(self.group_portal, user.group_ids)
        self.assertNotIn(self.group_user, user.group_ids)

    def test_03_partner_matching_on_create(self):
        """Test that creating a user uses existing partner with same email."""
        partner = self.env['res.partner'].create({
            'name': 'Matching Partner',
            'email': 'match@example.com',
        })

        user = self.env['res.users'].create({
            'name': 'Match User',
            'login': 'match@example.com',
            'email': 'match@example.com',
        })

        self.assertEqual(user.partner_id.id, partner.id, "Existing partner with same email should be linked.")
