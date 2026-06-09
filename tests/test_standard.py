# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestStudentStandard(TransactionCase):

    def test_01_compute_name(self):
        """Test the computation of standard name."""
        # Scenario 1: standard and division both set
        std1 = self.env['student.standard'].create({
            'standard': '10',
            'division': 'B',
        })
        self.assertEqual(std1.name, '10-B')

        # Scenario 2: division is empty
        std2 = self.env['student.standard'].create({
            'standard': '11',
            'division': '',
        })
        self.assertEqual(std2.name, '11')

    def test_02_check_standard_value(self):
        """Test constraints on standard value."""
        # Single letter standard should raise ValidationError
        with self.assertRaises(ValidationError):
            self.env['student.standard'].create({
                'standard': 'A',
                'division': '1',
            })
            
        with self.assertRaises(ValidationError):
            self.env['student.standard'].create({
                'standard': 'F',
                'division': 'A',
            })

    def test_03_subject_relation(self):
        """Test subject relation compute and inverse methods."""
        # Create subjects with standard name
        sub1 = self.env['student.subject'].create({
            'name': 'History',
            'standard_name': '9'
        })
        sub2 = self.env['student.subject'].create({
            'name': 'Geography',
            'standard_name': '9'
        })

        # Create standard 9
        std = self.env['student.standard'].create({
            'standard': '9',
            'division': 'A'
        })

        # The subjects should be auto-linked to standard via computed subject_ids
        self.assertEqual(std.subject_ids, sub1 | sub2, "Subjects with same standard_name should be linked.")

        # Test inverse: add another subject by assigning to subject_ids
        sub3 = self.env['student.subject'].create({
            'name': 'English',
            'standard_name': 'Other'
        })
        std.write({
            'subject_ids': [(4, sub3.id)]
        })
        self.assertEqual(sub3.standard_name, '9', "Inversing subject_ids should update the subject's standard name.")

        # Test inverse removal (unlinking)
        std.write({
            'subject_ids': [(3, sub1.id)]
        })
        # Check if sub1 is deleted (since _inverse_subject_ids unlinks removed subjects)
        self.assertFalse(sub1.exists(), "Removed subjects from standard should be unlinked/deleted.")
