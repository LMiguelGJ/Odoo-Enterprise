from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountReportsModelo(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_es.account_chart_template_pymes"):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].country_id = cls.env.ref('base.be').id
        cls.company_data['company'].currency_id = cls.env.ref('base.EUR').id
        cls.company_data['currency'] = cls.env.ref('base.EUR')

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Bidule',
            'company_id': cls.company_data['company'].id,
            'company_type': 'company',
            'country_id': cls.company_data['company'].country_id.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Crazy Product',
            'lst_price': 100.0
        })

        cls.account_income = cls.env['account.account'].create({
            'account_type': 'income',
            'name': 'Account Income',
            'code': '121020',
            'reconcile': True,
        })

        cls.report = cls.env.ref('l10n_es_reports.mod_349')

    def test_mod349_rectifications(self):
        """
            Test the rectification part of modelo 349, if an in_refund/ot_refund is found in the period :
                - if the linked original invoice is in the same period or if there is no linked invoice -> "Facturas" section
                - if the linked original invoice is before the period -> "Rectificaciones" section
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')

        # 1) we create a move in april 2019
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        # 2) The move is not reversed yet, so it should appear in the "Facturas" section on the April 2019 report
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                     1],
            [
                ('Resumen',                                                                                                                                        ''),
                ('Número total de operadores intracomunitarios',                                                                                                    1),
                ('Importe de las operaciones intracomunitarias',                                                                                               400.00),
                ('Número total de operadores intracomunitarios con rectificaciones',                                                                                0),
                ('Importe de las operaciones intracomunitarias con rectificaciones',                                                                               ''),
                ('Facturas',                                                                                                                                       ''),
                ('E. Entregas intracomunitarias',                                                                                                              400.00),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                                         ''),
                ('D. Devoluciones de mercancías previamente enviadas desde el TAI',                                                                                ''),
                ('C. Sustitución de bienes',                                                                                                                       ''),
                ('Rectificaciones',                                                                                                                                ''),
                ('E. Entregas intracomunitarias exentas',                                                                                                          ''),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Rectificaciones de las transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                  ''),
                ('D. Rectificaciones de devoluciones de mercancías previamente enviadas desde el TAI',                                                             ''),
                ('C. Rectificaciones por sustitución de bienes',                                                                                                   ''),
            ]
        )

        # 3) We reverse the move in May 2019
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'date': fields.Date.from_string('2019-05-05'),
            'refund_method': 'refund',
            'journal_id': self.company_data['default_journal_sale'].id,
        })
        reversal = move_reversal.reverse_moves()
        reversed_move = self.env['account.move'].browse(reversal['res_id'])
        # As we don't want to fully reverse the move, we only reverse 1 of the 4 products on the invoice_line
        reversed_move.invoice_line_ids.quantity = 1

        reversed_move.action_post()

        # We reconcile the 2 moves
        (invoice + reversed_move).line_ids.filtered(lambda line: line.account_id == self.account_income).reconcile()
        (invoice + reversed_move).line_ids.filtered(lambda line: line.account_id != self.account_income).reconcile()

        # 4) We change the report period to May 2019, as the rectifications must target a move in a previous period
        options = self._generate_options(self.report, '2019-05-01', '2019-05-31')

        # 5) Now, in the report of May 2019, the new balance of the move created in April 2019 is reported in the 'Rectificaciones' section
        # The new balance is computed like this : invoice.residual_amount - reversed_move.amount_total
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                    1],
            [
                ('Resumen',                                                                                                                                       ''),
                ('Número total de operadores intracomunitarios',                                                                                                   0),
                ('Importe de las operaciones intracomunitarias',                                                                                                  ''),
                ('Número total de operadores intracomunitarios con rectificaciones',                                                                               1),
                ('Importe de las operaciones intracomunitarias con rectificaciones',                                                                          300.00),
                ('Facturas',                                                                                                                                      ''),
                ('E. Entregas intracomunitarias',                                                                                                                 ''),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                    ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',         ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                   ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                               ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                  ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                           ''),
                ('R. Transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                                        ''),
                ('D. Devoluciones de mercancías previamente enviadas desde el TAI',                                                                               ''),
                ('C. Sustitución de bienes',                                                                                                                      ''),
                ('Rectificaciones',                                                                                                                               ''),
                ('E. Entregas intracomunitarias exentas',                                                                                                     300.00),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                    ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',         ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                   ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                               ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                  ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                           ''),
                ('R. Rectificaciones de las transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                 ''),
                ('D. Rectificaciones de devoluciones de mercancías previamente enviadas desde el TAI',                                                            ''),
                ('C. Rectificaciones por sustitución de bienes',                                                                                                  ''),
            ]
        )

    def test_mod349_report_change_key_on_existing_move(self):
        """ This test makes sure the report display the lines depending on the key set on the move, even if we change
            the key of an existing move.
        """
        options = self._generate_options(self.report, fields.Date.from_string('2019-04-01'), fields.Date.from_string('2019-04-30'))

        # 1) We create an invoice with the key 'E'
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        # 2) We make sure the report show the value in the 'E' line
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                    1],
            [
                ('Resumen',                                                                                                                                       ''),
                ('Número total de operadores intracomunitarios',                                                                                                   1),
                ('Importe de las operaciones intracomunitarias',                                                                                              400.00),
                ('Número total de operadores intracomunitarios con rectificaciones',                                                                               0),
                ('Importe de las operaciones intracomunitarias con rectificaciones',                                                                              ''),
                ('Facturas',                                                                                                                                      ''),
                ('E. Entregas intracomunitarias',                                                                                                             400.00),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                    ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',         ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                   ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                               ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                  ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                           ''),
                ('R. Transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                                        ''),
                ('D. Devoluciones de mercancías previamente enviadas desde el TAI',                                                                               ''),
                ('C. Sustitución de bienes',                                                                                                                      ''),
                ('Rectificaciones',                                                                                                                               ''),
                ('E. Entregas intracomunitarias exentas',                                                                                                         ''),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                    ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',         ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                   ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                               ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                  ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                           ''),
                ('R. Rectificaciones de las transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                 ''),
                ('D. Rectificaciones de devoluciones de mercancías previamente enviadas desde el TAI',                                                            ''),
                ('C. Rectificaciones por sustitución de bienes',                                                                                                  ''),
            ]
        )

        # 3) We change the key of the invoice to set it to 'R'
        invoice.update({
            'state': 'draft',
            'l10n_es_reports_mod349_invoice_type': 'R',
        })
        invoice.action_post()

        # 4) The report should now put the value in the 'R' line
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                    1],
            [
                ('Resumen',                                                                                                                                       ''),
                ('Número total de operadores intracomunitarios',                                                                                                   1),
                ('Importe de las operaciones intracomunitarias',                                                                                              400.00),
                ('Número total de operadores intracomunitarios con rectificaciones',                                                                               0),
                ('Importe de las operaciones intracomunitarias con rectificaciones',                                                                              ''),
                ('Facturas',                                                                                                                                      ''),
                ('E. Entregas intracomunitarias',                                                                                                                 ''),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                    ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',         ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                   ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                               ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                  ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                           ''),
                ('R. Transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                                    400.00),
                ('D. Devoluciones de mercancías previamente enviadas desde el TAI',                                                                               ''),
                ('C. Sustitución de bienes',                                                                                                                      ''),
                ('Rectificaciones',                                                                                                                               ''),
                ('E. Entregas intracomunitarias exentas',                                                                                                         ''),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                    ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',         ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                   ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                               ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                  ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                           ''),
                ('R. Rectificaciones de las transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                 ''),
                ('D. Rectificaciones de devoluciones de mercancías previamente enviadas desde el TAI',                                                            ''),
                ('C. Rectificaciones por sustitución de bienes',                                                                                                  ''),
            ]
        )

    def test_mod349_credit_note(self):
        """
            Test the rectification part of modelo 349, if an refund is found without linked invoice
            it still ends up in the "Rectificaciones" section.
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-03-05'),
            'invoice_date': fields.Date.from_string('2019-03-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        credit_note = invoice._reverse_moves()

        credit_note.write({
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
        })

        credit_note.action_post()

        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                     1],
            [
                ('Resumen',                                                                                                                                        ''),
                ('Número total de operadores intracomunitarios',                                                                                                    0),
                ('Importe de las operaciones intracomunitarias',                                                                                                   ''),
                ('Número total de operadores intracomunitarios con rectificaciones',                                                                                1),
                ('Importe de las operaciones intracomunitarias con rectificaciones',                                                                                400.0),
                ('Facturas',                                                                                                                                       ''),
                ('E. Entregas intracomunitarias',                                                                                                                  ''),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                                         ''),
                ('D. Devoluciones de mercancías previamente enviadas desde el TAI',                                                                                ''),
                ('C. Sustitución de bienes',                                                                                                                       ''),
                ('Rectificaciones',                                                                                                                                ''),
                ('E. Entregas intracomunitarias exentas',                                                                                                          400.00),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Rectificaciones de las transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                  ''),
                ('D. Rectificaciones de devoluciones de mercancías previamente enviadas desde el TAI',                                                             ''),
                ('C. Rectificaciones por sustitución de bienes',                                                                                                   ''),
            ]
        )

    def test_mod349_report_invoice_paid(self):
        """ This test makes sure the report numbers are correct after registering as paid an existing move.
        """
        options = self._generate_options(self.report, fields.Date.from_string('2019-04-01'), fields.Date.from_string('2019-04-30'))

        # 1) We create an invoice with the key 'E'
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        # 2) We make sure the report show the value in the 'E' line
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                     1],
            [
                ('Resumen',                                                                                                                                        ''),
                ('Número total de operadores intracomunitarios',                                                                                                    1),
                ('Importe de las operaciones intracomunitarias',                                                                                                   400.0),
                ('Número total de operadores intracomunitarios con rectificaciones',                                                                                0),
                ('Importe de las operaciones intracomunitarias con rectificaciones',                                                                               ''),
                ('Facturas',                                                                                                                                       ''),
                ('E. Entregas intracomunitarias',                                                                                                                  400.0),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                                         ''),
                ('D. Devoluciones de mercancías previamente enviadas desde el TAI',                                                                                ''),
                ('C. Sustitución de bienes',                                                                                                                       ''),
                ('Rectificaciones',                                                                                                                                ''),
                ('E. Entregas intracomunitarias exentas',                                                                                                          ''),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Rectificaciones de las transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                  ''),
                ('D. Rectificaciones de devoluciones de mercancías previamente enviadas desde el TAI',                                                             ''),
                ('C. Rectificaciones por sustitución de bienes',                                                                                                   ''),
            ]
        )

        # 3) We register payment for the invoice
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()

        # 4) We make sure the report show the same values
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                     1],
            [
                ('Resumen',                                                                                                                                        ''),
                ('Número total de operadores intracomunitarios',                                                                                                    1),
                ('Importe de las operaciones intracomunitarias',                                                                                                   400.0),
                ('Número total de operadores intracomunitarios con rectificaciones',                                                                                0),
                ('Importe de las operaciones intracomunitarias con rectificaciones',                                                                               ''),
                ('Facturas',                                                                                                                                       ''),
                ('E. Entregas intracomunitarias',                                                                                                                  400.0),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                                         ''),
                ('D. Devoluciones de mercancías previamente enviadas desde el TAI',                                                                                ''),
                ('C. Sustitución de bienes',                                                                                                                       ''),
                ('Rectificaciones',                                                                                                                                ''),
                ('E. Entregas intracomunitarias exentas',                                                                                                          ''),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Rectificaciones de las transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                  ''),
                ('D. Rectificaciones de devoluciones de mercancías previamente enviadas desde el TAI',                                                             ''),
                ('C. Rectificaciones por sustitución de bienes',                                                                                                   ''),
            ]
        )

    def test_mod349_report_operators(self):
        """ This test makes sure the report show the number of partners involved in intra-community operations
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')
        partner_b = self.env['res.partner'].create({
            'name': 'Test',
            'company_id': self.company_data['company'].id,
            'company_type': 'company',
            'country_id': self.company_data['company'].country_id.id,
        })


        # 1) We create several invoices with the key 'E'
        for partner_id in (self.partner_a | partner_b).ids * 2:
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'date': '2019-04-05',
                'invoice_date': '2019-04-05',
                'partner_id': partner_id,
                'l10n_es_reports_mod349_invoice_type': 'E',
                'line_ids': [
                    Command.create({
                        'product_id': self.product.id,
                        'account_id': self.account_income.id,
                        'quantity': 1,
                        'price_unit': self.product.lst_price,
                        'tax_ids': [],
                    }),
                ]
            })
            invoice.action_post()

        credit_note = invoice._reverse_moves()
        credit_note.write({
            'date': '2019-04-05',
            'invoice_date': '2019-04-05',
        })

        credit_note.action_post()

        # 2) We make sure the report show the value number of different partners in line 1 & 3 of the report
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                     1],
            [
                ('Resumen',                                                                                                                                        ''),
                ('Número total de operadores intracomunitarios',                                                                                                    2),
                ('Importe de las operaciones intracomunitarias',                                                                                                   300.0),
                ('Número total de operadores intracomunitarios con rectificaciones',                                                                                0),
                ('Importe de las operaciones intracomunitarias con rectificaciones',                                                                               ''),
                ('Facturas',                                                                                                                                       ''),
                ('E. Entregas intracomunitarias',                                                                                                                  300.0),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                                         ''),
                ('D. Devoluciones de mercancías previamente enviadas desde el TAI',                                                                                ''),
                ('C. Sustitución de bienes',                                                                                                                       ''),
                ('Rectificaciones',                                                                                                                                ''),
                ('E. Entregas intracomunitarias exentas',                                                                                                          ''),
                ('A. Adquisiciones intracomunitarias sujetas',                                                                                                     ''),
                ('T. Entregas en otros Estados miembros subsiguientes a adquisiciones intracomunitarias exentas en el marco de operaciones triangulares',          ''),
                ('S. Prestaciones intracomunitarias de servicios realizadas por el declarante',                                                                    ''),
                ('I. Adquisiciones intracomunitarias de servicios',                                                                                                ''),
                ('M. Entregas intracomunitarias de bienes posteriores a una importación exenta',                                                                   ''),
                ('H. Entregas intracomunitarias de bienes posteriores a una importación exenta efectuadas por el representante fiscal',                            ''),
                ('R. Rectificaciones de las transferencias de bienes realizadas en virtud de contratos de venta en consignación',                                  ''),
                ('D. Rectificaciones de devoluciones de mercancías previamente enviadas desde el TAI',                                                             ''),
                ('C. Rectificaciones por sustitución de bienes',                                                                                                   ''),
            ]
        )
