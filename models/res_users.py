from odoo import models, fields, api, Command

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.onchange('group_ids')
    def _onchange_group_ids(self):
        group_student = self.env.ref('student_management.group_student', raise_if_not_found=False)
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)
        if group_student and group_user and group_student in self.group_ids:
            self.group_ids = self.group_ids - group_user

    def _resolve_student_groups(self, vals):
        group_ids_val = vals.get('group_ids')
        if group_ids_val is None:
            return

        try:
            group_student = self.env.ref('student_management.group_student')
            group_portal = self.env.ref('base.group_portal')
            group_user = self.env.ref('base.group_user')
            group_system = self.env.ref('base.group_system')
        except ValueError:
            return

        current_group_ids = self.group_ids.ids if self else []

        final_group_ids = set(current_group_ids)
        for command in group_ids_val:
            if not isinstance(command, (list, tuple)) or len(command) < 2:
                continue
            cmd_type = command[0]
            if cmd_type == 2:
                final_group_ids.discard(command[1])
            elif cmd_type == 3:
                final_group_ids.discard(command[1])
            elif cmd_type == 4:
                final_group_ids.add(command[1])
            elif cmd_type == 5:
                final_group_ids.clear()
            elif cmd_type == 6:
                final_group_ids = set(command[2])

        if group_student.id in final_group_ids:
            final_group_ids.discard(group_user.id)
            final_group_ids.discard(group_system.id)
            final_group_ids.add(group_portal.id)
            vals['group_ids'] = [Command.set(list(final_group_ids))]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._resolve_student_groups(vals)
            email = vals.get('email') or (vals.get('login') if '@' in vals.get('login', '') else None)
            if email and not vals.get('partner_id'):
                existing_partner = self.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
                if existing_partner:
                    vals['partner_id'] = existing_partner.id
        return super().create(vals_list)

    def write(self, vals):
        self._resolve_student_groups(vals)
        return super().write(vals)
