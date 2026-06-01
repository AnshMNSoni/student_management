# -*- coding: utf-8 -*-
from odoo import http
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
                # Prepare layout values manually
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


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        student = request.env['student.management'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if student:
            values['is_student'] = True
            if 'student_count' in counters:
                values['student_count'] = 1
            if 'result_count' in counters:
                values['result_count'] = request.env['student.result'].search_count([('student_id', '=', student.id)])
            if 'fees_count' in counters:
                values['fees_count'] = request.env['student.fees'].search_count([('student_id', '=', student.id)])
        else:
            values['is_student'] = False
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
