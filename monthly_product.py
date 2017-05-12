# -*- coding: utf-8 -*-
import logging
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp.osv import fields, osv, expression

from datetime import datetime
import time
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import timedelta, date

import calendar
import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)

_get_stock_options = [(u'期初销售出库', u'期初销售出库'),
                      (u'期初销售退货', u'期初销售退货'),
                      (u'期初销售订单', u'期初销售订单'),
                      (u'期初采购入库', u'期初采购入库'),
                      (u'期初采购退货', u'期初采购退货'),
                      (u'期初采购订单', u'期初采购订单'),
                      (u'期初借入', u'期初借入'),
                      (u'期初借入还出', u'期初借入还出'),
                      (u'期初借出', u'期初借出'),
                      (u'期初借出还入', u'期初借出还入'),
                      (u'期初数量', u'期初数量'),
                      (u'期初委外出库单', u'期初委外出库单'),
                      (u'期初委外出库还入单', u'期初委外出库还入单'),
                      (u'现有委外出库单', u'现有委外出库单'),
                      (u'现有委外出库还入单', u'现有委外出库还入单'),
                      (u'现有借出', u'现有借出'),
                      (u'现有借出还入', u'现有借出还入'),
                      (u'现有借入', u'现有借入'),
                      (u'现有借入还出', u'现有借入还出'),
                      (u'生产领料', u'生产领料'),
                      (u'生产计划领料', u'生产计划领料'),
                      (u'生产入库', u'生产入库'),
                      (u'生产计划入库', u'生产计划入库'),
                      (u'生产退料', u'生产退料'),
                      (u'盘点', u'盘点'),
                      (u'销售出库', u'销售出库'),
                      (u'销售退货', u'销售退货'),
                      (u'采购入库', u'采购入库'),
                      (u'采购退货', u'采购退货'),
                      (u'采购样品入库', u'采购样品入库'),
                      (u'采购样品退货', u'采购样品退货'),
                      (u'仓库调拨', u'仓库调拨'),
                      (u'采购订单', u'采购订单'),
                      (u'期初采购订单', u'期初采购订单'),
                      (u'期初销售订单', u'期初销售订单'),
                      (u'销售订单', u'销售订单'),
                      (u'电商订单', u'电商订单'),
                      (u'采购样品订单', u'采购样品订单'),
                      (u'销售样品订单', u'销售样品订单'),
                      (u'销售样品出库', u'销售样品出库'),
                      (u'销售样品退货', u'销售样品退货'),
                      ]


class stock_move(osv.Model):
    _inherit = 'stock.move'

    _columns = {
        'amount_total': fields.float(u'含税金额', ),
        'amount_untaxed': fields.float(u'不含税金额', ),
    }


class product_product(osv.osv):
    _inherit = "product.product"

    _columns = {
    }

    def but_monthly_product(self, cr, uid, ids, context=None):
        """
        创建一个产品全年的结算
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        self._monthly_product(cr, uid, ids, context)

        return True

    def _monthly_product(self, cr, uid, ids, context=None):

        product = self.pool.get('product.product').browse(cr, uid, ids, context=context)
        statistics_obj = self.pool.get('product.monthly.statistics')

        monthly_obj = self.pool.get('product.monthly')
        monthly_ids = monthly_obj.search(cr, uid, [], context=context)

        for id in monthly_ids:
            o = monthly_obj.browse(cr, uid, id, context)
            for m in o.period_ids:
                for p in product:
                    statistics_id = statistics_obj.search(cr, uid,
                                                          [('monthly_id', '=', m.id), ('product_id', '=', p['id'])],
                                                          context=context)
                    if len(statistics_id) == 0:
                        parm = {
                            # 'warehouse_id': o.warehouse_id.id,
                            'monthly_id': m.id,
                            'product_id': p['id'],
                        }
                        statistics_obj.create(cr, uid, parm, context=context)
        return True


class product_pool(osv.Model):
    _name = "product.pool"
    _description = u"不同类型的库位"

    _columns = {
        'name': fields.char(u'名称', ),
        'location_ids': fields.one2many('product.pool.line', 'product_pool_id', u'明细', copy=True),
        'company_id': fields.many2one('res.company', u'公司', required=True, ),
        'warehouse_id': fields.many2one('stock.warehouse', u'仓库', ),

    }
    _defaults = {
        'name': u'库位配置',
        # 'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

    def but_company_pool(self, cr, uid, ids, context=None):
        pool_line_obj = self.pool.get('product.pool.line')
        picking_type_obj = self.pool.get('stock.picking.type')
        o = self.browse(cr, uid, ids, context=context)
        pool_line_obj.unlink(cr, uid, o.location_ids.ids, context=context)

        # type_ids = picking_type_obj.search(cr, uid, [('warehouse_id', '=', o.warehouse_id.id)], context=context)
        type_ids = picking_type_obj.search(cr, uid, [], context=context)

        picking_type = picking_type_obj.browse(cr, uid, type_ids)
        pool_line_obj_dict = {}
        for options in _get_stock_options:
            options_temp = options[0]
            print options_temp

            stock_options_arr = []
            for line in picking_type:
                if line.initial == options_temp:
                    dest_id = line.default_location_dest_id.id
                    if pool_line_obj_dict.has_key((options_temp, dest_id)):
                        continue
                    pool_line_obj_dict[(options_temp, dest_id)] = {
                        "temp": True,
                    }
                    stock_options_arr.append(line.default_location_dest_id.id)
            if len(stock_options_arr) > 0:
                parm = {
                    'product_pool_id': ids[0],
                    'initial': options_temp,
                    'location_ids': [(6, 0, stock_options_arr)],
                }
                pool_line_obj.create(cr, uid, parm, context=context)

        return True

    _sql_constraints = [
        ('company_id_uniq', 'unique(company_id)', u'公司必须唯一!'),
    ]


class product_pool_line(osv.Model):
    _name = "product.pool.line"
    _description = u"库位明细"

    _columns = {
        'name': fields.char(u'备注'),
        'initial': fields.selection(_get_stock_options, u'库位类型', select=True),
        'location_ids': fields.many2many('stock.location', 'stock_location_product_pool_line_rel', 'a_id', 'b_id',
                                         u'库位', copy=True),
        'product_pool_id': fields.many2one('product.pool', u'库位', required=True, select=True),

    }


class product_monthly(osv.osv):
    _name = "product.monthly"
    _description = u"客户回收年度"
    _columns = {
        'name': fields.char(u'会计年度', required=True, states={'done': [('readonly', True)]}, help=u'只能输入年份数字如:2015'),
        'code': fields.integer(u'编码', required=True, states={'done': [('readonly', True)]}),
        'company_id': fields.many2one('res.company', u'公司', required=True, states={'done': [('readonly', True)]}),
        'date_start': fields.date(u'开始日期', required=True, states={'done': [('readonly', True)]}),
        'date_stop': fields.date(u'结束日期', required=True, states={'done': [('readonly', True)]}),
        'period_ids': fields.one2many('product.monthly.line', 'fiscalyear_id', u'期',
                                      states={'done': [('readonly', True)]}),
        'warehouse_id': fields.many2one('stock.warehouse', u'仓库', ),
        'pool_id': fields.many2one('product.pool', u'产品库位', ),
        'state': fields.selection([('draft', u'打开'), ('done', u'已确认')], u'状态', readonly=True, copy=False),

    }

    def _default_name(self, cr, uid, context=None):
        import datetime
        try:
            return datetime.date.today().year
        except:
            return False

    def _default_date_start(self, cr, uid, context=None):
        import datetime
        try:
            return str(datetime.date.today().year) + '-01-01'
        except:
            return False

    def _default_date_stop(self, cr, uid, context=None):
        import datetime
        try:
            return str(datetime.date.today().year) + '-12-%s' % calendar.monthrange(datetime.date.today().year, 12)[1]
        except:
            return False

    _defaults = {
        'state': 'draft',
        'name': _default_name,
        'date_start': _default_date_start,
        'date_stop': _default_date_stop,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    _order = "date_start, id"

    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state != 'draft':
                raise osv.except_osv(u'提醒', u'只能删除草稿')
        return super(product_monthly, self).unlink(cr, uid, ids, context)

    def _check_duration(self, cr, uid, ids, context=None):
        obj_fy = self.browse(cr, uid, ids[0], context=context)
        if obj_fy.date_stop < obj_fy.date_start:
            return False
        return True

    _constraints = [
        (_check_duration, u'提醒!\n开始日期必须在其结束日期之前.',
         ['date_start', 'date_stop'])
    ]

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        vals['code'] = vals.get('name', '/')
        new_id = super(product_monthly, self).create(cr, uid, vals, context=context)
        return new_id

    def write(self, cr, uid, ids, data, context=None):
        # if data.get('name', '/'):
        # data['code'] = data.get('name', '/')
        result = super(product_monthly, self).write(cr, uid, ids, data, context=context)
        return result

    def action_draft(self, cr, uid, ids, context=None):
        state = 'draft'
        self.write(cr, uid, ids, {'state': state}, context=context)
        return True

    def bnt_done(self, cr, uid, ids, context=None):
        state = 'done'
        self.write(cr, uid, ids, {'state': state}, context=context)
        return True

    def create_period3(self, cr, uid, ids, context=None):
        return self.create_period(cr, uid, ids, context, 3)

    def create_period(self, cr, uid, ids, context=None, interval=1):
        period_obj = self.pool.get('product.monthly.line')
        for fy in self.browse(cr, uid, ids, context=context):
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
            parent_id = False
            while ds.strftime('%Y-%m-%d') < fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)
                if de.strftime('%Y-%m-%d') > fy.date_stop:
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')
                parent_id = period_obj.create(cr, uid, {
                    'name': ds.strftime('%Y-%m'),
                    'code': ds.strftime('%Y%m'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                    'pool_id': fy.pool_id.id,
                    'parent_id': parent_id,

                })
                ds = ds + relativedelta(months=interval)
        return True

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if args is None:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        ids = self.search(cr, user, expression.AND([domain, args]), limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)

    #:::::::::::: 定时任务
    def _product_monthly_settings(self, cr, uid, ids=False, context=None):
        #:::找出现在使用的规则 先找年，再找月
        date = time.strftime('%Y')
        obj = self.pool.get('product.monthly')
        ids = obj.search(cr, uid, [('code', '=', date)], context=context)
        if ids:
            o = self.browse(cr, uid, ids[0])
            if o.settings_id:
                self.perform_actions(cr, uid, o.settings_id.id, context=context)
            else:
                for line in o.period_ids:
                    self.perform_actions(cr, uid, line.settings_id.id, context=context)

        return self.perform_actions(cr, uid, ids, context=context)

    def perform_actions(self, cr, uid, id, context=None):
        return True

    def get_day_of_day(self, n=0):
        if (n < 0):
            n = abs(n)
            return date.today() - timedelta(days=n)
        else:
            return date.today() + timedelta(days=n)

    def datediff(self, Maximum_date, Minimum_date):
        '''
        两个日期之间的天数
        :param Maximum_date:
        :param Minimum_date:
        :return:
        '''

        format = "%Y-%m-%d";
        now = datetime.now()
        if Maximum_date == None:
            Maximum_date = datetime.strptime(now.strftime(format), format)

        else:
            Maximum_date = datetime.strptime(Maximum_date, format)
        Minimum_date = datetime.strptime(Minimum_date, format)
        return abs(Maximum_date - Minimum_date).days

    def all_product(self, cr, uid, ids, context=None):
        obj = self.pool.get('product.monthly.statistics')

        #:::::开始日期
        # starttime = datetime.datetime.now()

        for id in ids:
            o = self.browse(cr, uid, id, context)
            list_ids = []
            for m in o.period_ids:
                list_ids.append(m.id)
            if len(list_ids) == 0:
                continue
            period_ids_t = tuple(list_ids)
            product_sql = """select p.id from product_product p
                             LEFT JOIN product_monthly_statistics ss on ss.monthly_id in %s and ss.product_id=p.id
                             where ss.product_id is null """
            cr.execute(product_sql, (period_ids_t,))
            product_ids = cr.fetchall()
            if len(product_ids) == 0:
                continue
            product_seach_ids = []
            for p_id in product_ids:
                product_seach_ids.append(p_id[0])
            product = self.pool.get('product.product').search_read(cr, uid, [('id', 'in', product_seach_ids)], ['name'],
                                                                   context=context)
            for m in o.period_ids:
                if m.beginning == True:
                    for p in product:
                        statistics_id = obj.search(cr, uid, [('monthly_id', '=', m.id), ('product_id', '=', p['id'])],
                                                   context=context)
                        if len(statistics_id) == 0:
                            # parm = {
                            #     'monthly_id': m.id,
                            #     'product_id': p['id'],
                            #     'warehouse_id': o.warehouse_id.id,
                            # }
                            monthly_id = m.id
                            product_id = p['id']
                            # new_id = obj.create(cr, uid, parm, context)
                            sql = "INSERT INTO product_monthly_statistics (company_id,name,monthly_id, product_id) VALUES ( %s, %s, %s, %s) " % (
                                m.company_id.id, o.id, monthly_id, product_id)
                            cr.execute(sql)
                            # print new_id
        #::::::结束日期
        # endtime = datetime.datetime.now()
        # print u"用时 %s 秒" % (endtime - starttime).seconds

        return True

    def year_product_average(self, cr, uid, ids, context=None):
        #::::产品计算每月的数量
        obj = self.pool.get('product.monthly.statistics')

        self.product_amount_total(cr, uid, ids, context=context)

        product = self.pool.get('product.product').search_read(cr, uid, [], ['name'], context=context)
        # now = time.time()
        # timeArray = time.localtime(now)
        # print time.strptime('%Y-%m-%d %H:%M:%S',timeArray),u'curr  month start'
        for id in ids:
            o = self.browse(cr, uid, id, context)
            for m in o.period_ids:
                if m.state == 'done':
                    continue
                for p in product:
                    # if p['id'] <> 28:
                    #     continue
                    statistics_id = obj.search(cr, uid, [('monthly_id', '=', m.id), ('product_id', '=', p['id'])],
                                               context=context)
                    if len(statistics_id) > 0:
                        obj.but_inventory_month_qty(cr, uid, statistics_id, context=None)
        return True

    def product_amount_total(self, cr, uid, ids, context=None):
        #::::计算所有产品的含税金额与不含税金额
        """
        tax_sale 销售税率
        tax_purchase 采购税率
        tax_sale_price_include 销售是否内含税
        tax_purchase_price_include 采购是否内含税
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        date_start = None
        date_stop = None
        for id in ids:
            o = self.browse(cr, uid, id, context)
            for m in o.period_ids:
                if m.state == 'done':
                    continue
                else:
                    date_start = m.date_start  # 开始日期
                    date_stop = m.date_stop  # 结束日期

        tax = self.pool.get('account.tax').search_read(cr, 1, [], ['id', 'type_tax_use', 'amount', 'price_include'],
                                                       context=context)

        for line in tax:
            tax_sale = tax_purchase = 0
            tax_sale_price_include = tax_purchase_price_include = False
            #::::::::计算含税价 如果是销售
            if line['type_tax_use'] == 'sale':
                tax_sale = line['amount']
                tax_sale_price_include = line['price_include']

                # 'amount_total': fields.float(u'含税金额', ),
                # 'amount_untaxed': fields.float(u'不含税金额', )

                # 价内税：税款=货款（销售款）×税率＝含税价格×税率
                # 价外税：税款=[货款/（1+税率）]×税率=不含税价格×税率
                # 我国目前的流转税中，增值税采用价外税模式

                amount_total = amount_untaxed = 0.00

                initial = u"('销售出库', '销售退货','销售样品出库', '销售样品退货')"

                if tax_sale_price_include == True:
                    # amount_total = m['product_uom_qty'] * m['price_unit']
                    # amount_untaxed = amount_total / (1 + tax_sale)
                    cr.execute(
                        "UPDATE stock_move SET amount_total=product_uom_qty*price_unit,amount_untaxed=(product_uom_qty*price_unit)/(1 + %s) WHERE initial in %s and price_unit>0 AND sale_line_id IN ( SELECT sol.ID FROM sale_order_line sol LEFT JOIN sale_order_tax sot ON sol.ID = sot.order_line_id LEFT JOIN account_tax AT ON sot.tax_id = AT .ID WHERE sol.ID IN ( SELECT sale_line_id FROM stock_move WHERE write_date >=to_date('%s','YYYY-MM-DD') AND write_date <=to_date('%s','YYYY-MM-DD') ) AND AT .ID = %s )" % (
                            tax_sale, initial, date_start, date_stop, line['id']))
                else:
                    # amount_untaxed = m['product_uom_qty'] * m['price_unit']
                    # amount_total = (m['product_uom_qty'] * m['price_unit']) * tax_sale + amount_untaxed
                    cr.execute(
                        "UPDATE stock_move SET amount_untaxed=product_uom_qty*price_unit,amount_total=product_uom_qty*price_unit*%s+product_uom_qty*price_unit WHERE initial in %s and price_unit>0 AND sale_line_id IN ( SELECT sol.ID FROM sale_order_line sol LEFT JOIN sale_order_tax sot ON sol.ID = sot.order_line_id LEFT JOIN account_tax AT ON sot.tax_id = AT .ID WHERE sol.ID IN ( SELECT sale_line_id FROM stock_move WHERE write_date >=to_date('%s','YYYY-MM-DD') AND write_date <=to_date('%s','YYYY-MM-DD') ) AND AT .ID = %s )" % (
                            tax_sale, initial, date_start, date_stop, line['id']))
            #::::::::计算含税价 如果是采购
            if line['type_tax_use'] == 'purchase':
                tax_purchase = line['amount']
                tax_purchase_price_include = line['price_include']
                initial = u"('采购入库','采购样品入库', '采购样品退货', '盘点', '仓库调拨')"
                initial2 = u"( '采购退货')"
                if tax_purchase_price_include == True:
                    # amount_total = m['product_uom_qty'] * m['price_unit']
                    # amount_untaxed = amount_total / (1 + tax_purchase)
                    cr.execute(
                        "UPDATE stock_move SET amount_total=product_uom_qty*price_unit,amount_untaxed=(product_uom_qty*price_unit)/(1 + %s) WHERE initial in %s and price_unit>0 AND purchase_line_id IN ( SELECT sol.ID FROM purchase_order_line sol LEFT JOIN purchase_order_taxe sot ON sol.ID = sot.ord_id  LEFT JOIN account_tax AT ON sot.tax_id = AT .ID WHERE sol.ID IN ( SELECT purchase_line_id FROM stock_move WHERE write_date >=to_date('%s','YYYY-MM-DD') AND write_date <=to_date('%s','YYYY-MM-DD') ) AND AT .ID = %s )" % (
                            tax_purchase, initial, date_start, date_stop, line['id']))
                    # 采购退货
                    cr.execute(
                        "UPDATE stock_move SET amount_total=product_uom_qty*price_unit,amount_untaxed=(product_uom_qty*price_unit)/(1 + %s) WHERE initial in %s and price_unit>0 AND purchase_returned_move_id  IN ( SELECT sol.ID FROM purchase_order_line sol LEFT JOIN purchase_order_taxe sot ON sol.ID = sot.ord_id  LEFT JOIN account_tax AT ON sot.tax_id = AT .ID WHERE sol.ID IN ( SELECT purchase_returned_move_id  FROM stock_move WHERE write_date >=to_date('%s','YYYY-MM-DD') AND write_date <=to_date('%s','YYYY-MM-DD') ) AND AT .ID = %s)" % (
                            tax_purchase, initial2, date_start, date_stop, line['id']))
                else:
                    # amount_untaxed = m['product_uom_qty'] * m['price_unit']
                    # amount_total = (m['product_uom_qty'] * m['price_unit']) * tax_purchase + amount_untaxed
                    cr.execute(
                        "UPDATE stock_move SET amount_untaxed=product_uom_qty*price_unit,amount_total=product_uom_qty*price_unit*%s+product_uom_qty*price_unit WHERE initial in %s and price_unit>0 AND purchase_line_id IN ( SELECT sol.ID FROM purchase_order_line sol LEFT JOIN purchase_order_taxe sot ON sol.ID = sot.ord_id  LEFT JOIN account_tax AT ON sot.tax_id = AT .ID WHERE sol.ID IN ( SELECT purchase_line_id FROM stock_move WHERE write_date >=to_date('%s','YYYY-MM-DD') AND write_date <=to_date('%s','YYYY-MM-DD') ) AND AT .ID = %s )" % (
                            tax_purchase, initial, date_start, date_stop, line['id']))
                    # 采购退货
                    cr.execute(
                        "UPDATE stock_move SET amount_untaxed=product_uom_qty*price_unit,amount_total=product_uom_qty*price_unit*%s+product_uom_qty*price_unit WHERE initial in %s and price_unit>0 AND purchase_returned_move_id  IN ( SELECT sol.ID FROM purchase_order_line sol LEFT JOIN purchase_order_taxe sot ON sol.ID = sot.ord_id  LEFT JOIN account_tax AT ON sot.tax_id = AT .ID WHERE sol.ID IN ( SELECT purchase_returned_move_id  FROM stock_move WHERE write_date >=to_date('%s','YYYY-MM-DD') AND write_date <=to_date('%s','YYYY-MM-DD') ) AND AT .ID = %s)" % (
                            tax_purchase, initial2, date_start, date_stop, line['id']))
        return True


class product_monthly_line(osv.osv):
    _name = "product.monthly.line"
    _description = u"月期间"
    _columns = {
        'name': fields.char(u'月期间 ', required=True, states={'done': [('readonly', True)]}),
        'code': fields.integer(u'编码 ', states={'done': [('readonly', True)]}),
        'special': fields.boolean(u'开始/结束期间 ', states={'done': [('readonly', True)]}),
        'date_start': fields.date(u'会计期间开始于', required=True, states={'done': [('readonly', True)]}),
        'date_stop': fields.date(u'结束会计期间', required=True, states={'done': [('readonly', True)]}),
        'fiscalyear_id': fields.many2one('product.monthly', u'回收年度', required=True,
                                         states={'done': [('readonly', True)]}, select=True, ondelete='cascade'),
        'state': fields.selection([('draft', u'开放'), ('done', u'关闭')], u'状态', readonly=True, copy=False, ),
        'company_id': fields.related('fiscalyear_id', 'company_id', type='many2one', relation='res.company',
                                     string=u'公司', store=True, readonly=True),
        'pool_id': fields.many2one('product.pool', u'产品库位', ),
        'parent_id': fields.many2one('product.monthly.line', u'上月', ),
        'beginning': fields.boolean(u'是否创建月结产品'),

    }
    _defaults = {
        'state': 'draft',
        'beginning': True,
    }
    _order = "date_start, special desc"
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', u'名称与公司必须唯一'),
    ]

    def all_product(self, cr, uid, ids, context=None):

        #::::本月所有月结产品
        product = self.pool.get('product.product').search_read(cr, uid, [], ['name'], context=context)

        for id in ids:
            m = self.browse(cr, uid, id, context)
            # 1 zqw add 2016-01-04 修改生成月结产品问题,比如产品A是2015年12月第一次采购的产品（新开发的产品），在2015年11月并没有该产品
            # 2 并不是所有月份都要重新生成一遍产品月结，根据需要生成
            if m.state == 'done':
                continue
            obj = self.pool.get('product.monthly.statistics')
            for p in product:
                statistics_id = obj.search(cr, uid, [('monthly_id', '=', m.id), ('product_id', '=', p['id'])],
                                           context=context)

                if len(statistics_id) == 0:
                    parm = {
                        'monthly_id': m.id,
                        'product_id': p['id'],
                        # 'warehouse_id': m.fiscalyear_id.warehouse_id.id,
                    }
                    new_id = obj.create(cr, uid, parm, context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.fiscalyear_id.state != 'draft':
                raise osv.except_osv(u'提醒', u'只能删除草稿')
        return super(product_monthly_line, self).unlink(cr, uid, ids, context)

    def _check_duration(self, cr, uid, ids, context=None):
        obj_period = self.browse(cr, uid, ids[0], context=context)
        if obj_period.date_stop < obj_period.date_start:
            return False
        return True

    def _check_year_limit(self, cr, uid, ids, context=None):
        for obj_period in self.browse(cr, uid, ids, context=context):
            if obj_period.special:
                continue

            if obj_period.fiscalyear_id.date_stop < obj_period.date_stop or \
                            obj_period.fiscalyear_id.date_stop < obj_period.date_start or \
                            obj_period.fiscalyear_id.date_start > obj_period.date_start or \
                            obj_period.fiscalyear_id.date_start > obj_period.date_stop:
                return False

            pids = self.search(cr, uid,
                               [('date_stop', '>=', obj_period.date_start), ('date_start', '<=', obj_period.date_stop),
                                ('special', '=', False), ('id', '<>', obj_period.id)])
            for period in self.browse(cr, uid, pids):
                if period.fiscalyear_id.company_id.id == obj_period.fiscalyear_id.company_id.id:
                    return False
        return True

    _constraints = [
        (_check_duration, u'错误!\n期间错误.', ['date_stop']),
        (_check_year_limit,
         u'错误!\n无效期间,或不在有效的年度中.',
         ['date_stop'])
    ]

    def action_draft(self, cr, uid, ids, context=None):
        state = 'draft'
        self.write(cr, uid, ids, {'state': state}, context=context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        state = 'done'
        self.write(cr, uid, ids, {'state': state}, context=context)
        return True

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if args is None:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        ids = self.search(cr, user, expression.AND([domain, args]), limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        return super(product_monthly_line, self).write(cr, uid, ids, vals, context=context)

    def close_monthly(self, cr, uid, ids, context=None):

        o = self.browse(cr, uid, ids)
        if o.state == 'draft':
            self.write(cr, uid, ids, {'state': 'done'}, context=context)
        else:
            self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        return True


class product_monthly_statistics(osv.osv):
    _name = "product.monthly.statistics"
    _description = u"客户回收期间"

    def _amount_all_product(self, cr, uid, ids, field_name, arg, context=None):
        return self._amount_all(cr, uid, ids, field_name, arg, context=context)

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        pool_obj = self.pool.get('product.pool')
        stock_obj = self.pool.get('stock.move')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'purchase_month_qty': 0.0,
            }
            # product_location_ids = pool_obj.browse(cr, uid, order.company_id.id)
            # for location in product_location_ids.location_ids:
            #     if location.initial == '采购入库':
            #         print location.location_ids._ids,'-----差一个库位类型-------'
            # cr.execute(
            #     "select sum(a.product_uom_qty) from stock_move as a inner join stock_picking as b on a.picking_id = b.id and a.state='done' and a.product_id = %s and a.product_id = %s and date_done >='%s' and  date_done <='%s' " % (
            #         order.product_id.id, order.monthly_id.date_start, order.monthly_id.date_stop))
            # res[order.id]['purchase_month_qty'] = cr.fetchone()[0] or 0.0
        return res

    _columns = {
        'warehouse_id': fields.many2one('stock.warehouse', u'仓库', ),
        'product_id': fields.many2one('product.product', u'产品'),
        'image': fields.related("product_id", "image", type="binary", string=u"图片", ),
        'uom_id': fields.related('product_id', 'uom_id', type="many2one", relation="product.uom", string=u"单位",
                                 readonly=True),
        'monthly_id': fields.many2one('product.monthly.line', u'月份'),

        'name': fields.related('monthly_id', 'fiscalyear_id', type="many2one", relation="product.monthly",
                               string=u"年份", store=True),
        'company_id': fields.related('monthly_id', 'company_id', type="many2one", relation="res.company",
                                     string=u"公司", store=True),
        # 入库数量
        'mrp_month_in_qty': fields.float(u'本月生产入库数量', digits=(16, 2), ),
        'overage_month_in_qty': fields.float(u'本月盘盈数量', digits=(16, 2), ),
        'overage_month_in_amount': fields.float(u'本月盘盈金额', digits=(16, 2), ),
        'lend_month_in_qty': fields.float(u'本月借入数量', digits=(16, 2), ),
        'lend_also_month_in_qty': fields.float(u'本月借出还入数量', digits=(16, 2), ),
        'outsourcing_month_in_qty': fields.float(u'本月委外数量(入)', digits=(16, 2), ),
        'sale_sample_month_in_qty': fields.float(u'本月销售样品退货数量(入)', digits=(16, 2), ),
        'sale_sample_month_in_amount': fields.float(u'本月销售样品退货金额', digits=(16, 2), ),
        'purchase_sample_month_in_qty': fields.float(u'本月采购样品入库', digits=(16, 2), ),
        'purchase_sample_month_in_amount': fields.float(u'本月采购样品金额', digits=(16, 2), ),
        'purchase_month_in_qty': fields.float(u'本月采购入库', digits=(16, 2), ),
        'purchase_month_in_amount': fields.float(u'本月采购金额', digits=(16, 2), ),
        'sale_month_in_qty': fields.float(u'本月销售销售退货', digits=(16, 2), ),
        'sale_month_in_amount': fields.float(u'本月销售销售金额', digits=(16, 2), ),
        'stock_allocation_month_in_qty': fields.float(u'本月仓库调拨(入)', digits=(16, 2), ),
        'stock_allocation_month_in_amount': fields.float(u'本月仓库调拨(入)金额', digits=(16, 2), ),

        # 出库数量
        'sale_month_out_qty': fields.float(u'本月销售出库数量', digits=(16, 2), ),
        'sale_month_out_amount': fields.float(u'本月销售出库金额', digits=(16, 2), ),
        'sale_sample_month_out_qty': fields.float(u'本月销售样品出库', digits=(16, 2), ),
        'sale_sample_month_out_amount': fields.float(u'本月销售样品出库金额', digits=(16, 2), ),
        'purchase_sample_month_out_qty': fields.float(u'本月采购样品退货', digits=(16, 2), ),
        'purchase_sample_month_out_amount': fields.float(u'本月采购样品退货', digits=(16, 2), ),
        'purchase_month_out_qty': fields.float(u'本月采购退货', digits=(16, 2), ),
        'purchase_month_out_amount': fields.float(u'本月采购退货金额', digits=(16, 2), ),
        'mrp_month_out_qty': fields.float(u'本月生产领料数量', digits=(16, 2), ),
        'loss_month_qty': fields.float(u'本月盘亏数量', digits=(16, 2), ),
        'loss_month_amount': fields.float(u'本月盘亏金额', digits=(16, 2), ),
        'lend_month_out_qty': fields.float(u'本月借出数量', digits=(16, 2), ),
        'lend_also_month_out_qty': fields.float(u'本月借入还出数量', digits=(16, 2), ),
        'outsourcing_month_out_qty': fields.float(u'本月委外数量(出)', digits=(16, 2), ),
        'stock_allocation_month_out_qty': fields.float(u'本月仓库调拨(出)', digits=(16, 2), ),
        'stock_allocation_month_out_amount': fields.float(u'本月仓库调拨(出)金额', digits=(16, 2), ),

        # 上月结存
        'last_month_qty': fields.float(u'上月结存数量', digits=(16, 2), ),
        'last_month_amount': fields.float(u'上月结存金额', digits=(16, 2), ),
        'last_month_qty_price_unit': fields.float(u'上月加权平均', digits_compute=dp.get_precision('Product Price')),

        # 本月结存
        'inventory_month_qty': fields.float(u'本月结存数量', digits=(16, 2), ),
        'inventory_month_amount': fields.float(u'本月结存金额', digits=(16, 2), ),
        'inventory_month_qty_price_unit': fields.float(u'本月加权平均', digits_compute=dp.get_precision('Product Price')),

        'price_changes': fields.float(u'下月期初平均价格', digits_compute=dp.get_precision('Product Price'), ),
        'state': fields.selection([('draft', u'开放'), ('done', u'关闭')], u'状态', readonly=True, copy=False, ),

        # 上月折扣
        'discount_last_month_qty': fields.float(u'上月折扣数量', digits=(16, 2), ),
        'discount_last_month_amount': fields.float(u'上月折扣金额', digits=(16, 2), ),
        'discount_last_month_qty_price_unit': fields.float(u'上月折扣加权平均',
                                                           digits_compute=dp.get_precision('Product Price')),

        # 本月折扣
        'discount_inventory_month_qty': fields.float(u'本月折扣数量', digits=(16, 2), ),
        'discount_inventory_month_amount': fields.float(u'本月折扣金额', digits=(16, 2), ),
        'discount_inventory_month_qty_price_unit': fields.float(u'本月折扣加权平均',
                                                                digits_compute=dp.get_precision('Product Price')),

        # 产品天结明细
        'statistics_line': fields.one2many('product.monthly.statistics.line', 'statistics_id', '天结明细' ,copy=True),
    }



    #::::本月结存
    def but_inventory_month_qty(self, cr, uid, ids, context=None):
        #:::所有数量重新计算 最后再读取一次汇总
        date_local = datetime.now()
        date_local_day = (str(date_local))[0:10]
        print '20170505-----------111111111111',ids
        for id in ids:
            o = self.browse(cr, 1, id, context=context)

            #:::加载上月结存数据
            last_month_qty = last_month_amount = last_month_qty_price_unit = 0.00
            discount_last_month_qty = discount_last_month_amount = discount_last_month_qty_price_unit = 0.00
            last_month_id = None
            if o.monthly_id.parent_id:
                last_month_id = o.monthly_id.parent_id.id
            else:
                cr.execute("""select max(id) from product_monthly_line where id < %s;"""
                           % (o.monthly_id.id))
                # 获取sql返回后的信息；
                object_reult = cr.fetchall()
                if object_reult[0][0] != None:
                    last_month_id = object_reult[0][0]
            if last_month_id:
                # ('warehouse_id', '=', o.warehouse_id.id),
                product_month_id = self.search(cr, uid, [('company_id', '=', o.company_id.id),
                                                         ('product_id', '=', o.product_id.id),
                                                         ('monthly_id', '=', last_month_id)],
                                               context=context)
                if len(product_month_id) != 0:
                    last_month = self.browse(cr, uid, product_month_id)
                    last_month_qty_price_unit = last_month.inventory_month_qty_price_unit
                    if last_month.price_changes > 0:
                        last_month_qty_price_unit = last_month.price_changes

                    parm = {
                        'last_month_qty': last_month.inventory_month_qty or 0.00,
                        'last_month_amount': last_month.inventory_month_amount or 0.00,
                        'last_month_qty_price_unit': last_month_qty_price_unit or 0.00,
                    }

                    if parm['last_month_qty'] == 0 and parm['last_month_amount'] == 0 and parm[
                        'last_month_qty_price_unit']:
                        pass
                    else:
                        last_month_qty = parm['last_month_qty']
                        last_month_amount = parm['last_month_amount']
                        last_month_qty_price_unit = parm['last_month_qty_price_unit']

                    discount_last_month_qty_price_unit = last_month.discount_inventory_month_qty_price_unit

                    parm = {
                        'discount_last_month_qty': last_month.discount_inventory_month_qty or 0.00,
                        'discount_last_month_amount': last_month.discount_inventory_month_amount or 0.00,
                        'discount_last_month_qty_price_unit': discount_last_month_qty_price_unit or 0.00,
                    }

                    if parm['discount_last_month_qty'] == 0 and parm['discount_last_month_amount'] == 0 and parm[
                        'discount_last_month_qty_price_unit']:
                        pass
                    else:
                        discount_last_month_qty = parm['discount_last_month_qty']
                        discount_last_month_amount = parm['discount_last_month_amount']
                        discount_last_month_qty_price_unit = parm['discount_last_month_qty_price_unit']

                        # zqw modify product_month_id[0]  改为 本月的id
                        # sql = "UPDATE product_monthly_statistics SET last_month_qty=%s, last_month_amount=%s, last_month_qty_price_unit=%s WHERE id =%s " % (
                        #            parm['last_month_qty'], parm['last_month_amount'], parm['last_month_qty_price_unit'],id)
                        # cr.execute(sql)
                        # self.write(cr, uid, product_month_id[0], parm, context)

            # initial = (u'采购入库',)
            # context = {}
            # context['initial'] = u'采购入库'
            # self._month_compute(cr, uid, id, 'purchase_month_in_qty', 'purchase_month_in_amount', initial, context)
            # initial = (u'采购退货',)
            # self._month_compute(cr, uid, id, 'purchase_month_out_qty', 'purchase_month_out_amount', initial, context)
            # initial = (u'采购样品入库',)
            # self._month_compute(cr, uid, id, 'purchase_sample_month_in_qty', 'purchase_sample_month_in_amount',
            #                     initial,
            #                     context)
            # initial = (u'采购样品退货',)
            # self._month_compute(cr, uid, id, 'purchase_sample_month_out_qty', 'purchase_sample_month_out_amount',
            #                     initial,
            #                     context)
            # initial = (u'销售出库',)
            # self._month_compute(cr, uid, id, 'sale_month_out_qty', 'sale_month_out_amount', initial, context)
            # initial = (u'销售退货',)
            # self._month_compute(cr, uid, id, 'sale_month_in_qty', 'sale_month_in_amount', initial, context)
            # initial = (u'销售样品出库',)
            # self._month_compute(cr, uid, id, 'sale_sample_month_out_qty', 'sale_sample_month_out_amount', initial,
            #                     context)
            # initial = (u'销售样品退货',)
            # self._month_compute(cr, uid, id, 'sale_sample_month_in_qty', 'sale_sample_month_in_amount', initial,
            #                     context)
            # initial = (u'仓库调拨',)
            # self._month_compute(cr, uid, id, 'stock_allocation_month_in_qty', 'stock_allocation_month_in_amount',
            #                     initial,
            #                     context)
            # initial = u'仓库调拨'
            # self._month_compute_negated(cr, uid, id, 'stock_allocation_month_out_qty',
            #                             'stock_allocation_month_out_amount',
            #                             initial, context)
            # initial = u'盘点'
            # self._month_property_stock_inventory(cr, uid, id, 'loss_month_qty', 'loss_month_amount', initial, True,
            #                                      context)
            # initial = u'盘点'
            # self._month_property_stock_inventory(cr, uid, id, 'overage_month_in_qty', 'overage_month_in_amount',
            #                                      initial,
            #                                      False, context)
            initial = (u'采购入库',)
            context = {}
            context['initial'] = u'采购入库'
            purchase_month_in_qty, purchase_month_in_amount = self._month_compute_hxy(cr, uid, id,
                                                                                      'purchase_month_in_qty',
                                                                                      'purchase_month_in_amount', o,
                                                                                      initial, context)
            initial = (u'采购退货',)
            purchase_month_out_qty, purchase_month_out_amount = self._month_compute_hxy(cr, uid, id,
                                                                                        'purchase_month_out_qty',
                                                                                        'purchase_month_out_amount', o,
                                                                                        initial, context)
            initial = (u'采购样品入库',)
            purchase_sample_month_in_qty, purchase_sample_month_in_amount = self._month_compute_hxy(cr, uid, id,
                                                                                                    'purchase_sample_month_in_qty',
                                                                                                    'purchase_sample_month_in_amount',
                                                                                                    o, initial, context)
            initial = (u'采购样品退货',)
            purchase_sample_month_out_qty, purchase_sample_month_out_amount = self._month_compute_hxy(cr, uid, id,
                                                                                                      'purchase_sample_month_out_qty',
                                                                                                      'purchase_sample_month_out_amount',
                                                                                                      o, initial,
                                                                                                      context)
            initial = (u'销售出库',)
            sale_month_out_qty, sale_month_out_amount = self._month_compute_hxy(cr, uid, id, 'sale_month_out_qty',
                                                                                'sale_month_out_amount', o, initial,
                                                                                context)
            initial = (u'销售退货',)
            sale_month_in_qty, sale_month_in_amount = self._month_compute_hxy(cr, uid, id, 'sale_month_in_qty',
                                                                              'sale_month_in_amount', o, initial,
                                                                              context)
            initial = (u'销售样品出库',)
            sale_sample_month_out_qty, sale_sample_month_out_amount = self._month_compute_hxy(cr, uid, id,
                                                                                              'sale_sample_month_out_qty',
                                                                                              'sale_sample_month_out_amount',
                                                                                              o, initial,
                                                                                              context)
            initial = (u'销售样品退货',)
            sale_sample_month_in_qty, sale_sample_month_in_amount = self._month_compute_hxy(cr, uid, id,
                                                                                            'sale_sample_month_in_qty',
                                                                                            'sale_sample_month_in_amount',
                                                                                            o, initial,
                                                                                            context)
            initial = (u'仓库调拨',)
            stock_allocation_month_in_qty, stock_allocation_month_in_amount = self._month_compute_hxy(cr, uid, id,
                                                                                                      'stock_allocation_month_in_qty',
                                                                                                      'stock_allocation_month_in_amount',
                                                                                                      o, initial,
                                                                                                      context)
            initial = u'仓库调拨'
            stock_allocation_month_out_qty, stock_allocation_month_out_amount = self._month_compute_negated_hxy(cr, uid,
                                                                                                                id,
                                                                                                                'stock_allocation_month_out_qty',
                                                                                                                'stock_allocation_month_out_amount',
                                                                                                                o,
                                                                                                                initial,
                                                                                                                context)
            initial = u'盘点'
            loss_month_qty, loss_month_amount = self._month_property_stock_inventory(cr, uid, id, 'loss_month_qty',
                                                                                     'loss_month_amount', o, initial,
                                                                                     True, context)
            initial = u'盘点'
            overage_month_in_qty, overage_month_in_amount = self._month_property_stock_inventory(cr, uid, id,
                                                                                                 'overage_month_in_qty',
                                                                                                 'overage_month_in_amount',
                                                                                                 o, initial, False,
                                                                                                 context)
            product_id = o.product_id.id  # 产品
            date_start = o.monthly_id.date_start  # 开始日期
            date_stop = o.monthly_id.date_stop  # 结束日期

            discount_inventory_month_qty = 0
            discount_inventory_month_amount = 0.00
            discount_inventory_month_qty_price_unit = 0.00
            # XXX TODO:供应商发票 id,供应商发票 折扣金额
            cr.execute(
                """select abm.id, abm.discount_amount ,abm.account from account_bill_management abm
                    where abm.type='in_invoice' and abm.state = 'done' and abm.discount_amount != 0
                           and abm.write_date >= %s and abm.write_date <= %s
                       """,
                (date_start, date_stop))
            results = cr.dictfetchall()
            if len(results) > 0:
                for res in results:
                    discount_amount = res['discount_amount']
                    account = res['account']
                    # XXX TODO:发票 id
                    cr.execute(
                        """select ail.id,ail.product_id,ail.quantity,ail.price_unit,ail.price_subtotal
                            from account_invoice_line ail
                            left join account_invoice ai on ail.invoice_id = ai.id
                            where ail.product_id = %s and ail.invoice_id In (select abmair.invoice_id from account_bill_management_account_invoice_rel abmair
                                                                              where abmair.bill_id = %s)
                               """,
                        (product_id, res['id']))
                    results_fp = cr.dictfetchall()
                    if len(results_fp) > 0:
                        for fp in results_fp:
                            fp_quantity = fp['quantity']
                            fp_price_unit = fp['price_unit']

                            # 当前产品的 （总）折扣数量；
                            # 计算公式 一：把同一产品的数量 从 供应商发票——形式发票——发票——产品的数量；
                            discount_inventory_month_qty = discount_inventory_month_qty + fp_quantity

                            # 当前产品的 （一个实际发票） 折扣金额
                            # 计算公式 二：供应商发票——形式发票——发票——产品的数量 * 单价 * 1.17 * 供应商发票 折扣金额 / （折扣金额 + 发票金额）
                            dis_temp_amont = fp_quantity * fp_price_unit * 1.17 * (
                                discount_amount / (account + discount_amount))
                            discount_inventory_month_amount = discount_inventory_month_amount + dis_temp_amont

            inventory_month_qty = inventory_month_amount = 0.00
            # inventory_month_qty = o.last_month_qty + o.purchase_month_in_qty + o.purchase_sample_month_in_qty + o.sale_month_in_qty + o.sale_sample_month_in_qty + o.stock_allocation_month_in_qty + o.overage_month_in_qty - o.purchase_month_out_qty - o.purchase_sample_month_out_qty - o.sale_month_out_qty - o.sale_sample_month_out_qty - o.stock_allocation_month_out_qty - o.loss_month_qty
            # inventory_month_amount = o.last_month_amount + o.purchase_month_in_amount + o.purchase_sample_month_in_amount + o.sale_month_in_amount + o.sale_sample_month_in_amount + o.stock_allocation_month_in_amount + o.overage_month_in_amount - o.purchase_month_out_amount - o.purchase_sample_month_out_amount - o.sale_month_out_amount - o.sale_sample_month_out_amount - o.stock_allocation_month_out_amount - o.loss_month_amount

            # 计算公式一 存货单位成本=[月初库存货的实际成本+∑（当月各批进货的实际单位成本×当月各批进货的数量）]/（月初库存存货数量+当月各批进货数量之和）





            inventory_month_qty = last_month_qty + purchase_month_in_qty + purchase_sample_month_in_qty
            inventory_month_amount = last_month_amount + purchase_month_in_amount + purchase_sample_month_in_amount

            if inventory_month_qty != 0:
                # 当月结存单价 zqw add 2015-12-30
                cur_month_qty_price_unit = inventory_month_amount / inventory_month_qty
                # if last_month_qty_price_unit > 0 and (last_month_qty == 0 or not last_month_qty):
                #     cur_month_qty_price_unit = (cur_month_qty_price_unit + last_month_qty_price_unit) / 2
                # cur_month_qty_price_unit = float('%0.6f'%cur_month_qty_price_unit)
                # 计算公式二 本月结存数量= 上月结存数+本月采购入库数+本月销售退货数+本月盘点盈数+本月调拨进数-本月销售出库数-本月采购退货数-本月盘点亏数-本月调拨出数
                # 当月结存数量 zqw add 2015-12-30
                otherQty = sale_month_in_qty + sale_sample_month_in_qty + overage_month_in_qty + stock_allocation_month_in_qty - \
                           purchase_month_out_qty - purchase_sample_month_out_qty - sale_month_out_qty - sale_sample_month_out_qty - \
                           stock_allocation_month_out_qty - loss_month_qty
                cur_inventory_month_qty = inventory_month_qty + otherQty
                # todo 计算除采购退货的数量：
                otherQty_purchase_out = sale_month_in_qty + sale_sample_month_in_qty + overage_month_in_qty + stock_allocation_month_in_qty - \
                           sale_month_out_qty - sale_sample_month_out_qty - \
                           stock_allocation_month_out_qty - loss_month_qty
                # zqw 修改 调拨先不计算, 问题：当前调拨只计算了一个正品库，没有计算其他库
                # cur_inventory_month_qty = cur_inventory_month_qty+stock_allocation_month_in_qty-stock_allocation_month_out_qty
                # 当月结存金额 zqw add 2015-12-30
                cur_inventory_month_amount = inventory_month_amount + otherQty_purchase_out * cur_month_qty_price_unit - purchase_month_out_amount - purchase_sample_month_out_amount
                # cur_inventory_month_amount =cur_inventory_month_amount+(stock_allocation_month_in_qty-stock_allocation_month_out_qty)*cur_month_qty_price_unit
                # zqw modify 2016-01-04 解决问题:102.8781-102.8781 不等于0的问题，等于-0.00数据库存储2.91038304567E-11   测试条件：产品id=577 2015-12月结
                cur_inventory_month_amount = float('%0.8f' % cur_inventory_month_amount)
                if discount_inventory_month_qty != 0:
                    #     当月折扣加权平均：
                    discount_inventory_month_qty_price_unit = discount_inventory_month_amount / discount_inventory_month_qty

                    if cur_inventory_month_amount > 0 and cur_inventory_month_qty > 0:
                        cur_inventory_month_amount = cur_inventory_month_amount - discount_inventory_month_amount
                        cur_month_qty_price_unit = cur_inventory_month_amount / cur_inventory_month_qty
                    else:
                        cur_month_qty_price_unit = cur_month_qty_price_unit - discount_inventory_month_qty_price_unit
                if not cur_month_qty_price_unit:
                    # todo 当月的产品采购价格：
                    cur_month_qty_price_unit = o.product_id.standard_price
                parm = {
                    'inventory_month_qty': cur_inventory_month_qty,
                    'inventory_month_amount': cur_inventory_month_amount,
                    'inventory_month_qty_price_unit': cur_month_qty_price_unit,
                }
                # self.write(cr, uid, id, parm, context=context)
                updateSql = """
                    UPDATE product_monthly_statistics SET inventory_month_qty=%s, inventory_month_amount=%s, inventory_month_qty_price_unit=%s
                    ,purchase_month_in_qty=%s ,purchase_month_in_amount=%s
                    ,purchase_month_out_qty=%s ,purchase_month_out_amount=%s
                    ,purchase_sample_month_in_qty=%s ,purchase_sample_month_in_amount=%s
                    ,purchase_sample_month_out_qty=%s ,purchase_sample_month_out_amount=%s
                    ,sale_month_out_qty=%s ,sale_month_out_amount=%s
                    ,sale_month_in_qty=%s ,sale_month_in_amount=%s
                    ,sale_sample_month_out_qty=%s ,sale_sample_month_out_amount=%s
                    ,sale_sample_month_in_qty=%s ,sale_sample_month_in_amount=%s
                    ,loss_month_qty=%s ,loss_month_amount=%s
                    ,overage_month_in_qty=%s ,overage_month_in_amount=%s
                    ,last_month_qty=%s ,last_month_amount=%s,last_month_qty_price_unit=%s
                    ,discount_inventory_month_qty=%s ,discount_inventory_month_amount=%s,discount_inventory_month_qty_price_unit=%s
                    ,discount_last_month_qty=%s ,discount_last_month_amount=%s,discount_last_month_qty_price_unit=%s
                    WHERE id =%s
                   """ % (
                    parm['inventory_month_qty'], parm['inventory_month_amount'], parm['inventory_month_qty_price_unit'],
                    purchase_month_in_qty, purchase_month_in_amount,
                    purchase_month_out_qty, purchase_month_out_amount,
                    purchase_sample_month_in_qty, purchase_sample_month_in_amount,
                    purchase_sample_month_out_qty, purchase_sample_month_out_amount,
                    sale_month_out_qty, sale_month_out_amount,
                    sale_month_in_qty, sale_month_in_amount,
                    sale_sample_month_out_qty, sale_sample_month_out_amount,
                    sale_sample_month_in_qty, sale_sample_month_in_amount,
                    loss_month_qty, loss_month_amount,
                    overage_month_in_qty, overage_month_in_amount,
                    last_month_qty, last_month_amount, last_month_qty_price_unit,
                    discount_inventory_month_qty, discount_inventory_month_amount,
                    discount_inventory_month_qty_price_unit,
                    discount_last_month_qty, discount_last_month_amount, discount_last_month_qty_price_unit,
                    id)
                # sql = "UPDATE product_monthly_statistics SET inventory_month_qty=%s, inventory_month_amount=%s, inventory_month_qty_price_unit=%s WHERE id =%s " % (
                #             parm['inventory_month_qty'], parm['inventory_month_amount'], parm['inventory_month_qty_price_unit'],
                #             id)
                cr.execute(updateSql)
            elif last_month_qty_price_unit > 0:
                cur_month_qty_price_unit = last_month_qty_price_unit
                if discount_inventory_month_qty != 0:
                    #     当月折扣加权平均：
                    discount_inventory_month_qty_price_unit = discount_inventory_month_amount / discount_inventory_month_qty
                    cur_month_qty_price_unit = last_month_qty_price_unit - discount_inventory_month_qty_price_unit
                if not cur_month_qty_price_unit:
                    # todo 当月的产品采购价格：
                    cur_month_qty_price_unit = o.product_id.standard_price
                updateSql = """
                    UPDATE product_monthly_statistics SET  inventory_month_qty_price_unit=%s
                    ,last_month_qty_price_unit=%s
                    WHERE id =%s
                   """ % (cur_month_qty_price_unit, last_month_qty_price_unit, id)
                cr.execute(updateSql)
            else:
                # todo 当月的产品采购价格：
                cur_month_qty_price_unit = o.product_id.standard_price
                last_month_qty_price_unit = cur_month_qty_price_unit
                updateSql = """
                    UPDATE product_monthly_statistics SET  inventory_month_qty_price_unit=%s
                    ,last_month_qty_price_unit=%s
                    WHERE id =%s
                   """ % (cur_month_qty_price_unit, last_month_qty_price_unit, id)
                cr.execute(updateSql)

            # todo 实现产品月结以天计算的功能：
            product_monthly_statistics_line = self.pool.get('product.monthly.statistics.line')
            # TODO 1、查询当前的 id 中是否有 产品月结成本，a、没有,创建一个产品的成本的明细；
            # TODO                                       b、有，则比较最近的产品月结成本是否相等，相等就不改变，不相等，增加新生成成本；
            cr.execute("""SELECT pmsl.id,pmsl.product_id,pmsl.monthly_date,pmsl.discount_last_day_qty_price_unit,pmsl.discount_today_qty_price_unit
                        FROM product_monthly_statistics_line pmsl
                        WHERE pmsl.statistics_id = %s ORDER BY pmsl.id DESC LIMIT 1""", (id,))
            results_product = cr.dictfetchall()
            if results_product and len(results_product) > 0:
                line_id = results_product[0]['id']
                product_id = results_product[0]['product_id']
                monthly_date = results_product[0]['monthly_date']
                discount_last_day_qty_price_unit = results_product[0]['discount_last_day_qty_price_unit']
                discount_today_qty_price_unit = results_product[0]['discount_today_qty_price_unit']
                line_parm = {
                    'statistics_id': id,
                    'product_id': product_id,
                    'discount_last_day_qty_price_unit': discount_today_qty_price_unit,
                    'monthly_date': date_local_day,
                    'discount_today_qty_price_unit': cur_month_qty_price_unit,
                }
                if cur_month_qty_price_unit != discount_today_qty_price_unit:
                    if date_local_day == monthly_date:
                        updatemonthlySql_a = """
                            UPDATE product_monthly_statistics_line SET  discount_today_qty_price_unit=%s
                            ,discount_last_day_qty_price_unit=%s
                            WHERE id =%s
                           """ % (cur_month_qty_price_unit, discount_last_day_qty_price_unit, line_id)
                        cr.execute(updatemonthlySql_a)
                    else:
                        # todo 创建产品明细：
                        product_monthly_statistics_line.create(cr, SUPERUSER_ID, line_parm, context=context)
            else:
                line_parm = {
                    'statistics_id': id,
                    'product_id': product_id,
                    'discount_last_day_qty_price_unit': last_month_qty_price_unit,
                    'monthly_date': date_local_day,
                    'discount_today_qty_price_unit': cur_month_qty_price_unit,
                }
                # todo 创建产品明细：
                product_monthly_statistics_line.create(cr, SUPERUSER_ID, line_parm, context=context)
        # 明细排序：
        self.new_sequence(cr, SUPERUSER_ID, ids, context=None)
        return True

    #::::本月采购入库
    def but_purchase_month_in_qty(self, cr, uid, ids, context=None):

        initial = (u'采购入库',)
        self._month_compute(cr, uid, ids, 'purchase_month_in_qty', 'purchase_month_in_amount', initial, context)
        return True

    #::::本月采购退货
    def but_purchase_month_out_qty(self, cr, uid, ids, context=None):
        initial = (u'采购退货',)
        self._month_compute(cr, uid, ids, 'purchase_month_out_qty', 'purchase_month_out_amount', initial, context)
        return True

    #::::本月采购样品入库
    def but_purchase_sample_month_in_qty(self, cr, uid, ids, context=None):

        initial = (u'采购样品入库',)
        self._month_compute(cr, uid, ids, 'purchase_sample_month_in_qty', 'purchase_sample_month_in_amount', initial,
                            context)
        return True

    #::::本月采购样品退库
    def but_purchase_sample_month_out_qty(self, cr, uid, ids, context=None):

        initial = (u'采购样品退货',)
        self._month_compute(cr, uid, ids, 'purchase_sample_month_out_qty', 'purchase_sample_month_out_amount', initial,
                            context)
        return True

    #::::本月销售出库
    def but_sale_month_out_qty(self, cr, uid, ids, context=None):

        initial = (u'销售出库',)
        self._month_compute(cr, uid, ids, 'sale_month_out_qty', 'sale_month_out_amount', initial, context)
        return True

    #::::本月销售退货
    def but_sale_month_in_qty(self, cr, uid, ids, context=None):

        initial = (u'销售退货',)
        self._month_compute(cr, uid, ids, 'sale_month_in_qty', 'sale_month_in_amount', initial, context)
        return True

    #::::本月销售样品出库
    def but_sale_sample_month_out_qty(self, cr, uid, ids, context=None):

        initial = (u'销售样品出库',)
        self._month_compute(cr, uid, ids, 'sale_sample_month_out_qty', 'sale_sample_month_out_amount', initial, context)
        return True

    #::::本月销售样品退货
    def but_sale_sample_month_in_qty(self, cr, uid, ids, context=None):

        initial = (u'销售样品退货',)
        self._month_compute(cr, uid, ids, 'sale_sample_month_in_qty', 'sale_sample_month_in_amount', initial, context)
        return True

    #::::本月仓库调拨入
    def but_stock_allocation_month_in_qty(self, cr, uid, ids, context=None):

        initial = (u'仓库调拨',)
        self._month_compute(cr, uid, ids, 'stock_allocation_month_in_qty', 'stock_allocation_month_in_amount', initial,
                            context)
        return True

    #::::本月仓库调拨出
    def but_stock_allocation_month_out_qty(self, cr, uid, ids, context=None):

        initial = u'仓库调拨'
        self._month_compute_negated(cr, uid, ids, 'stock_allocation_month_out_qty', 'stock_allocation_month_out_amount',
                                    initial, context)
        return True

    #::::本月盘亏数量
    def but_loss_month_qty(self, cr, uid, ids, context=None):

        initial = u'盘点'
        self._month_property_stock_inventory(cr, uid, ids, 'loss_month_qty', 'loss_month_amount', initial, True,
                                             context)
        return True

    #::::本月盘盈数量
    def but_overage_month_in_qty(self, cr, uid, ids, context=None):

        initial = u'盘点'
        self._month_property_stock_inventory(cr, uid, ids, 'overage_month_in_qty', 'overage_month_in_amount', initial,
                                             False, context)
        return True

    def _month_property_stock_inventory(self, cr, uid, id, field_qty, field_amount, o, initial, direction,
                                        context=None):

        # o = self.browse(cr, 1, id, context=context)

        context['product_id'] = o.product_id.id  # 产品
        context['location_ids'] = o.product_id.property_stock_inventory.id  # 盘存盈亏
        context['initial'] = initial  # 入库数据属性
        context['date_start'] = o.monthly_id.date_start+" 00:00:00"  # 开始日期
        context['date_stop'] = o.monthly_id.date_stop+" 23:59:59"  # 结束日期
        context['direction'] = direction  # 方向
        qty, amount = self._statistical_property_stock_inventory(cr, 1, context)
        # parm = {
        #     '%s' % field_qty: qty,
        #     '%s' % field_amount: amount,
        # }
        # self.write(cr, 1, id, parm, context=context)

        return qty, amount

    def _statistical_property_stock_inventory(self, cr, uid, context=None):
        """
        求和
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        quantity = amount = 0.00
        if context['direction'] == True:
            # XXX TODO: 数量合计
            cr.execute(
                """select sum(sm.product_uom_qty) as qty,sum(sm.amount_total) as amount  from stock_move as sm where
                    sm.product_id =%s and
                    sm.state = 'done' and
                    sm.date >= %s and
                    sm.date <= %s and
                    sm.location_dest_id = %s and
                    sm.initial = %s
                       """,
                (context['product_id'], context['date_start'], context['date_stop'], context['location_ids'],
                 context['initial']))
            results = cr.dictfetchall()
            if results[0]['qty'] is not None:
                quantity = results[0]['qty']

            # XXX TODO: 金额合计
            if results[0]['amount'] is not None:
                amount = results[0]['amount']

        if context['direction'] == False:
            # XXX TODO: 数量合计
            cr.execute(
                """select sum(sm.product_uom_qty) as qty,sum(sm.amount_total) as amount  from stock_move as sm where
                    sm.product_id =%s and
                    sm.state = 'done' and
                    sm.date >= %s and
                    sm.date <= %s and
                    sm.location_dest_id != %s and
                    sm.initial = %s
                       """,
                (context['product_id'], context['date_start'], context['date_stop'], context['location_ids'],
                 context['initial']))
            results = cr.dictfetchall()
            if results[0]['qty'] is not None:
                quantity = results[0]['qty']

            # XXX TODO: 金额合计
            if results[0]['amount'] is not None:
                amount = results[0]['amount']
        return quantity, amount

    def _month_compute_negated(self, cr, uid, id, field_qty, field_amount, initial, context=None):

        o = self.browse(cr, 1, id, context=context)

        pool_obj = self.pool.get('product.pool.line')
        pool_ids = pool_obj.search(cr, 1,
                                   [('product_pool_id', '=', o.monthly_id.pool_id.id), ('initial', '=', initial)],
                                   context=context)
        pool_line = pool_obj.browse(cr, 1, pool_ids, context=context)

        location_ids = []
        for l in pool_line:
            location_ids += l.location_ids.ids

        context['product_id'] = o.product_id.id  # 产品
        context['location_ids'] = tuple(list(set(location_ids)))  # 入库库位
        context['initial'] = initial  # 入库数据属性
        context['date_start'] = o.monthly_id.date_start+" 00:00:00"  # 开始日期
        context['date_stop'] = o.monthly_id.date_stop+" 23:59:59"  # 结束日期
        qty, amount = self._statistical_negated(cr, 1, context)
        parm = {
            '%s' % field_qty: qty,
            '%s' % field_amount: amount,
        }
        self.write(cr, 1, id, parm, context=context)

        return

    def _statistical_negated(self, cr, uid, context=None):
        """
        求和
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        quantity = amount = 0.00
        # XXX TODO: 数量合计
        cr.execute(
            """select sum(sm.product_uom_qty) as qty  from stock_move as sm where
                sm.product_id =%s and
                sm.state = 'done' and
                sm.date >= %s and
                sm.date <= %s and
                sm.location_dest_id not in %s and
                sm.initial = %s
                   """,
            (context['product_id'], context['date_start'], context['date_stop'], context['location_ids'],
             context['initial']))
        results = cr.dictfetchall()
        if results[0]['qty'] is not None:
            quantity = results[0]['qty']

        # XXX TODO: 金额合计
        cr.execute(
            """select sum(sm.amount_total) as amount  from stock_move as sm where
                sm.product_id =%s and
                sm.state = 'done' and
                sm.date >= %s and
                sm.date <= %s and
                sm.location_dest_id not in %s and
                sm.initial = %s
                   """,
            (context['product_id'], context['date_start'], context['date_stop'], context['location_ids'],
             context['initial']))
        results = cr.dictfetchall()
        if results[0]['amount'] is not None:
            amount = results[0]['amount']
        return quantity, amount

    def _month_compute(self, cr, uid, id, field_qty, field_amount, initial, context=None):

        o = self.browse(cr, 1, id, context=context)

        pool_obj = self.pool.get('product.pool.line')
        pool_ids = pool_obj.search(cr, 1,
                                   [('product_pool_id', '=', o.monthly_id.pool_id.id), ('initial', 'in', initial)],
                                   context=context)
        pool_line = pool_obj.browse(cr, 1, pool_ids, context=context)

        location_ids = []
        for l in pool_line:
            location_ids += l.location_ids.ids
        context['product_id'] = o.product_id.id  # 产品
        context['location_ids'] = tuple(list(set(location_ids)))  # 入库库位
        context['initial'] = initial  # 入库数据属性
        context['date_start'] = o.monthly_id.date_start+" 00:00:00"  # 开始日期
        context['date_stop'] = o.monthly_id.date_stop+" 23:59:59"  # 结束日期
        qty, amount = self._statistical(cr, 1, context)
        parm = {
            '%s' % field_qty: qty,
            '%s' % field_amount: amount,
        }
        self.write(cr, 1, id, parm, context=context)

        return

    # zqw add 快速查询 数量和金额  不做update更新 调拨入
    def _month_compute_hxy(self, cr, uid, id, field_qty, field_amount, o, initial, context=None):

        # XXX TODO: 库位id
        cr.execute(
            """select l.id,s.b_id from product_pool_line l
               LEFT JOIN stock_location_product_pool_line_rel s on l.id=s.a_id
               where l.product_pool_id=%s
               and l.initial in %s
                   """,
            (o.monthly_id.pool_id.id, initial))
        results = cr.dictfetchall()
        location_ids = []
        # for l in pool_line:
        #   location_ids += l.location_ids.ids
        if len(results) > 0:
            for res in results:
                if res['b_id'] is not None:
                    location_ids.append(res['b_id'])
                    # location_ids += res['b_id']
        context['product_id'] = o.product_id.id  # 产品
        context['location_ids'] = tuple(list(set(location_ids)))  # 入库库位
        context['initial'] = initial  # 入库数据属性
        context['date_start'] = o.monthly_id.date_start+" 00:00:00"  # 开始日期
        context['date_stop'] = o.monthly_id.date_stop+" 23:59:59"  # 结束日期
        qty, amount = self._statistical_hxy(cr, 1, context)

        return qty, amount

    def _statistical_hxy(self, cr, uid, context=None):
        """
        求和
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        quantity = amount = 0.00
        # XXX TODO: 数量合计
        cr.execute(
            """select sum(sm.product_uom_qty) as qty,sum(sm.amount_total) as amount  from stock_move as sm where
                sm.product_id =%s and
                sm.state = 'done' and
                sm.date >= %s and
                sm.date <= %s and
                sm.location_dest_id in %s and
                sm.initial in %s
                   """,
            (context['product_id'], context['date_start'], context['date_stop'], context['location_ids'],
             context['initial']))
        results = cr.dictfetchall()
        if results[0]['qty'] is not None:
            quantity = results[0]['qty']
        # XXX TODO: 金额合计
        if results[0]['amount'] is not None:
            amount = results[0]['amount']

        return quantity, amount

    # zqw add 2015-12-29 解决查询速度慢的问题 调拨出
    def _month_compute_negated_hxy(self, cr, uid, id, field_qty, field_amount, o, initial, context=None):

        # XXX TODO: 库位id
        cr.execute(
            """select l.id,s.b_id from product_pool_line l
               LEFT JOIN stock_location_product_pool_line_rel s on l.id=s.a_id
               where l.product_pool_id=%s
               and l.initial = %s
                   """,
            (o.monthly_id.pool_id.id, initial))
        results = cr.dictfetchall()
        location_ids = []
        if len(results) > 0:
            for res in results:
                if res['b_id'] is not None:
                    location_ids.append(res['b_id'])
                    # location_ids += res['b_id']
        context['product_id'] = o.product_id.id  # 产品
        context['location_ids'] = tuple(list(set(location_ids)))  # 入库库位
        context['initial'] = initial  # 入库数据属性
        context['date_start'] = o.monthly_id.date_start+" 00:00:00"  # 开始日期
        context['date_stop'] = o.monthly_id.date_stop+" 23:59:59"  # 结束日期
        qty, amount = self._statistical_negated_hxy(cr, 1, context)

        return qty, amount

    def _statistical_negated_hxy(self, cr, uid, context=None):
        """
        求和
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        quantity = amount = 0.00
        # XXX TODO: 数量合计
        cr.execute(
            """select sum(sm.product_uom_qty) as qty,sum(sm.amount_total) as amount  from stock_move as sm where
                sm.product_id =%s and
                sm.state = 'done' and
                sm.date >= %s and
                sm.date <= %s and
                sm.location_id in %s and
                sm.initial = %s
                   """,
            (context['product_id'], context['date_start'], context['date_stop'], context['location_ids'],
             context['initial']))
        results = cr.dictfetchall()
        if results[0]['qty'] is not None:
            quantity = results[0]['qty']
        # XXX TODO: 金额合计
        if results[0]['amount'] is not None:
            amount = results[0]['amount']

        return quantity, amount

    def but_show_monthly(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'odoo8_monthly_system', 'view_tree_odoo8_monthly_system')
        id = result and result[1] or False

        result_search = mod_obj.get_object_reference(cr, uid, 'odoo8_monthly_system',
                                                     'view_search_actions_monthly_system')
        search_id = result_search and result_search[1] or False

        initial = context['initial']

        o = self.browse(cr, uid, ids[0], context)

        pool_obj = self.pool.get('product.pool.line')
        pool_ids = pool_obj.search(cr, uid,
                                   [('product_pool_id', '=', o.monthly_id.pool_id.id), ('initial', '=', initial)],
                                   context=context)


        #:::::库位，开始与结束
        pool_line = pool_obj.browse(cr, 1, pool_ids, context=context)
        location_ids = []
        for l in pool_line:
            location_ids += l.location_ids.ids

        date_start = o.monthly_id.date_start
        date_stop = o.monthly_id.date_stop

        # 查询所有所有符合当前条件的id
        domain = [('product_id', '=', o.product_id.id), ('state', '=', 'done'), ('date', '>=', date_start),
                  ('date', '<=', date_stop), ('location_dest_id', 'in', tuple(list(set(location_ids)))),
                  ('initial', '=', initial)]
        obj_move = self.pool.get('stock.move')
        move_ids = obj_move.search(cr, 1, domain)

        return {
            'name': initial,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_model': 'stock.move',
            'view_mode': 'tree',
            'view_id': id,
            'search_view_id': search_id,
            'target': 'current',
            'domain': "[('id','in',%s)]" % move_ids,
            'context': {'my_partner': True}
        }

    def new_sequence(self, cr, uid, ids, context=None):
        #::::修改自动编号 开始
        o = self.browse(cr, uid, ids, context=context)
        sequence = 1
        for gid in o.statistics_line:
            cr.execute("UPDATE product_monthly_statistics_line  SET sequence=%s  WHERE id = %s  " % (sequence, gid.id))
            sequence = sequence + 1
        #::::修改自动编号 结束

        return True


class product_monthly_price_changes(osv.osv):
    _name = "product.monthly.price.changes"
    _description = u"下月期初平均价格"

    _columns = {
        'product_id': fields.many2one('product.product', u'产品'),
        'monthly_id': fields.many2one('product.monthly.line', u'月份'),
        'name': fields.many2one('product.monthly', u'年份'),
        'price_changes': fields.float(u'下月期初平均价格', digits_compute=dp.get_precision('Product Price'), ),

        'state': fields.selection([('draft', u'草稿'),
                                   ('review', u'等待审核'),
                                   ('done', u'已完成'),
                                   ('sent', u'发送邮件'),
                                   ('cancel', u'取消'), ],
                                  u'状态', ),

    }

    _defaults = {
        'state': 'draft',
    }

    def but_review(self, cr, uid, ids, context=None):
        state = 'review'
        message = '提交草稿 等待审核!'
        self.write(cr, uid, ids, {'state': state}, context=context)
        return True

    def but_cancel(self, cr, uid, ids, context=None):
        state = 'cancel'
        message = '单据已取消'
        self.but_action(cr, uid, ids, state, message, context=context)
        return True

    def but_done(self, cr, uid, ids, context={}):
        state = 'done'
        message = '单据已完成'
        self.but_action(cr, uid, ids, state, message, context=context)
        return True

    def but_draft(self, cr, uid, ids, context={}):
        state = 'draft'
        message = '单据重置为草稿'
        self.but_action(cr, uid, ids, state, message, context=context)
        return True

    def but_action(self, cr, uid, ids, state, message, context={}):
        self.write(cr, uid, ids, {'state': state}, context=context)
        return True

class product_monthly_statistics_line(osv.osv):
    _name = "product.monthly.statistics.line"
    _description = u"产品月结成本（天）"
    _rec_name = 'product_id'
    _order = 'id asc'

    _columns = {
        'sequence': fields.integer(u'序号'),
        'product_id': fields.many2one('product.product', u'产品'),
        'monthly_date': fields.date(u'月结时间'),
        'discount_last_day_qty_price_unit': fields.float(u'昨天加权平均', digits_compute=dp.get_precision('Product Price')),
        'discount_today_qty_price_unit': fields.float(u'当天加权平均', digits_compute=dp.get_precision('Product Price')),
        'statistics_id': fields.many2one('product.monthly.statistics', u'产品月结', ondelete='cascade', select=True)
    }
