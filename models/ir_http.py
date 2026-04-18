from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _frontend_pre_dispatch(cls):
        """Override to use the logged-in user's preferred language on portal pages.

        By default, Odoo resolves the frontend language from (1) URL prefix,
        (2) ``frontend_lang`` cookie, (3) context, (4) default partner lang
        (usually en_US).  Between ``_match`` (where cookies are read) and
        ``_pre_dispatch`` (where the template context is set), the resolved
        language can be lost because these run in separate DB transactions.

        This override detects an authenticated, non-public user on a frontend
        page and applies the user's stored language preference so that portal
        templates are always rendered in the correct language.
        """
        if request.is_frontend and request.session.uid:
            user_lang = request.env['res.users'].sudo().browse(
                request.session.uid
            ).lang
            if user_lang:
                lang_data = request.env['res.lang']._get_data(code=user_lang)
                if lang_data:
                    request.lang = lang_data

        super()._frontend_pre_dispatch()
