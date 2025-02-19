# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from .common import TestInterCompanyRulesCommonSOPO
from odoo import fields
from odoo.tests import Form
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestInterCompanySaleToPurchase(TestInterCompanyRulesCommonSOPO):

    def _generate_draft_sale_order(self, company, partner, user):
        """ Generate sale order and confirm its state """
        sale_order = Form(self.env['sale.order'])
        sale_order.company_id = company
        sale_order.warehouse_id = company.warehouse_id
        sale_order.pricelist_id = self.env['product.pricelist'].search([('id', '=', 1)])
        sale_order.partner_id = partner
        sale_order.user_id = user
        sale_order.partner_invoice_id = partner
        sale_order.partner_shipping_id = partner
        sale_order = sale_order.save()

        with Form(sale_order) as so:
            with so.order_line.new() as line:
                line.name = 'Service'
                line.product_id = self.product_consultant
                line.price_unit = 450.0

        return sale_order

    def generate_sale_order(self, company, partner, user):
        sale_order = self._generate_draft_sale_order(company, partner, user)
        sale_order.action_confirm()

    def validate_generated_purchase_order(self, company, partner):
        """ Validate purchase order which has been generated from sale order
        and test its state, total_amount, product_name and product_quantity.
        """

        # I check that Quotation of purchase order and order line is same as sale order
        purchase_order = self.env['purchase.order'].search([('company_id', '=', partner.id)], limit=1)
        fp = self.env['account.fiscal.position'].with_company(partner)._get_fiscal_position(company.partner_id)

        self.assertEqual(purchase_order.state, "draft", "Invoice should be in draft state.")
        self.assertEqual(purchase_order.partner_id, company.partner_id, "Vendor does not correspond to Company %s." % company.name)
        self.assertEqual(purchase_order.company_id, partner, "Company is not correspond to purchase order.")
        self.assertEqual(purchase_order.amount_total, 517.5, "Total amount is incorrect.")
        self.assertEqual(purchase_order.order_line[0].product_id, self.product_consultant, "Product in line is incorrect.")
        self.assertEqual(purchase_order.order_line[0].name, 'Service', "Product name is incorrect.")
        self.assertEqual(purchase_order.order_line[0].price_unit, 450, "Price unit is incorrect.")
        self.assertEqual(purchase_order.order_line[0].product_qty, 1, "Product qty is incorrect.")
        self.assertEqual(purchase_order.order_line[0].price_subtotal, 450, "line total is incorrect.")
        self.assertEqual(purchase_order.fiscal_position_id, fp)
        return purchase_order

    def test_00_inter_company_sale_purchase(self):
        """ Configure "Sale/Purchase" option and then Create sale order and find related
        purchase order to related company and compare them.
        """

        # Generate sale order in company A for company B
        self.company_b.update({
            'rule_type': 'sale_purchase',
        })
        self.generate_sale_order(self.company_a, self.company_b.partner_id, self.res_users_company_a)
        # Check purchase order is created in company B ( for company A )
        self.validate_generated_purchase_order(self.company_a, self.company_b)
        # reset configuration of company B
        self.company_b.update({
            'rule_type': False,
        })

        # Generate sale order in company B for company A
        self.company_a.update({
            'rule_type': 'sale_purchase',
        })
        self.generate_sale_order(self.company_b, self.company_a.partner_id, self.res_users_company_b)
        # Check purchase order is created in company A ( for company B )
        self.validate_generated_purchase_order(self.company_b, self.company_a)
        # reset configuration of company A
        self.company_a.update({
            'rule_type': False,
        })

    def test_01_inter_company_sale_order_with_configuration(self):
        """ Configure only "Sale" option and then Create sale order and find related
        purchase order to related company and compare them.
        """

        # Generate sale order in company A for company B
        self.company_b.update({
            'rule_type': 'sale',
        })
        self.generate_sale_order(self.company_a, self.company_b.partner_id, self.res_users_company_a)
        # Check purchase order is created in company B ( for company A )
        self.validate_generated_purchase_order(self.company_a, self.company_b)
        # reset configuration of company B
        self.company_b.update({
            'rule_type': False,
        })

        # Generate sale order in company B for company A
        self.company_a.update({
            'rule_type': 'sale',
        })
        self.generate_sale_order(self.company_b, self.company_a.partner_id, self.res_users_company_b)
        # Check purchase order is created in company A ( for company B )
        self.validate_generated_purchase_order(self.company_b, self.company_a)
        # reset configuration of company A
        self.company_a.update({
            'rule_type': False,
        })

    def test_02_sale_to_purchase_without_configuration(self):
        """ Without any Configuration Create sale order and try to find related
        purchase order to related company.
        """

        # Generate sale order in company A for company B
        self.generate_sale_order(self.company_a, self.company_b.partner_id, self.res_users_company_a)
        # I check that purchase order has been created with company_b
        purchase_order = self.env['purchase.order'].search([('company_id', '=', self.company_b.id)], limit=1)
        self.assertTrue((not purchase_order), "Purchase order created for company A from Purchase order of company B without configuration")

        # Generate sale order in company A for company B
        self.generate_sale_order(self.company_b, self.company_a.partner_id, self.res_users_company_b)
        # I check that purchase order has been created with company_a
        purchase_order = self.env['purchase.order'].search([('company_id', '=', self.company_a.id)], limit=1)
        self.assertTrue((not purchase_order), "Sale order created for company B from Purchase order of company B without configuration")

    def test_03_inter_company_so_section(self):
        """ Configure "Sale/Purchase" option.
        Create a sale order which has a section line
        Find related purchase order to related company and compare them.
        """

        # Generate sale order in company A for company B
        self.company_b.update({
            'rule_type': 'sale_purchase',
        })
        so = self._generate_draft_sale_order(self.company_a, self.company_b.partner_id, self.res_users_company_a)
        so.write({
            'order_line': [(0, False, {'display_type': 'line_section', 'name': 'Great Section'})]
        })
        so.action_confirm()
        self.assertEqual(len(so.order_line), 2)
        # Check purchase order is created in company B ( for company A )
        po = self.validate_generated_purchase_order(self.company_a, self.company_b)
        self.assertEqual(len(po.order_line), 2)

    def test_04_inter_company_auto_validation(self):
        """ Configure "Sale/Purchase" option and tick auto validation.
        Find related purchase order to related company and confirm it.
        """
        # Create a product in 'Auto Purchase' to by in company B
        my_service = self.env['product.product'].create({
            'name': 'my service',
            'type': 'service',
            'service_to_purchase': True,
            'seller_ids': [(0, 0, {'partner_id': self.company_b.partner_id.id, 'price': 100, 'company_id': self.company_a.id})]
        })

        self.company_b.update({
            'rule_type': 'sale_purchase',
            'auto_validation': True,
        })
        # Generate sale order in company A for company B
        partner_a = self.env['res.partner'].create({
            'name': 'partner_a',
            'company_id': False,
        })
        so = self._generate_draft_sale_order(self.company_a, partner_a, self.res_users_company_a)
        so.order_line.product_id = my_service
        so.order_line.product_uom = my_service.uom_id
        so.with_user(self.res_users_company_a).action_confirm()
        # Check purchase order is created in company B ( for company A )
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.company_b.partner_id.id)], limit=1)
        self.assertTrue(purchase_order)
        purchase_order.with_user(self.res_users_company_a).button_confirm()

    def test_05_inter_company_delivery_date(self):
        """ Ensures the SO's commitment date is properly reflected on the PO's expected arrival.
        """
        today = fields.Datetime.today()
        self.company_b.update({
            'rule_type': 'sale',
        })

        sale_order = self._generate_draft_sale_order(self.company_a, self.company_b.partner_id, self.res_users_company_a)
        sale_order.commitment_date = today + relativedelta(days=7)
        sale_order.with_user(self.res_users_company_a).action_confirm()

        purchase_order = self.env['purchase.order'].search([('company_id', '=', self.company_b.id)], limit=1)
        self.assertEqual(purchase_order.date_planned, today + relativedelta(days=7))

    def test_sale_to_specific_partner(self):
        """
        Classic intercompany SO-PO on company C2. C1 sells to a child of C2. It
        should still create a PO on C2 side.
        """
        self.company_b.rule_type = 'sale_purchase'
        partner_b = self.env['res.partner'].create({
            'name': 'SuperPartner',
            'parent_id': self.company_b.partner_id.id,
        })
        so = self._generate_draft_sale_order(self.company_a, partner_b, self.res_users_company_a)
        so.with_user(self.res_users_company_a).action_confirm()
        purchase_order = self.env['purchase.order'].sudo().search([('partner_id', '=', self.company_a.partner_id.id)], limit=1)
        self.assertEqual(purchase_order.company_id, self.company_b)
