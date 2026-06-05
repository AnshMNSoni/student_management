from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.website.controllers.main import Website

class Website(Website):

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        if request.session.uid:
            partner = request.env.user.partner_id
            student = request.env['student.management'].sudo().search([('partner_id', '=', partner.id)], limit=1)
            if student:
                sales_user_sudo = request.env['res.users']
                if partner.user_id and not partner.user_id._is_public():
                    sales_user_sudo = partner.user_id
                else:
                    fallback_sales_user = partner.commercial_partner_id.user_id
                    if fallback_sales_user and not fallback_sales_user._is_public():
                        sales_user_sudo = fallback_sales_user

                values = {
                    'sales_user': sales_user_sudo,
                    'page_name': 'student_profile',
                    'student': student,
                }
                return request.render('student_management.portal_student_profile', values)
        return super().index(**kw)

    @http.route('/student/register', type='http', auth='public', website=True)
    def student_register(self, **kw):
        user = request.env.user
        if not user._is_public() and user.has_group('student_management.group_teacher') and not user.has_group('student_management.group_admin'):
            return request.render('website.403')

        standards = request.env['student.standard'].sudo().search([])
        return request.render('student_management.student_registration_form_temp', {
            'standards': standards,
        })

    @staticmethod
    def _validate_student_registration(post):
        name = post.get('name')
        roll_number = post.get('roll_number')
        email = post.get('email')
        standard_id = post.get('standard_id')
        password = post.get('password')
        confirm_password = post.get('confirm_password')

        if not name or not roll_number or not email or not standard_id or not password or not confirm_password:
            return 'Please fill all required fields.'

        if password != confirm_password:
            return 'Passwords do not match.'

        existing_user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
        if existing_user:
            return 'A user with this email is already registered.'

        existing_student = request.env['student.management'].sudo().search([('roll_number', '=', roll_number)], limit=1)
        if existing_student:
            return 'Roll Number must be unique. A student with this roll number is already registered.'

        return None

    @http.route('/student/register/submit', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def student_register_submit(self, **post):
        user = request.env.user
        if not user._is_public() and user.has_group('student_management.group_teacher') and not user.has_group('student_management.group_admin'):
            return request.render('website.403')

        error = self._validate_student_registration(post)
        if error:
            standards = request.env['student.standard'].sudo().search([])
            return request.render('student_management.student_registration_form_temp', {
                'standards': standards,
                'error': error,
                'post': post
            })

        name = post.get('name')
        roll_number = post.get('roll_number')
        age = post.get('age')
        email = post.get('email')
        standard_id = post.get('standard_id')
        admission_date = post.get('admission_date')
        password = post.get('password')
        subject_ids = request.httprequest.form.getlist('subject_ids')

        try:
            student_vals = {
                'name': name,
                'roll_number': roll_number,
                'age': int(age) if age else 0,
                'email': email,
                'standard_id': int(standard_id),
                'admission_date': admission_date or fields.Date.today(),
                'status': 'draft',
            }
            if subject_ids:
                student_vals['subject_ids'] = [(6, 0, [int(sid) for sid in subject_ids])]

            student = request.env['student.management'].sudo().create(student_vals)
            
            # Create corresponding res.users record
            user_vals = {
                'name': name,
                'login': email,
                'email': email,
                'partner_id': student.partner_id.id,
                'password': password,
                'group_ids': [(6, 0, [request.env.ref('student_management.group_student').id])]
            }
            request.env['res.users'].sudo().create(user_vals)
            
            student.action_send_registration_email()

            return request.render('student_management.student_registration_success', {
                'student': student
            })
        except Exception as e:
            standards = request.env['student.standard'].sudo().search([])
            return request.render('student_management.student_registration_form_temp', {
                'standards': standards,
                'error': str(e),
                'post': post
            })

    @http.route('/student/get_standard_details', type='json', auth='public')
    def get_standard_details(self, standard_id):
        standard = request.env['student.standard'].sudo().browse(int(standard_id))
        if not standard.exists():
            return {'subjects': [], 'fees': 0}
        subjects = request.env['student.subject'].sudo().search([('standard_name', '=', standard.standard)])
        return {
            'fees': standard.fees_amount or 0.0,
            'subjects': [{'id': s.id, 'name': s.name} for s in subjects]
        }


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        student = request.env['student.management'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        # Only inject the non-counter QWeb rendering variable if this is not a counters JSON-RPC call
        if request.httprequest.path != '/my/counters':
            values['is_student'] = bool(student)
            
        if student:
            if 'student_count' in counters:
                values['student_count'] = 1
            if 'result_count' in counters:
                values['result_count'] = request.env['student.result'].search_count([('student_id', '=', student.id)])
            if 'fees_count' in counters:
                values['fees_count'] = request.env['student.fees'].search_count([('student_id', '=', student.id)])
        return values

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        partner = request.env.user.partner_id
        student = request.env['student.management'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if student:
            return request.redirect('/')
        return super().home(**kw)

    @http.route(['/my/student/profile'], type='http', auth='user', website=True)
    def student_profile(self, **kw):
        partner = request.env.user.partner_id
        student = request.env['student.management'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not student:
            return request.redirect('/my')
            
        values = self._prepare_portal_layout_values()
        values.update({
            'student': student,
            'page_name': 'student_profile',
        })
        return request.render('student_management.portal_student_profile', values)

    @http.route(['/my/student/results', '/my/student/results/page/<int:page>'], type='http', auth='user', website=True)
    def student_results(self, page=1, **kw):
        partner = request.env.user.partner_id
        student = request.env['student.management'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not student:
            return request.redirect('/my')
            
        Result = request.env['student.result']
        domain = [('student_id', '=', student.id)]
        results_count = Result.search_count(domain)
        pager = portal_pager(
            url="/my/student/results",
            total=results_count,
            page=page,
            step=10
        )
        results = Result.search(domain, limit=10, offset=pager['offset'])
        
        values = self._prepare_portal_layout_values()
        values.update({
            'results': results,
            'page_name': 'student_results',
            'pager': pager,
        })
        return request.render('student_management.portal_student_results', values)

    @http.route(['/my/student/fees', '/my/student/fees/page/<int:page>'], type='http', auth='user', website=True)
    def student_fees(self, page=1, **kw):
        partner = request.env.user.partner_id
        student = request.env['student.management'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not student:
            return request.redirect('/my')
            
        Fees = request.env['student.fees']
        domain = [('student_id', '=', student.id)]
        fees_count = Fees.search_count(domain)
        pager = portal_pager(
            url="/my/student/fees",
            total=fees_count,
            page=page,
            step=10
        )
        fees = Fees.search(domain, limit=10, offset=pager['offset'])
        
        values = self._prepare_portal_layout_values()
        values.update({
            'fees': fees,
            'page_name': 'student_fees',
            'pager': pager,
        })
        return request.render('student_management.portal_student_fees', values)

    @http.route('/my/student/fees/pay/<int:fee_id>', type='http', auth='user', website=True)
    def portal_pay_fee(self, fee_id, **kw):
        partner = request.env.user.partner_id
        student = request.env['student.management'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not student:
            return request.redirect('/my')

        fee = request.env['student.fees'].sudo().search([
            ('id', '=', fee_id),
            ('student_id', '=', student.id)
        ], limit=1)
        
        if not fee:
            return request.redirect('/my/student/fees')

        if not fee.sale_order_id and fee.state == 'draft':
            fee.action_pay()

        if fee.sale_order_id:
            return request.redirect(f'/my/orders/{fee.sale_order_id.id}')

        return request.redirect('/my/student/fees')
