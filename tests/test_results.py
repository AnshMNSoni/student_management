from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestStudentResults(TransactionCase):

    def setUp(self):
        super(TestStudentResults, self).setUp()
        
        # Setup standard, student, and subjects
        self.standard = self.env['student.standard'].create({
            'standard': '10',
            'division': 'A',
        })
        self.student = self.env['student.management'].create({
            'name': 'Charlie Brown',
            'roll_number': 'S107',
            'age': 15,
            'email': 'charlie@example.com',
            'standard_id': self.standard.id,
        })
        self.subject_math = self.env['student.subject'].create({
            'name': 'Mathematics',
            'standard_name': '10'
        })
        self.subject_science = self.env['student.subject'].create({
            'name': 'Science',
            'standard_name': '10'
        })
        self.subject_history = self.env['student.subject'].create({
            'name': 'History',
            'standard_name': '10'
        })

    def test_01_result_computations_and_grades(self):
        """Test grade/percentage computation for results and lines."""
        # Create empty result
        result = self.env['student.result'].create({
            'student_id': self.student.id,
        })
        self.assertEqual(result.overall_percentage, 0.0)
        self.assertEqual(result.overall_grade, 'F')

        # Add lines with grades A, B
        line1 = self.env['student.result.line'].create({
            'result_id': result.id,
            'subject_id': self.subject_math.id,
            'marks': 95.0,
        })
        self.assertEqual(line1.grade, 'A')

        line2 = self.env['student.result.line'].create({
            'result_id': result.id,
            'subject_id': self.subject_science.id,
            'marks': 75.0,
        })
        self.assertEqual(line2.grade, 'B')

        # Overall average should be 85.0 -> Grade B
        result.flush_model() # ensures compute is run and saved
        self.assertEqual(result.overall_percentage, 85.0)
        self.assertEqual(result.overall_grade, 'B')

    def test_02_duplicate_subject_validation(self):
        """Test that duplicate subjects under the same result record raise ValidationError."""
        result = self.env['student.result'].create({
            'student_id': self.student.id,
        })
        
        self.env['student.result.line'].create({
            'result_id': result.id,
            'subject_id': self.subject_math.id,
            'marks': 80.0,
        })

        # Attempt to add another line for Mathematics
        with self.assertRaises(ValidationError):
            self.env['student.result.line'].create({
                'result_id': result.id,
                'subject_id': self.subject_math.id,
                'marks': 90.0,
            })

    def test_03_sequence_generation(self):
        """Test that result sequence increases automatically."""
        result1 = self.env['student.result'].create({
            'student_id': self.student.id,
        })
        result2 = self.env['student.result'].create({
            'student_id': self.student.id,
        })
        
        self.assertTrue(result2.sequence > result1.sequence, "Sequence should be incremented.")

    def test_04_allowed_subjects(self):
        """Test allowed subjects computation logic."""
        result = self.env['student.result'].create({
            'student_id': self.student.id,
        })
        
        line1 = self.env['student.result.line'].create({
            'result_id': result.id,
            'subject_id': self.subject_math.id,
            'marks': 85.0,
        })

        # Calculate allowed subjects for a new line on the same result
        new_line = self.env['student.result.line'].new({
            'result_id': result.id,
        })
        new_line._compute_allowed_subject_ids()
        
        # Expected subjects: all standard 10 subjects EXCEPT Mathematics (which is already in line1)
        expected_allowed = self.subject_science | self.subject_history
        self.assertEqual(new_line.allowed_subject_ids._origin, expected_allowed)
